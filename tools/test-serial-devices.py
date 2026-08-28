#!/usr/bin/env python3
"""Offline tests for dynamic serial-device discovery and console exclusion."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src/opnsense/scripts/sophos_frontpanel/list_serial_devices.py"
spec = importlib.util.spec_from_file_location("serial_devices_test", SCRIPT)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

DMESG_BASE = """\
uart: ns8250: UART FCR is broken (0x1)
uart0: <16550 or compatible> port 0x3f8-0x3ff irq 4 flags 0x10 on acpi0
uart: ns8250: UART FCR is broken (0x1)
uart1: <16550 or compatible> port 0x2f8-0x2ff irq 3 on acpi0
"""
DEVICES = ["/dev/cuau0", "/dev/cuau1", "/dev/cuaU0"]


def run_case(responses, dmesg=DMESG_BASE):
    original_run = module.run
    original_discover = module.discover_devices

    def fake_run(argv):
        key = tuple(argv)
        return responses.get(key, "")

    try:
        module.run = fake_run
        module.discover_devices = lambda dev_dir="/dev": list(DEVICES)
        return module.device_labels(list(DEVICES), dmesg)
    finally:
        module.run = original_run
        module.discover_devices = original_discover


# uart0 flags 0x10 means potential console support, not an active serial console.
labels = run_case({
    ("/sbin/sysctl", "-n", "kern.console"): "ttyv0,/uart,ucom,ttyv0",
    ("/bin/ps", "ax", "-o", "command="): "/usr/libexec/getty Pc ttyv0",
    ("/usr/bin/kenv", "console"): "vidconsole",
})
assert "/dev/cuau0" in labels, labels
assert "/dev/cuau1" in labels, labels
assert "/dev/cuaU0" in labels, labels
assert labels["/dev/cuau0"].endswith("uart0, COM1, 0x3f8)"), labels
assert labels["/dev/cuau1"].endswith("uart1, COM2, 0x2f8)"), labels

# Explicit kernel-console message excludes uart0.
labels = run_case({
    ("/sbin/sysctl", "-n", "kern.console"): "ttyv0,/uart,ucom,ttyv0",
    ("/bin/ps", "ax", "-o", "command="): "/usr/libexec/getty Pc ttyv0",
    ("/usr/bin/kenv", "console"): "vidconsole",
}, DMESG_BASE + "uart0: console (115200,n,8,1)\n")
assert "/dev/cuau0" not in labels, labels
assert "/dev/cuau1" in labels, labels

# Loader comconsole on COM2 excludes cuau1.
labels = run_case({
    ("/sbin/sysctl", "-n", "kern.console"): "ttyv0,/uart,ucom,ttyv0",
    ("/bin/ps", "ax", "-o", "command="): "/usr/libexec/getty Pc ttyv0",
    ("/usr/bin/kenv", "console"): "comconsole,vidconsole",
    ("/usr/bin/kenv", "comconsole_port"): "0x2f8",
})
assert "/dev/cuau0" in labels, labels
assert "/dev/cuau1" not in labels, labels

# A running serial getty also makes the port unavailable.
labels = run_case({
    ("/sbin/sysctl", "-n", "kern.console"): "ttyv0",
    ("/bin/ps", "ax", "-o", "command="): "/usr/libexec/getty std.115200 ttyu1",
    ("/usr/bin/kenv", "console"): "vidconsole",
})
assert "/dev/cuau1" not in labels, labels

# New uart(4) hw.uart.console tunable maps the I/O address back to uartN.
labels = run_case({
    ("/sbin/sysctl", "-n", "kern.console"): "ttyv0,/uart,ucom,ttyv0",
    ("/bin/ps", "ax", "-o", "command="): "/usr/libexec/getty Pc ttyv0",
    ("/usr/bin/kenv", "console"): "vidconsole",
    ("/usr/bin/kenv", "hw.uart.console"): "io:0x3f8,br=115200",
})
assert "/dev/cuau0" not in labels, labels
assert "/dev/cuau1" in labels, labels

print("OK: serial dropdown discovers callout devices and excludes active console UARTs")
