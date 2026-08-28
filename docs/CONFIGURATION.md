# Configuration

The plugin is configured under **Services -> Sophos Frontpanel**.

## Enable

Starts/stops the daemon as part of Save & Apply and at boot.

## Serial device

Dynamic dropdown populated by `configd`.

Recognized callout device families:

- motherboard UARTs: `/dev/cuau*`
- USB serial adapters: `/dev/cuaU*`

The discovery helper excludes ports it can identify as actively used by a
kernel, loader or login console. A FreeBSD UART `flags 0x10` capability alone
is not treated as proof that the UART is actively in use as the console.

## LCD title

Home-page title. The physical display is 16 columns wide, therefore the field
accepts **1 to 16 simple ASCII characters**. The limit is enforced both in the
browser and in the MVC model.

## WAN interfaces / LAN interfaces

Both are native OPNsense multi-select fields. Every selected interface receives
its own LCD page.

Example selections:

```text
WAN group: WAN, WANSL
LAN group: LAN, TECHNIK
```

## WAN/LAN: show Description

Enabled:

```text
WANSL       igb2
100.64.12.34
```

Disabled (Identifier mode):

```text
OPT1        igb2
100.64.12.34
```

The left label is shortened first if required; the real FreeBSD device is kept
right-aligned where possible.

## Button polling interval

Allowed range: **100-1000 ms**.

100 ms is the tested/default value. The panel requires polling; keys are not
sent asynchronously.

## Live value refresh

Allowed range: **2-60 seconds**.

The daemon samples live OPNsense/FreeBSD values on this interval but writes an
LCD frame only when the visible 16x2 content changed.

## Auto rotation / rotation interval

Automatic page change can be enabled in the WebGUI and toggled at runtime with
ENTER. Rotation interval range: **2-60 seconds**.

## Log level

Available daemon levels are Debug, Info, Warning and Error. Debug should be
used only while diagnosing problems.
