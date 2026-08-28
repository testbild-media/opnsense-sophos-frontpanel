#!/usr/local/bin/python3
"""Sophos SG/XG front-panel daemon for OPNsense.

Protocol implemented from measurements on the original Sophos 16x2 front panel:
  2400 8N2, no flow control
  FE 01 clear
  FE 02 home / display-shift reset
  FE 06 key poll; response FD xx
  FE 0C display on, cursor off, blink off
  FE 80 line 1
  FE C0 line 2

After every key poll FE 02 + 40 ms + FE 0C + 20 ms is mandatory because
FE 06 changes the LCD controller state.
"""

from __future__ import annotations

import argparse
import configparser
import fcntl
import json
import logging
import os
import re
import select
import signal
import subprocess
import sys
import termios
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CONFIG_FILE = "/usr/local/etc/sophos_frontpanel.conf"
STATUS_FILE = "/var/run/sophos_frontpanel.status.json"
LCD_WIDTH = 16
SERIAL_DEVICE_RE = re.compile(r"^/dev/(?:cuau[0-9]+|cuaU[0-9]+(?:\.[0-9]+)?)$")

CMD = 0xFE
RESP = 0xFD
KEY_NONE = 0xBF
KEY_CODES = {
    0xBE: "UP",
    0xBD: "DOWN",
    0xBB: "ENTER",
    0xB7: "ESC",
}

LOG = logging.getLogger("sophos_frontpanel")


@dataclass
class Config:
    enabled: bool = False
    device: str = "/dev/cuau1"
    title: str = "OPNsense SG330"
    wan_interfaces: List[str] = None
    lan_interfaces: List[str] = None
    wan_use_description: bool = True
    lan_use_description: bool = True

    def __post_init__(self) -> None:
        if self.wan_interfaces is None:
            self.wan_interfaces = ["wan"]
        if self.lan_interfaces is None:
            self.lan_interfaces = ["lan"]
    poll_ms: int = 100
    refresh_seconds: int = 2
    auto_rotate: bool = True
    rotate_seconds: int = 5
    log_level: str = "info"


def _cfg_bool(section: configparser.SectionProxy, name: str, default: bool) -> bool:
    value = section.get(name, "1" if default else "0").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _cfg_list(section: configparser.SectionProxy, plural_name: str, singular_name: str, default: List[str]) -> List[str]:
    raw = section.get(plural_name, section.get(singular_name, ",".join(default))).strip()
    values: List[str] = []
    for item in raw.split(","):
        item = item.strip()
        if item and re.fullmatch(r"[A-Za-z0-9_]+", item) and item not in values:
            values.append(item)
    return values or list(default)


def _cfg_int(
    section: configparser.SectionProxy, name: str, default: int, low: int, high: int
) -> int:
    try:
        value = int(section.get(name, str(default)).strip())
    except ValueError:
        return default
    return max(low, min(high, value))


def load_config(path: str = CONFIG_FILE) -> Config:
    cfg = Config()
    parser = configparser.ConfigParser(interpolation=None)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            parser.read_file(handle)
    except OSError as exc:
        LOG.warning("Cannot read rendered plugin configuration %s: %s", path, exc)
        return cfg
    except configparser.Error as exc:
        LOG.error("Invalid rendered plugin configuration %s: %s", path, exc)
        return cfg

    if not parser.has_section("general"):
        LOG.warning("Rendered plugin configuration %s has no [general] section", path)
        return cfg

    section = parser["general"]
    cfg.enabled = _cfg_bool(section, "enabled", cfg.enabled)
    cfg.device = section.get("device", cfg.device).strip()
    cfg.title = section.get("title", cfg.title).strip()[:LCD_WIDTH]
    cfg.wan_interfaces = _cfg_list(section, "wan_interfaces", "wan_interface", cfg.wan_interfaces)
    cfg.lan_interfaces = _cfg_list(section, "lan_interfaces", "lan_interface", cfg.lan_interfaces)
    cfg.wan_use_description = _cfg_bool(section, "wan_use_description", cfg.wan_use_description)
    cfg.lan_use_description = _cfg_bool(section, "lan_use_description", cfg.lan_use_description)
    cfg.poll_ms = _cfg_int(section, "poll_ms", cfg.poll_ms, 100, 1000)
    cfg.refresh_seconds = _cfg_int(
        section, "refresh_seconds", cfg.refresh_seconds, 2, 60
    )
    cfg.auto_rotate = _cfg_bool(section, "auto_rotate", cfg.auto_rotate)
    cfg.rotate_seconds = _cfg_int(
        section, "rotate_seconds", cfg.rotate_seconds, 2, 60
    )
    cfg.log_level = section.get("log_level", cfg.log_level).strip().lower()
    if cfg.log_level not in {"debug", "info", "warning", "error"}:
        cfg.log_level = "info"
    return cfg


def run_command(argv: List[str], timeout: float = 1.5) -> str:
    try:
        proc = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def lcd_text(value: str, width: int = LCD_WIDTH) -> str:
    """Return printable LCD-safe ASCII text no wider than *width*."""
    replacements = str.maketrans({
        "ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss",
        "–": "-", "—": "-", "→": ">", "←": "<", "°": "o",
    })
    value = str(value).translate(replacements)
    value = "".join(ch if 32 <= ord(ch) <= 126 else "?" for ch in value)
    return value[:max(0, width)]


def ascii16(value: str) -> bytes:
    """Return exactly 16 printable ASCII bytes and never append NUL."""
    return lcd_text(value).ljust(LCD_WIDTH).encode("ascii", "replace")


def short_ip(value: str) -> str:
    value = value.strip()
    if not value:
        return "-"
    # pluginctl may theoretically return a JSON/string wrapper on a future build.
    return lcd_text(value.strip('"'))


def compact_address(value: str) -> str:
    """Fit an address on one LCD row while preserving both ends when needed."""
    value = lcd_text(value, 255).strip() or "-"
    if len(value) <= LCD_WIDTH:
        return value
    # IPv6 and other long addresses cannot be represented fully on a 16-column
    # display. Preserve recognizable prefix and suffix rather than blind chopping.
    return value[:7] + ".." + value[-7:]


def compact_storage(value_bytes: int) -> str:
    gib = max(0, value_bytes) / (1024 ** 3)
    if gib >= 1024:
        tib = gib / 1024.0
        return f"{tib:.1f}T" if tib < 10 else f"{tib:.0f}T"
    if gib < 10:
        return f"{gib:.1f}G"
    return f"{gib:.0f}G"


def memory_line(percent: int, used_bytes: int, total_bytes: int) -> str:
    used = compact_storage(used_bytes)
    total = compact_storage(total_bytes)
    candidates = [
        f"MEM {percent}% {used}/{total}",
        f"MEM {percent}% {used}",
        f"MEM {percent}%",
    ]
    for candidate in candidates:
        if len(candidate) <= LCD_WIDTH:
            return candidate
    return lcd_text(candidates[-1])


def gateway_header(name: str, marker: str) -> str:
    marker = lcd_text(marker, 4) or "?"
    prefix = "GW "
    suffix = " " + marker
    available = max(1, LCD_WIDTH - len(prefix) - len(suffix))
    return prefix + lcd_text(name, available) + suffix



def interface_header(display_name: str, device: str) -> str:
    """Render interface name left and real device right within 16 columns.

    Typical result: ``WANSL       igb0``.  When both values do not fit, the
    interface name is shortened first.  Very long device names are capped at
    ten columns so that the page still identifies the logical interface.
    """
    label = lcd_text(display_name, LCD_WIDTH).strip() or "IF"
    dev = lcd_text(device, LCD_WIDTH).strip()
    if not dev:
        return lcd_text(label)
    if len(dev) > 10:
        dev = dev[:10]
    left_width = max(1, LCD_WIDTH - len(dev) - 1)
    label = label[:left_width]
    return label.ljust(LCD_WIDTH - len(dev)) + dev


def interface_display_name(logical_name: str, description: str, use_description: bool) -> str:
    """Choose the visible OPNsense interface identifier or Description."""
    identifier = lcd_text(logical_name.upper(), LCD_WIDTH).strip() or "IF"
    descr = lcd_text(description, LCD_WIDTH).strip()
    return descr if use_description and descr else identifier

def fmt_uptime(seconds: int) -> str:
    days, rem = divmod(max(0, seconds), 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d {hours:02d}h {minutes:02d}m"
    return f"{hours:02d}h {minutes:02d}m"


class SerialFrontPanel:
    def __init__(self, device: str):
        self.device = device
        self.fd: Optional[int] = None
        self.last_display: Optional[Tuple[bytes, bytes]] = None

    def open(self) -> None:
        if not SERIAL_DEVICE_RE.fullmatch(self.device):
            raise ValueError(f"Unsupported serial device name: {self.device}")
        fd = os.open(self.device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if hasattr(termios, "TIOCEXCL"):
                try:
                    fcntl.ioctl(fd, termios.TIOCEXCL)
                except OSError:
                    pass
            attrs = termios.tcgetattr(fd)
            attrs[0] = 0  # iflag
            attrs[1] = 0  # oflag
            attrs[2] = termios.CLOCAL | termios.CREAD | termios.CS8 | termios.CSTOPB
            attrs[3] = 0  # lflag
            attrs[4] = termios.B2400
            attrs[5] = termios.B2400
            attrs[6][termios.VMIN] = 0
            attrs[6][termios.VTIME] = 0
            termios.tcsetattr(fd, termios.TCSANOW, attrs)
            termios.tcflush(fd, termios.TCIOFLUSH)
        except Exception:
            os.close(fd)
            raise
        self.fd = fd
        LOG.info("Opened front panel UART %s at 2400 8N2", self.device)

    def close(self) -> None:
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None

    def _write(self, data: bytes) -> None:
        if self.fd is None:
            raise RuntimeError("serial port not open")
        view = memoryview(data)
        while view:
            try:
                sent = os.write(self.fd, view)
            except BlockingIOError:
                select.select([], [self.fd], [], 0.1)
                continue
            view = view[sent:]

    def initialize(self) -> None:
        self._write(bytes([CMD, 0x01]))
        time.sleep(0.100)
        self._write(bytes([CMD, 0x0C]))
        time.sleep(0.020)
        self.last_display = None

    def display(self, line1: str, line2: str, force: bool = False) -> bool:
        row1, row2 = ascii16(line1), ascii16(line2)
        if not force and self.last_display == (row1, row2):
            return False
        # Do not clear on live updates. The controller briefly blanks when content
        # is actually rewritten, so we only write changed 16x2 frames.
        self._write(bytes([CMD, 0x80]) + row1)
        self._write(bytes([CMD, 0xC0]) + row2)
        self.last_display = (row1, row2)
        return True

    def _restore_after_poll(self) -> None:
        self._write(bytes([CMD, 0x02]))
        time.sleep(0.040)
        self._write(bytes([CMD, 0x0C]))
        time.sleep(0.020)

    def poll_key(self, response_window: float = 0.060) -> int:
        if self.fd is None:
            return KEY_NONE
        try:
            termios.tcflush(self.fd, termios.TCIFLUSH)
            self._write(bytes([CMD, 0x06]))
            deadline = time.monotonic() + response_window
            rx = bytearray()
            while time.monotonic() < deadline:
                remaining = max(0.0, deadline - time.monotonic())
                readable, _, _ = select.select([self.fd], [], [], remaining)
                if not readable:
                    break
                try:
                    chunk = os.read(self.fd, 64)
                except BlockingIOError:
                    continue
                if not chunk:
                    continue
                rx.extend(chunk)
                # Find any complete FD xx frame. Last frame wins.
                if len(rx) >= 2 and RESP in rx[:-1]:
                    break
            key = KEY_NONE
            for idx in range(len(rx) - 1):
                if rx[idx] == RESP:
                    key = rx[idx + 1]
            return key
        finally:
            # This is required even if the reply is absent or malformed.
            self._restore_after_poll()


class SystemSampler:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._last_cpu: Optional[List[int]] = None
        self.cpu_percent = 0
        self.ram_percent = 0
        self.ram_used_bytes = 0
        self.ram_total_bytes = 0
        self.load1 = 0.0
        self.uptime_seconds = 0
        self.hostname = "OPNsense"
        self.interfaces: Dict[str, Dict[str, str]] = {}
        self.gateways: List[Dict[str, str]] = []

    def _sysctl(self, name: str) -> str:
        return run_command(["/sbin/sysctl", "-n", name])

    def _cpu(self) -> int:
        raw = self._sysctl("kern.cp_time")
        try:
            values = [int(x) for x in raw.split()[:5]]
        except ValueError:
            return self.cpu_percent
        if len(values) != 5:
            return self.cpu_percent
        if self._last_cpu is not None:
            delta = [max(0, now - old) for now, old in zip(values, self._last_cpu)]
            total = sum(delta)
            if total > 0:
                self.cpu_percent = int(round(100.0 * (total - delta[4]) / total))
        self._last_cpu = values
        return max(0, min(100, self.cpu_percent))

    def _ram(self) -> int:
        try:
            phys = int(self._sysctl("hw.physmem"))
            page_size = int(self._sysctl("hw.pagesize"))
            free_pages = int(self._sysctl("vm.stats.vm.v_free_count"))
            inactive_pages = int(self._sysctl("vm.stats.vm.v_inactive_count"))
            available = (free_pages + inactive_pages) * page_size
            used = max(0, phys - available)
            self.ram_total_bytes = phys
            self.ram_used_bytes = used
            if phys > 0:
                self.ram_percent = int(round(used * 100.0 / phys))
        except ValueError:
            pass
        return max(0, min(100, self.ram_percent))

    def _uptime(self) -> int:
        raw = self._sysctl("kern.boottime")
        match = re.search(r"sec\s*=\s*(\d+)", raw)
        if match:
            self.uptime_seconds = max(0, int(time.time()) - int(match.group(1)))
        return self.uptime_seconds

    def _load(self) -> float:
        raw = self._sysctl("vm.loadavg")
        match = re.search(r"([0-9]+(?:\.[0-9]+)?)", raw)
        if match:
            try:
                self.load1 = float(match.group(1))
            except ValueError:
                pass
        return self.load1

    def _interface_details(self, name: str) -> Dict[str, str]:
        """Read identifier, Description, resolved device and IPv4 address.

        OPNsense's pluginctl is used as the supported local accessor: ``-g``
        reads the configured interface node and ``-4`` returns the primary IPv4
        address together with the resolved runtime device.
        """
        result = {
            "identifier": name.upper(),
            "description": name.upper(),
            "device": "",
            "address": "-",
        }
        if not re.fullmatch(r"[A-Za-z0-9_]+", name):
            return result

        # Read configured metadata as scalar properties. This is more reliable
        # than parsing the whole interface node and, importantly, prevents a
        # runtime JSON null from becoming the literal string "None".
        configured_device = run_command([
            "/usr/local/sbin/pluginctl", "-g", f"interfaces.{name}.if"
        ]).strip()
        configured_descr = run_command([
            "/usr/local/sbin/pluginctl", "-g", f"interfaces.{name}.descr"
        ]).strip()
        if configured_descr:
            result["description"] = configured_descr
        if configured_device:
            result["device"] = configured_device

        out = run_command(["/usr/local/sbin/pluginctl", "-4", name])
        if out.startswith("{"):
            try:
                parsed = json.loads(out)
                if isinstance(parsed, dict):
                    value = parsed.get(name)
                    item = None
                    if isinstance(value, list) and value and isinstance(value[0], dict):
                        item = value[0]
                    elif isinstance(value, dict):
                        item = value
                    if item is not None:
                        raw_address = item.get("address")
                        raw_device = item.get("device")
                        address = raw_address.strip() if isinstance(raw_address, str) else ""
                        runtime_device = raw_device.strip() if isinstance(raw_device, str) else ""
                        if address:
                            result["address"] = short_ip(address)
                        # Prefer the configured OPNsense interface device. Use
                        # the runtime value only as a fallback when config has
                        # no device at all (e.g. a dynamically registered type).
                        if not result["device"] and runtime_device:
                            result["device"] = runtime_device
            except json.JSONDecodeError:
                pass
        elif out:
            result["address"] = short_ip(out)

        return result

    def _gateway_status(self) -> List[Dict[str, str]]:
        out = run_command(["/usr/local/sbin/configctl", "interface", "gateways.status"], timeout=2.0)
        if not out:
            return []
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return []
        result: List[Dict[str, str]] = []
        if isinstance(data, dict):
            for key, item in data.items():
                if not isinstance(item, dict):
                    continue
                result.append({
                    "name": str(item.get("name", key)),
                    "status": str(item.get("status_translated", item.get("status", "?"))),
                    "address": str(item.get("address", "~")),
                })
        return result[:8]

    def sample(self) -> None:
        self.hostname = self._sysctl("kern.hostname") or "OPNsense"
        self._cpu()
        self._ram()
        self._uptime()
        self._load()
        selected = list(dict.fromkeys(self.cfg.wan_interfaces + self.cfg.lan_interfaces))
        self.interfaces = {name: self._interface_details(name) for name in selected}
        self.gateways = self._gateway_status()

    def pages(self, title: str) -> List[Tuple[str, str, str]]:
        # The physical panel is strictly 16x2. Keep every page intentionally
        # within 16 characters instead of relying on ascii16() truncation.
        load = min(max(self.load1, 0.0), 99.9)
        cpu_line = f"CPU {self.cpu_percent:3d}% L {load:4.1f}"

        mem_line = memory_line(self.ram_percent, self.ram_used_bytes, self.ram_total_bytes)

        pages: List[Tuple[str, str, str]] = [
            ("HOME", lcd_text(title or "OPNsense"), lcd_text(self.hostname)),
        ]
        for name in self.cfg.wan_interfaces:
            meta = self.interfaces.get(name, {})
            label = interface_display_name(
                name, str(meta.get("description", "")), self.cfg.wan_use_description
            )
            pages.append((
                f"WAN:{name}",
                interface_header(label, str(meta.get("device", ""))),
                compact_address(str(meta.get("address", "-"))),
            ))
        for name in self.cfg.lan_interfaces:
            meta = self.interfaces.get(name, {})
            label = interface_display_name(
                name, str(meta.get("description", "")), self.cfg.lan_use_description
            )
            pages.append((
                f"LAN:{name}",
                interface_header(label, str(meta.get("device", ""))),
                compact_address(str(meta.get("address", "-"))),
            ))
        pages.extend([
            ("LOAD", lcd_text(cpu_line), lcd_text(mem_line)),
            ("UPTIME", "System Uptime", lcd_text(fmt_uptime(self.uptime_seconds))),
        ])
        if self.gateways:
            for gw in self.gateways:
                status = gw["status"]
                normalized = status.lower()
                if "online" in normalized or normalized == "none":
                    marker = "OK"
                elif "pending" in normalized:
                    marker = "WAIT"
                else:
                    marker = "ERR"
                pages.append(("GW", gateway_header(gw["name"], marker), compact_address(gw["address"])))
        else:
            pages.append(("GW", "Gateway status", "not available"))
        return pages


class FrontPanelDaemon:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.panel = SerialFrontPanel(cfg.device)
        self.sampler = SystemSampler(cfg)
        self.running = True
        self.page_index = 0
        self.auto_rotate = cfg.auto_rotate
        self.previous_key = KEY_NONE
        self.next_sample = 0.0
        self.next_rotate = 0.0
        self.flash_until = 0.0
        self.flash_lines: Optional[Tuple[str, str]] = None
        self.started_at = time.time()
        self.last_status_write = 0.0

    def stop(self, *_args) -> None:
        self.running = False

    def flash(self, line1: str, line2: str = "", seconds: float = 1.0) -> None:
        self.flash_lines = (lcd_text(line1), lcd_text(line2))
        self.flash_until = time.monotonic() + seconds
        self.panel.display(self.flash_lines[0], self.flash_lines[1], force=True)

    def current_pages(self) -> List[Tuple[str, str, str]]:
        pages = self.sampler.pages(self.cfg.title)
        if not pages:
            return [("HOME", self.cfg.title, "OPNsense")]
        self.page_index %= len(pages)
        return pages

    def handle_key(self, key_code: int) -> None:
        # Only a transition from no-key to key is a new physical press.
        if key_code == KEY_NONE:
            self.previous_key = KEY_NONE
            return
        if self.previous_key != KEY_NONE:
            self.previous_key = key_code
            return
        self.previous_key = key_code
        key = KEY_CODES.get(key_code)
        if key is None:
            LOG.debug("Unknown key code 0x%02X", key_code)
            return
        LOG.info("Front panel key: %s", key)
        pages = self.current_pages()
        if key == "UP":
            self.page_index = (self.page_index - 1) % len(pages)
            self.next_rotate = time.monotonic() + self.cfg.rotate_seconds
        elif key == "DOWN":
            self.page_index = (self.page_index + 1) % len(pages)
            self.next_rotate = time.monotonic() + self.cfg.rotate_seconds
        elif key == "ENTER":
            self.auto_rotate = not self.auto_rotate
            self.flash("Auto rotation", "ON" if self.auto_rotate else "OFF")
            self.next_rotate = time.monotonic() + self.cfg.rotate_seconds
        elif key == "ESC":
            self.page_index = 0
            self.flash("Home", self.cfg.title)
            self.next_rotate = time.monotonic() + self.cfg.rotate_seconds

    def render(self, force: bool = False) -> None:
        now = time.monotonic()
        if self.flash_lines is not None and now < self.flash_until:
            return
        if self.flash_lines is not None:
            self.flash_lines = None
            force = True
        pages = self.current_pages()
        _, line1, line2 = pages[self.page_index]
        self.panel.display(line1, line2, force=force)

    def write_status(self, last_error: str = "") -> None:
        now = time.monotonic()
        if not last_error and now - self.last_status_write < 1.0:
            return
        pages = self.current_pages()
        page_name = pages[self.page_index][0] if pages else "HOME"
        payload = {
            "running": True,
            "pid": os.getpid(),
            "device": self.cfg.device,
            "page": page_name,
            "auto_rotate": self.auto_rotate,
            "started": int(self.started_at),
            "last_error": last_error,
        }
        tmp = STATUS_FILE + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, separators=(",", ":"))
            os.replace(tmp, STATUS_FILE)
            self.last_status_write = now
        except OSError:
            pass

    def run(self) -> int:
        self.panel.open()
        self.panel.initialize()
        self.sampler.sample()
        self.render(force=True)
        now = time.monotonic()
        self.next_sample = now + self.cfg.refresh_seconds
        self.next_rotate = now + self.cfg.rotate_seconds
        self.write_status()
        LOG.info("Sophos front panel daemon started")

        try:
            while self.running:
                cycle_start = time.monotonic()
                try:
                    key = self.panel.poll_key()
                    self.handle_key(key)
                except OSError as exc:
                    LOG.error("Serial I/O error: %s", exc)
                    self.write_status(str(exc))
                    return 2

                now = time.monotonic()
                if now >= self.next_sample:
                    self.sampler.sample()
                    self.next_sample = now + self.cfg.refresh_seconds

                pages = self.current_pages()
                if self.auto_rotate and now >= self.next_rotate and self.flash_lines is None:
                    self.page_index = (self.page_index + 1) % len(pages)
                    self.next_rotate = now + self.cfg.rotate_seconds

                self.render()
                self.write_status()

                # pollMs means minimum start-to-start interval. The mandatory
                # response/restore timings already consume about 120 ms when the
                # full response window is used, so this never busy-loops.
                elapsed = time.monotonic() - cycle_start
                delay = max(0.0, self.cfg.poll_ms / 1000.0 - elapsed)
                if delay:
                    time.sleep(delay)
        finally:
            LOG.info("Stopping Sophos front panel daemon")
            self.panel.close()
            try:
                os.unlink(STATUS_FILE)
            except OSError:
                pass
        return 0


def configure_logging(level: str) -> None:
    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Sophos front panel daemon for OPNsense")
    parser.add_argument("--config", default=CONFIG_FILE, help="rendered plugin configuration path")
    parser.add_argument("--check", action="store_true", help="validate configuration/device and exit")
    parser.add_argument("--is-enabled", action="store_true", help="return success only when enabled in OPNsense")
    parser.add_argument("--force", action="store_true", help="run even if the GUI enabled flag is off")
    parser.add_argument("--device", help="override serial device for diagnostics")
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.device:
        cfg.device = args.device
    configure_logging(cfg.log_level)

    if args.is_enabled:
        return 0 if cfg.enabled else 1

    if not cfg.enabled and not args.force and not args.check:
        LOG.info("Sophos Frontpanel is disabled in the rendered OPNsense plugin configuration")
        return 0

    if not SERIAL_DEVICE_RE.fullmatch(cfg.device):
        LOG.error("Invalid device %r; expected a FreeBSD /dev/cuauN or /dev/cuaUN callout device", cfg.device)
        return 64
    if not os.path.exists(cfg.device):
        LOG.error("Serial device %s does not exist", cfg.device)
        return 66

    if args.check:
        panel = SerialFrontPanel(cfg.device)
        try:
            panel.open()
            print(f"UART {cfg.device}: OK (2400 8N2)")
            return 0
        except Exception as exc:
            print(f"UART {cfg.device}: FAILED: {exc}", file=sys.stderr)
            return 1
        finally:
            panel.close()

    daemon = FrontPanelDaemon(cfg)
    signal.signal(signal.SIGTERM, daemon.stop)
    signal.signal(signal.SIGINT, daemon.stop)
    try:
        return daemon.run()
    except (OSError, ValueError, RuntimeError) as exc:
        LOG.error("Fatal: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
