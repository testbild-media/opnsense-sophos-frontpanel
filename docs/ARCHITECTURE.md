# Architecture

## Data flow

```text
OPNsense WebGUI
    |
    v
MVC model: OPNsense/SophosFrontpanel
    |
    | configd template reload
    v
/usr/local/etc/sophos_frontpanel.conf
    |
    v
frontpaneld.py
    |                  \
    | local data        \ 2400 8N2
    v                    v
pluginctl/configctl     Sophos front panel
sysctl                  16x2 LCD + buttons
```

## WebGUI / MVC

The plugin uses:

- `IndexController.php` for the page route
- `forms/general.xml` for the settings form
- `SettingsController.php` for mutable model operations
- `ServiceController.php` for service/status/check/reconfigure actions
- `SophosFrontpanel.xml` for configuration fields and validation
- ACL and Menu XML for OPNsense integration
- `index.volt` for the page view

## Configuration boundary

The daemon does not parse `/conf/config.xml` directly. The MVC model remains the
source of configuration data and OPNsense renders the daemon-specific file:

```text
/usr/local/etc/sophos_frontpanel.conf
```

This keeps backend runtime parsing small and separates OPNsense's persistent
configuration format from the daemon's INI-style runtime configuration.

## Backend actions

`actions_sophos_frontpanel.conf` exposes configd actions for:

- start
- stop
- restart
- status
- check
- serial device discovery

The WebGUI service controller uses these actions rather than spawning arbitrary
commands directly.

## Serial ownership

`frontpaneld` opens the callout device exclusively and attempts `TIOCEXCL` where
available. There must be only one owner of the front-panel UART.

## Button polling

The panel does not spontaneously emit key events. The daemon sends `FE 06`,
parses the `FD xx` reply and performs edge detection. A held key therefore does
not repeatedly change pages.

Every poll is followed by the mandatory LCD-state restore sequence documented
in `Protocol-Reference.md`.

## LCD renderer

All pages are generated as two strings with a hard maximum of 16 printable
ASCII characters each. Before transport, `ascii16()` pads each row to exactly
16 bytes. A NUL terminator is never sent.

The tests in `tools/test-display-layout.py` cover normal and edge-case values,
including long interface descriptions, long device names, full IPv4 addresses,
IPv6 compaction and large memory sizes.
