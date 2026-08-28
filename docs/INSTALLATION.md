# Installation

## Requirements

- OPNsense appliance with a supported/compatible Sophos front panel
- root shell access for package creation/installation
- Python 3 as shipped with current OPNsense
- a free serial callout device corresponding to the front panel

Confirmed reference system:

```text
Sophos SG330 Rev.1
OPNsense 26.7
FreeBSD 15.1-RELEASE-p1
Frontpanel: /dev/cuau1 (uart1, 0x2f8, IRQ 3)
```

## 1. Confirm the UARTs

On OPNsense:

```sh
dmesg | grep -i uart
ls -la /dev | grep -E 'cuau|cuaU|ttyu|ttyU'
sysctl kern.console
```

On the confirmed SG330 Rev.1 the relevant UART appears as:

```text
uart1: <16550 or compatible> port 0x2f8-0x2ff irq 3 on acpi0
/dev/cuau1
```

Do not use a UART that is actively assigned to the system/login console. The
plugin's serial dropdown attempts to detect and exclude such devices.

## 2. Copy the repository/source release to OPNsense

For example:

```text
/root/opnsense-sophos-frontpanel/
```

The top-level directory must contain `VERSION`, `src/`, `tools/` and
`build-and-install.sh`.

## 3. Build and install the native package

Recommended standalone-repository method:

```sh
cd /root/opnsense-sophos-frontpanel
sh build-and-install.sh
```

This performs the regression tests first, stages the `src/` tree and builds a
native `os-sophos-frontpanel-<version>.pkg` with OPNsense's own `pkg create`.
It then installs the package through `pkg add`.

Build and install can also be run separately:

```sh
sh tools/build-package.sh
ls -lh packages/
sh tools/install-package.sh
```

## 4. Verify package ownership

```sh
pkg info os-sophos-frontpanel
pkg which /usr/local/opnsense/mvc/app/controllers/OPNsense/SophosFrontpanel/forms/general.xml
```

The form file should be owned by `os-sophos-frontpanel`.

Run the full verification:

```sh
sh tools/verify-install.sh
```

## 5. Configure in the WebGUI

Open:

```text
Services -> Sophos Frontpanel
```

Suggested reference settings for an SG330 Rev.1:

```text
Enable:                  on
Serial device:           /dev/cuau1
LCD title:               OPNsense SG330
WAN interfaces:          select required WAN interfaces
LAN interfaces:          select required LAN interfaces
WAN show Description:    on
LAN show Description:    on
Button polling interval: 100 ms
Live value refresh:      2 s
Auto rotation:           on
Rotation interval:       5 s
Log level:               Info
```

Press **Save & Apply**.

## 6. Verify the daemon

```sh
configctl sophos_frontpanel status
configctl sophos_frontpanel check
```

Expected UART check format:

```text
UART /dev/cuau1: OK (2400 8N2)
```

## Upgrade from the pre-public 1.1.x development packages

The public project intentionally starts at package version **1.0.0** even though
some hardware-development systems may already have a locally built 1.1.x
package installed.

`tools/install-package.sh` removes an installed `os-sophos-frontpanel` package
before adding the newly built public package, so the lower public package number
does not block installation. Plugin settings under `/conf/config.xml` are not
deleted by package removal.

The public v1.0.0 package also uses MVC schema version 1.0.0. Systems that ran
private development builds should keep a configuration backup before switching
to the public release.

Recommended transition:

```sh
cd /root/opnsense-sophos-frontpanel
sh tools/build-package.sh
sh tools/install-package.sh
sh tools/verify-install.sh
```

## Uninstall

```sh
pkg delete os-sophos-frontpanel
```

The generated runtime config and PID/status files are removed by the package
hooks. OPNsense MVC configuration data is deliberately not destructively edited
from `/conf/config.xml` by the uninstall hook.
