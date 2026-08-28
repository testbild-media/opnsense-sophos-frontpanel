# Changelog

All notable public changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses semantic versioning for public package releases.

## [1.0.0] - 2026-08-28

### Added

- Native pkg-managed OPNsense plugin integration.
- OPNsense MVC settings page under **Services -> Sophos Frontpanel**.
- configd actions, configuration template, rc.d integration, service registration
  and boot syshook.
- Hardware-tested Sophos front-panel protocol at 2400 8N2.
- Support for the original 16x2 LCD and UP/DOWN/ENTER/ESC buttons.
- Mandatory post-button-poll LCD restore sequence.
- Dynamic serial-device dropdown with active-console exclusion.
- Browser- and model-side 16-character LCD title limit.
- WAN and LAN multi-select fields.
- Per-group switch between OPNsense interface Description and Identifier.
- Right-aligned physical FreeBSD device names on WAN/LAN pages.
- WAN/LAN IPv4, CPU/load, RAM, uptime and gateway pages.
- Exact 16x2 rendering checks and NUL-byte prevention.
- Local native package builder using the OPNsense `pkg` toolchain.
- Installation verification and legacy-development-build cleanup tools.
- Offline regression tests and GitHub Actions CI.

### Fixed

- Avoid duplicate labels such as `WAN WAN` / `LAN LAN`.
- Preserve complete IPv4 addresses where possible on 16-column pages.
- Prevent JSON `null` runtime device values from appearing as literal `None`.
- Prefer configured OPNsense interface device metadata (`interfaces.<id>.if`) and
  use runtime device metadata only as a valid-string fallback.
- Keep memory percentage and units visible within the 16-character boundary.

### Compatibility

- Confirmed on Sophos SG330 Rev.1 with OPNsense 26.7 / FreeBSD 15.1.
- Public package version and MVC model schema both start at 1.0.0.
