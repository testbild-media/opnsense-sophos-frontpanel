# Releasing

## Versioning

Public releases use semantic versioning and the canonical package version is in:

```text
VERSION
```

The MVC schema version is separate and must only change when configuration
schema migration semantics require it.

## Release checklist

1. Update `VERSION`.
2. Update `CHANGELOG.md`.
3. Run the offline tests:

```sh
python3 tools/test-display-layout.py
python3 tools/test-serial-devices.py
python3 tools/test-plugin-schema.py
python3 tools/test-version.py
```

4. Run PHP/XML/shell syntax checks (or let GitHub Actions do so).
5. On a test OPNsense appliance:

```sh
sh tools/build-package.sh
sh tools/install-package.sh
sh tools/verify-install.sh
```

6. Test LCD rendering and all four physical buttons.
7. Commit the release.
8. Tag it as `vX.Y.Z` and create the GitHub Release.

## Binary package policy

The standalone local builder intentionally creates the native `.pkg` **on the
OPNsense/FreeBSD system itself**. Do not present a package assembled on Linux as
a native OPNsense package.

A distributable binary package should be produced in a compatible OPNsense
build environment or via the official OPNsense plugin build framework.
