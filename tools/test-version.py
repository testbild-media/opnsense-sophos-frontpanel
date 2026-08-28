#!/usr/bin/env python3
"""Repository-level public version consistency checks."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
assert re.fullmatch(r"\d+\.\d+\.\d+", version), version

makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
assert "PLUGIN_VERSION!= cat ${.CURDIR}/VERSION" in makefile

build = (ROOT / "tools/build-package.sh").read_text(encoding="utf-8")
install = (ROOT / "tools/install-package.sh").read_text(encoding="utf-8")
assert 'VERSION=$(cat "$ROOT/VERSION")' in build
assert 'VERSION=$(cat "$ROOT/VERSION")' in install
assert 'PROJECT_URL=${PROJECT_URL:-https://github.com/testbild-media/opnsense-sophos-frontpanel}' in build

readme = (ROOT / "README.md").read_text(encoding="utf-8")
assert f"public release **v{version}**" in readme

changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
assert f"## [{version}]" in changelog

# Public package version and MVC model schema are aligned.
model = (ROOT / "src/opnsense/mvc/app/models/OPNsense/SophosFrontpanel/SophosFrontpanel.xml").read_text(encoding="utf-8")
assert f"<version>{version}</version>" in model

print(f"OK: public package version and MVC schema are both {version}")
