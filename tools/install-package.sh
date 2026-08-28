#!/bin/sh
set -eu

NAME=os-sophos-frontpanel
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VERSION=$(cat "$ROOT/VERSION")
PKG=/usr/local/sbin/pkg

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: run as root on OPNsense." >&2
    exit 1
fi

PACKAGE=$(find "$ROOT/packages" -maxdepth 1 -type f \( -name "${NAME}-${VERSION}.pkg" -o -name "${NAME}-${VERSION}.txz" \) | head -n 1 || true)
if [ -z "$PACKAGE" ]; then
    echo "ERROR: package not found. Run: sh tools/build-package.sh" >&2
    exit 1
fi

if "$PKG" info -e "$NAME" >/dev/null 2>&1; then
    echo "Removing previously installed $NAME before reinstall..."
    "$PKG" delete -fy "$NAME"
fi

echo "Installing $PACKAGE ..."
"$PKG" add -f "$PACKAGE"

echo
echo "Installed package:"
"$PKG" info "$NAME"
echo
echo "Owned form file:"
"$PKG" which /usr/local/opnsense/mvc/app/controllers/OPNsense/SophosFrontpanel/forms/general.xml || true
