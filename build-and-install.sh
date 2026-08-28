#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PKG=/usr/local/sbin/pkg

# Always build the replacement package before touching an installed version.
sh "$ROOT/tools/build-package.sh"

if [ ! -x "$PKG" ] || ! "$PKG" info -e os-sophos-frontpanel >/dev/null 2>&1; then
    # Only use legacy cleanup when no pkg-managed version exists.
    if [ -e /usr/local/opnsense/scripts/sophos_frontpanel ] || \
       [ -e /usr/local/opnsense/mvc/app/controllers/OPNsense/SophosFrontpanel ]; then
        sh "$ROOT/tools/remove-legacy.sh"
    fi
fi

sh "$ROOT/tools/install-package.sh"

echo
echo "Sophos Frontpanel native OPNsense plugin installation complete."
echo "Open: Services -> Sophos Frontpanel"
