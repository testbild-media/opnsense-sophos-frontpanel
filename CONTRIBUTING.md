# Contributing

Contributions are welcome, especially hardware reports for additional Sophos
SG/XG models.

## Before opening a pull request

- Keep the physical 16x2 display limit explicit in all new pages.
- Add/update regression tests for new rendering logic.
- Do not append NUL bytes to LCD strings.
- Do not remove the post-`FE 06` restore sequence.
- Do not read or rewrite unrelated OPNsense configuration directly.
- Keep the serial device exclusive to the daemon.
- Run the offline tests and syntax checks described in `docs/DEVELOPMENT.md`.

## Hardware reports

For new appliance support, include:

- exact Sophos model/revision
- OPNsense version
- output of `dmesg | grep -i uart`
- relevant `/dev/cuau*` / `/dev/cuaU*` entries
- confirmed frontpanel callout device
- whether LCD and all four buttons were tested

Do not post private IPs, credentials, API keys, configuration backups or other
sensitive firewall data.

## Pull requests

Keep changes focused. Explain behavioral changes, hardware impact and how the
change was tested. If a change affects the MVC schema, document whether a model
migration is required.
