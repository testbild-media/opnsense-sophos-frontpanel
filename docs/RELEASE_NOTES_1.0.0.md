# OPNsense Sophos Frontpanel v1.0.0

First public release of the native OPNsense plugin for the original Sophos
SG/XG chassis front panel.

## Highlights

- pkg-managed OPNsense integration
- WebGUI under **Services -> Sophos Frontpanel**
- tested Sophos SG330 Rev.1 front-panel UART support
- 16x2 LCD output with strict layout enforcement
- UP/DOWN/ENTER/ESC button support
- dynamic serial-device selection with console exclusion
- WAN/LAN multi-select
- Description/Identifier display mode
- right-aligned physical interface device names
- CPU/load, RAM, uptime and gateway pages
- native package build on OPNsense
- installation verification and offline regression tests

## Tested platform

```text
Sophos SG330 Rev.1
OPNsense 26.7
FreeBSD 15.1-RELEASE-p1
Frontpanel UART: /dev/cuau1 / uart1 / 0x2f8 / IRQ 3
2400 8N2
```

## Note for development-build users

Systems that previously ran private/local 1.1.x development packages can move
to this public 1.0.0 release with `tools/install-package.sh`. The public package
number intentionally restarts at 1.0.0, and the MVC schema version is also
1.0.0 for the first public release.
