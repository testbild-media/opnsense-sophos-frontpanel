#!/usr/local/bin/python3
"""List usable FreeBSD serial callout devices for the OPNsense MVC dropdown.

The list deliberately excludes a serial device when it is actively configured
as a system/login console. Potential-console capability alone (uart flags 0x10)
is not enough to exclude a port.

Output format is a flat JSON object for OPNsense JsonKeyValueStoreField:
    {"/dev/cuau0": "/dev/cuau0 (uart0, COM1, 0x3f8)", ...}
"""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
from typing import Dict, Iterable, Set

CALLOUT_RE = re.compile(r"^/dev/(?:cuau\d+|cuaU\d+(?:\.\d+)?)$")
TTY_RE = re.compile(r"\b(ttyu\d+|ttyU\d+(?:\.\d+)?)\b")
UART_LINE_RE = re.compile(r"^uart(\d+):.*?\bport\s+(0x[0-9a-fA-F]+)(?:-[^\s]+)?\b")
UART_CONSOLE_RE = re.compile(r"^uart(\d+):\s+console\b", re.MULTILINE)
HEX_PORT_RE = re.compile(r"0x[0-9a-fA-F]+")


def run(argv: Iterable[str]) -> str:
    try:
        proc = subprocess.run(
            list(argv),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def tty_to_callout(tty_name: str) -> str:
    if tty_name.startswith("ttyu"):
        return "/dev/cuau" + tty_name[4:]
    if tty_name.startswith("ttyU"):
        return "/dev/cuaU" + tty_name[4:]
    return ""


def discover_devices(dev_dir: str = "/dev") -> list[str]:
    candidates = []
    for pattern in ("cuau*", "cuaU*"):
        candidates.extend(glob.glob(os.path.join(dev_dir, pattern)))
    result = []
    for path in candidates:
        normalized = "/dev/" + os.path.basename(path)
        if CALLOUT_RE.fullmatch(normalized):
            result.append(normalized)
    return sorted(set(result), key=natural_device_key)


def natural_device_key(path: str):
    # Legacy motherboard UARTs first, then USB serial devices, each numerically.
    base = os.path.basename(path)
    family = 0 if base.startswith("cuau") else 1
    match = re.search(r"(\d+)(?:\.(\d+))?$", base)
    return (family, int(match.group(1)) if match else 9999, int(match.group(2) or 0) if match else 0, base)


def parse_uart_ports(dmesg: str) -> Dict[int, int]:
    result: Dict[int, int] = {}
    for line in dmesg.splitlines():
        match = UART_LINE_RE.search(line)
        if match:
            try:
                result[int(match.group(1))] = int(match.group(2), 16)
            except ValueError:
                pass
    return result


def port_to_device(port: int, uart_ports: Dict[int, int]) -> str:
    for unit, ioport in uart_ports.items():
        if ioport == port:
            return f"/dev/cuau{unit}"
    return ""


def parse_port(value: str) -> int | None:
    match = HEX_PORT_RE.search(value or "")
    if not match:
        return None
    try:
        return int(match.group(0), 16)
    except ValueError:
        return None


def detect_console_devices(dmesg: str | None = None) -> Set[str]:
    excluded: Set[str] = set()
    dmesg_text = run(["/sbin/dmesg"]) if dmesg is None else dmesg
    uart_ports = parse_uart_ports(dmesg_text)

    # Kernel console reporting, when it exposes a concrete tty device.
    kern_console = run(["/sbin/sysctl", "-n", "kern.console"])
    for tty in TTY_RE.findall(kern_console):
        device = tty_to_callout(tty)
        if device:
            excluded.add(device)

    # FreeBSD emits an explicit line when a UART is actually the kernel console.
    for unit_text in UART_CONSOLE_RE.findall(dmesg_text):
        excluded.add(f"/dev/cuau{int(unit_text)}")

    # Exclude serial ports with a running getty as they are actively consumed as
    # login terminals even if kern.console itself is video-only.
    ps_text = run(["/bin/ps", "ax", "-o", "command="])
    for line in ps_text.splitlines():
        if "getty" not in line:
            continue
        for tty in TTY_RE.findall(line):
            device = tty_to_callout(tty)
            if device:
                excluded.add(device)

    # Loader console settings can identify comconsole even when kern.console is
    # terse (for example generic '/uart'). Map the configured I/O port to uartN.
    loader_console = run(["/usr/bin/kenv", "console"])
    if "comconsole" in loader_console.lower():
        com_port_text = run(["/usr/bin/kenv", "comconsole_port"])
        com_port = parse_port(com_port_text)
        if com_port is not None:
            mapped = port_to_device(com_port, uart_ports)
            if mapped:
                excluded.add(mapped)
        elif "/dev/cuau0" in discover_devices():
            # COM1 is the historical default only when comconsole is explicitly
            # active and no port value can be recovered.
            excluded.add("/dev/cuau0")

    # Newer uart(4) console tunable, e.g. hw.uart.console="io:0x2f8,br=115200".
    uart_console = run(["/usr/bin/kenv", "hw.uart.console"])
    if not uart_console:
        uart_console = run(["/sbin/sysctl", "-n", "hw.uart.console"])
    uart_port = parse_port(uart_console)
    if uart_port is not None:
        mapped = port_to_device(uart_port, uart_ports)
        if mapped:
            excluded.add(mapped)

    return excluded


def device_labels(devices: list[str], dmesg: str | None = None) -> Dict[str, str]:
    dmesg_text = run(["/sbin/dmesg"]) if dmesg is None else dmesg
    uart_ports = parse_uart_ports(dmesg_text)
    excluded = detect_console_devices(dmesg_text)
    labels: Dict[str, str] = {}
    for device in devices:
        if device in excluded:
            continue
        base = os.path.basename(device)
        if base.startswith("cuau"):
            match = re.search(r"(\d+)$", base)
            unit = int(match.group(1)) if match else -1
            details = [f"uart{unit}"] if unit >= 0 else []
            if unit >= 0:
                details.append(f"COM{unit + 1}")
            if unit in uart_ports:
                details.append(f"0x{uart_ports[unit]:x}")
            label = f"{device} ({', '.join(details)})" if details else device
        else:
            label = f"{device} (USB serial)"
        labels[device] = label
    return labels


def main() -> int:
    devices = discover_devices()
    print(json.dumps(device_labels(devices), sort_keys=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
