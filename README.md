# OPNsense Sophos Frontpanel

Native OPNsense integration for the original front panel used in Sophos SG/XG
appliances. The plugin controls the **16x2 LCD** and the four chassis buttons
(**UP / DOWN / ENTER / ESC**) through the internal RS232 UART.

> **Project status:** community plugin, public release **v1.0.0**. Hardware-tested
> on a **Sophos SG330 Rev.1** running **OPNsense 26.7** on bare metal.

This repository is independent from Sophos and OPNsense/Deciso. See
[NOTICE.md](NOTICE.md).

Repository: [https://github.com/testbild-media/opnsense-sophos-frontpanel](https://github.com/testbild-media/opnsense-sophos-frontpanel)

[Deutsche Dokumentation](README.de.md)

## Features

- Native OPNsense MVC page under **Services -> Sophos Frontpanel**
- pkg-managed `os-sophos-frontpanel` package
- Dynamic serial-device dropdown
  - detects `/dev/cuau*` and `/dev/cuaU*`
  - excludes serial ports actively used as kernel/loader/login consoles
- Hard 16x2 LCD rendering boundary
  - every row is composed for at most 16 visible characters
  - serial writes are padded to exactly 16 bytes
  - no NUL terminator is appended
- Configurable LCD title, limited to 16 characters in browser and backend model
- Multi-select WAN and LAN interface groups
- Per group choice between OPNsense **Description** and **Identifier**
- Physical FreeBSD interface device right-aligned in the header
  - example: `WANSL       igb2`
- IPv4 status pages for every selected WAN/LAN interface
- CPU, load, RAM and uptime pages
- Gateway status pages
- Automatic page rotation
- Front-panel button navigation
- No third-party Python modules
- Local OPNsense-native package builder using `pkg create`
- Offline regression tests for 16x2 layout, MVC schema and UART console filtering

## Confirmed hardware

| Component | Confirmed value |
|---|---|
| Appliance | Sophos SG330 Rev.1 |
| OPNsense | 26.7 |
| FreeBSD base | 15.1-RELEASE-p1 |
| Frontpanel UART | `uart1`, I/O `0x2f8`, IRQ 3 |
| Callout device | `/dev/cuau1` |
| LCD | 16 columns x 2 rows |
| Buttons | UP, DOWN, ENTER, ESC |
| Serial protocol | 2400 baud, 8N2, no flow control |

Other Sophos SG/XG models may use the same panel/protocol, but are **not claimed
as tested** unless listed above.

## LCD examples

Interface page using OPNsense Description:

```text
WANSL       igb2
100.64.12.34
```

System page:

```text
CPU  12% L  0.2
MEM 34% 4.1G/12G
```

The 16-column limit is treated as part of the UI contract, not as a final
truncation step.

## Quick installation

The safest standalone-repository workflow is to build the native package **on
the OPNsense firewall itself**.

1. Download a source release and copy/extract it on the firewall, e.g. under
   `/root/opnsense-sophos-frontpanel`.
2. Build and install:

```sh
cd /root/opnsense-sophos-frontpanel
sh build-and-install.sh
```

3. Verify:

```sh
pkg info os-sophos-frontpanel
sh tools/verify-install.sh
```

4. Open **Services -> Sophos Frontpanel**, select the serial device, choose WAN
   and LAN interfaces, then **Save & Apply**.

See [docs/INSTALLATION.md](docs/INSTALLATION.md) for the full procedure,
including upgrades from the pre-public development packages.

## Button controls

| Button | Action |
|---|---|
| UP | Previous page |
| DOWN | Next page |
| ENTER | Toggle automatic page rotation |
| ESC | Return to home page |

The controller does not emit unsolicited button events. The daemon polls the
button state and applies edge detection so a held key produces one UI event.

## Serial protocol summary

- 2400 baud, 8 data bits, no parity, 2 stop bits
- `FE 01` clear LCD
- `FE 02` home / reset display shift
- `FE 06` poll buttons
- `FE 0C` display on, cursor off, blink off
- `FE 80` position line 1
- `FE C0` position line 2

Button responses:

- `FD BF` no key
- `FD BE` UP
- `FD BD` DOWN
- `FD BB` ENTER
- `FD B7` ESC

After every `FE 06` poll the daemon sends `FE 02`, waits ~40 ms, sends `FE 0C`
and waits ~20 ms. This compensates for a front-panel controller side effect
that otherwise shifts the visible LCD state.

Full details: [docs/Protocol-Reference.md](docs/Protocol-Reference.md). Hardware notes: [docs/HARDWARE.md](docs/HARDWARE.md).

## Configuration

The WebGUI exposes:

- Enable
- Serial device
- LCD title (1-16 ASCII characters)
- WAN interfaces (multi-select)
- WAN: show Description
- LAN interfaces (multi-select)
- LAN: show Description
- Button polling interval
- Live value refresh
- Auto rotation
- Rotation interval
- Log level

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

## Diagnostics

```sh
configctl sophos_frontpanel status
configctl sophos_frontpanel check
configctl sophos_frontpanel restart
configctl sophos_frontpanel list_serial_devices

tail -f /var/log/sophos_frontpanel.log
cat /usr/local/etc/sophos_frontpanel.conf
```

For a complete installation check:

```sh
sh tools/verify-install.sh
```

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

## Repository layout

```text
.
├── .github/                         GitHub CI, issue and PR templates
├── docs/                            installation, configuration, protocol, dev docs
├── src/
│   ├── etc/                         rc.d, syshook and service registration
│   └── opnsense/
│       ├── mvc/                     MVC model, form, API, ACL, menu and view
│       ├── scripts/sophos_frontpanel/
│       │   ├── frontpaneld.py       LCD/button daemon
│       │   └── list_serial_devices.py
│       └── service/                 configd actions and template rendering
├── tools/                           local package builder, installer and tests
├── Makefile                         OPNsense plugins-tree Makefile
├── VERSION                          public package version
└── build-and-install.sh             convenience local build/install entry point
```

## Development and official plugin-tree build

The source layout follows the OPNsense plugins framework. OPNsense documents
plugin-local targets such as `lint`, `style`, `package`, `install` and
`upgrade` when the plugin lives under the official plugins repository tree.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md),
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md),
[docs/RELEASING.md](docs/RELEASING.md) and
[docs/GITHUB.md](docs/GITHUB.md).

## Versioning note

The public package starts at **1.0.0**. Earlier 1.1.x packages were private
hardware-development builds and are not public release history.

For the public v1.0.0 release, the MVC model schema is also **1.0.0**.
Package version and MVC schema version are intentionally kept aligned for this
first public release. Future schema migrations may advance the model version as
needed.

## License

BSD 2-Clause License. See [LICENSE](LICENSE).
