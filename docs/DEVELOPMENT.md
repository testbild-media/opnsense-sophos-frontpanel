# Development

## Architecture

The project follows the normal OPNsense plugin split:

- MVC model and WebGUI under `src/opnsense/mvc/`
- backend/configd actions under `src/opnsense/service/`
- daemon/helper scripts under `src/opnsense/scripts/sophos_frontpanel/`
- service registration and boot hooks under `src/etc/`

The daemon intentionally does **not** parse `/conf/config.xml` directly.
OPNsense MVC settings are rendered through the configd template system to:

```text
/usr/local/etc/sophos_frontpanel.conf
```

The daemon reads that rendered configuration.

## Package version and MVC schema version

`VERSION` contains the public package version. For the v1.0.0 release, the MVC
`<version>` tag in `SophosFrontpanel.xml` is also 1.0.0.

The repository test requires both values to match. If a future release introduces
a real configuration schema migration, update the model version and migration
logic deliberately.

## Offline tests

These tests do not require OPNsense:

```sh
python3 tools/test-display-layout.py
python3 tools/test-serial-devices.py
python3 tools/test-plugin-schema.py
python3 tools/test-version.py
```

Additional syntax checks:

```sh
python3 -m py_compile \
  src/opnsense/scripts/sophos_frontpanel/frontpaneld.py \
  src/opnsense/scripts/sophos_frontpanel/list_serial_devices.py
```

On systems with PHP installed:

```sh
find src -name '*.php' -print -exec php -l {} \;
```

XML can be parsed with Python's standard library or `xmllint`.

## OPNsense plugins-tree build

For the official OPNsense plugin framework, place the repository contents under
an OPNsense plugins category directory, for example:

```text
/usr/plugins/sysutils/sophos-frontpanel/
```

The top-level Makefile includes `../../Mk/plugins.mk` and can then use the normal
plugin targets such as:

```sh
make lint
make style
make package
```

OPNsense's plugins repository documents `clean`, `collect`, `install`, `lint`,
`package`, `upgrade`, `remove`, `style` and `sweep` as plugin-local targets.

## Local hardware development

For iterative development on a dedicated test firewall:

```sh
sh tools/build-package.sh
sh tools/install-package.sh
sh tools/verify-install.sh
```

Avoid manually copying individual MVC files into `/usr/local`; pkg ownership is
part of the installation contract.

## Coding rules specific to the front panel

1. The visible LCD is always exactly 16x2.
2. Compose content to <=16 characters before serial transport.
3. `ascii16()` must return exactly 16 bytes and never contain `0x00`.
4. Button polling must always restore LCD state after `FE 06`.
5. Only one process may own the serial device.
6. Held keys generate one UI event through edge detection.
7. Avoid rewriting unchanged LCD frames.
8. OPNsense data should be obtained through supported local interfaces such as
   configd/pluginctl/sysctl rather than by scraping the WebGUI.
