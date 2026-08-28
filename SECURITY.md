# Security Policy

This plugin runs on a firewall and opens a local hardware serial device, so
security reports should be treated carefully.

## Supported versions

Only the latest public release is supported for security fixes.

## Reporting

Do not include credentials, API keys, full OPNsense configuration backups or
other secrets in a public issue. For vulnerabilities that would expose firewall
security boundaries, use a private repository security advisory once the
repository is hosted on GitHub.

## Scope notes

The daemon is designed to:

- run locally on OPNsense
- use no external network listener
- use no third-party Python package
- open only a validated serial callout device
- consume OPNsense data through local backend/system interfaces
