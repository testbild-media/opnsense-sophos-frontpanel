#!/usr/bin/env python3
"""Offline sanity tests for the physical Sophos 16x2 LCD layout."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAEMON = ROOT / "src/opnsense/scripts/sophos_frontpanel/frontpaneld.py"
spec = importlib.util.spec_from_file_location("frontpaneld_test", DAEMON)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def assert_frame(name, line1, line2):
    assert len(line1) <= module.LCD_WIDTH, (name, line1, len(line1))
    assert len(line2) <= module.LCD_WIDTH, (name, line2, len(line2))
    row1 = module.ascii16(line1)
    row2 = module.ascii16(line2)
    assert len(row1) == module.LCD_WIDTH, (name, row1, len(row1))
    assert len(row2) == module.LCD_WIDTH, (name, row2, len(row2))
    assert b"\x00" not in row1 + row2, (name, row1, row2)


cfg = module.Config(
    wan_interfaces=["wan", "opt1"],
    lan_interfaces=["lan", "opt2"],
    wan_use_description=True,
    lan_use_description=True,
)
sampler = module.SystemSampler(cfg)
sampler.hostname = "OPNsense-SG330-VERY-LONG-HOSTNAME"
sampler.interfaces = {
    "wan": {"identifier": "WAN", "description": "WAN", "device": "igb1", "address": "255.255.255.255"},
    "opt1": {"identifier": "OPT1", "description": "WANSL", "device": "igb0", "address": "100.64.12.34"},
    "lan": {"identifier": "LAN", "description": "LAN", "device": "igb2", "address": "192.168.100.254"},
    "opt2": {"identifier": "OPT2", "description": "TECHNIK", "device": "igb3", "address": "10.10.10.1"},
}
sampler.uptime_seconds = 987654321

cases = [
    (0, 0, 0.0, 12.0, 0.0),
    (12, 34, 4.1, 12.0, 0.18),
    (100, 100, 12.0, 12.0, 99.9),
    (87, 64, 82.0, 128.0, 12.34),
    (100, 98, 1000.0, 1024.0, 99.9),
    (100, 99, 8192.0, 16384.0, 99.9),
]
for cpu, mem, used, total, load in cases:
    sampler.cpu_percent = cpu
    sampler.ram_percent = mem
    sampler.ram_used_bytes = int(used * (1024 ** 3))
    sampler.ram_total_bytes = int(total * (1024 ** 3))
    sampler.load1 = load
    sampler.gateways = [
        {
            "name": "WAN_DHCP_WITH_A_VERY_LONG_GATEWAY_NAME",
            "status": "Online",
            "address": "192.168.100.254",
        },
        {
            "name": "IPV6_GATEWAY_WITH_A_VERY_LONG_NAME",
            "status": "Offline",
            "address": "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
        },
        {
            "name": "WAITING_GATEWAY",
            "status": "Pending",
            "address": "10.255.255.254",
        },
    ]
    pages = sampler.pages("1234567890ABCDEF")
    for name, line1, line2 in pages:
        assert_frame(name, line1, line2)

# Critical known representations.
sampler.cpu_percent = 12
sampler.ram_percent = 34
sampler.ram_used_bytes = int(4.1 * (1024 ** 3))
sampler.ram_total_bytes = int(12 * (1024 ** 3))
sampler.load1 = 0.2
load_page = next(page for page in sampler.pages("OPNsense SG330") if page[0] == "LOAD")
assert load_page[1] == "CPU  12% L  0.2", load_page
assert load_page[2] == "MEM 34% 4.1G/12G", load_page

pages = sampler.pages("OPNsense SG330")
wan_main = next(page for page in pages if page[0] == "WAN:wan")
wan_opt = next(page for page in pages if page[0] == "WAN:opt1")
lan_main = next(page for page in pages if page[0] == "LAN:lan")
lan_opt = next(page for page in pages if page[0] == "LAN:opt2")
assert wan_main[1] == "WAN         igb1", wan_main
assert wan_main[2] == "255.255.255.255", wan_main
assert wan_opt[1] == "WANSL       igb0", wan_opt
assert wan_opt[2] == "100.64.12.34", wan_opt
assert lan_main[1] == "LAN         igb2", lan_main
assert lan_main[2] == "192.168.100.254", lan_main
assert lan_opt[1] == "TECHNIK     igb3", lan_opt
assert lan_opt[2] == "10.10.10.1", lan_opt
assert "WAN WAN" not in [p[1] for p in pages]
assert "LAN LAN" not in [p[1] for p in pages]

# Toggle to identifiers: OPT1/OPT2 must replace Description while the real device remains.
cfg.wan_use_description = False
cfg.lan_use_description = False
pages_identifier = sampler.pages("OPNsense SG330")
wan_opt_identifier = next(page for page in pages_identifier if page[0] == "WAN:opt1")
lan_opt_identifier = next(page for page in pages_identifier if page[0] == "LAN:opt2")
assert wan_opt_identifier[1] == "OPT1        igb0", wan_opt_identifier
assert lan_opt_identifier[1] == "OPT2        igb3", lan_opt_identifier

# Header alignment and clipping are deterministic and always fit 16 columns.
assert module.interface_header("WANSL", "igb0") == "WANSL       igb0"
assert module.interface_header("VERY-LONG-DESCRIPTION", "vlan0.1234") == "VERY- vlan0.1234"

gw_page = next(page for page in pages if page[0] == "GW")
assert gw_page[1].endswith(" OK"), gw_page
assert gw_page[2] == "192.168.100.254", gw_page

assert module.compact_address("2001:0db8:85a3:0000:0000:8a2e:0370:7334") == "2001:0d..70:7334"
assert module.lcd_text("äöüß", 16) == "aeoeuess"

# Verify OPNsense metadata parsing. The configured device must win, and a
# JSON null returned by pluginctl -4 must never render as the literal "None".
original_run_command = module.run_command
def fake_run_command(argv, timeout=1.5):
    if argv == ["/usr/local/sbin/pluginctl", "-g", "interfaces.opt1.if"]:
        return "igb2"
    if argv == ["/usr/local/sbin/pluginctl", "-g", "interfaces.opt1.descr"]:
        return "WANSL"
    if argv[:3] == ["/usr/local/sbin/pluginctl", "-4", "opt1"]:
        return '{"opt1":[{"address":"100.64.12.34","device":null,"interface":"opt1","family":"inet"}]}'
    return ""
module.run_command = fake_run_command
try:
    details = module.SystemSampler(module.Config())._interface_details("opt1")
finally:
    module.run_command = original_run_command
assert details == {
    "identifier": "OPT1",
    "description": "WANSL",
    "device": "igb2",
    "address": "100.64.12.34",
}, details
assert "None" not in module.interface_header(details["description"], details["device"])

print("OK: all generated LCD frames fit exactly 16x2; interface Description/Identifier and device alignment verified")
