#!/bin/sh
set -eu

PREFIX=/usr/local
PKG=/usr/local/sbin/pkg

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: run as root on OPNsense." >&2
    exit 1
fi

if [ ! -d /usr/local/opnsense ] || [ ! -f /conf/config.xml ]; then
    echo "ERROR: this does not look like an OPNsense installation." >&2
    exit 1
fi

echo "Stopping Sophos Frontpanel if it is running..."
if [ -x "$PREFIX/etc/rc.d/sophos_frontpanel" ]; then
    "$PREFIX/etc/rc.d/sophos_frontpanel" stop >/dev/null 2>&1 || true
fi

# If a pkg-managed test build already exists, let pkg remove its own files first.
if [ -x "$PKG" ] && "$PKG" info -e os-sophos-frontpanel >/dev/null 2>&1; then
    echo "Removing existing pkg-managed os-sophos-frontpanel..."
    "$PKG" delete -fy os-sophos-frontpanel
fi

echo "Removing files from the earlier manual pre-pkg development installation..."
rm -f "$PREFIX/etc/rc.d/sophos_frontpanel"
rm -f "$PREFIX/etc/inc/plugins.inc.d/sophos_frontpanel.inc"
rm -f "$PREFIX/etc/rc.syshook.d/start/50-sophos-frontpanel"
rm -f "$PREFIX/etc/sophos_frontpanel.conf"
rm -rf "$PREFIX/opnsense/scripts/sophos_frontpanel"
rm -f "$PREFIX/opnsense/service/conf/actions.d/actions_sophos_frontpanel.conf"
rm -rf "$PREFIX/opnsense/service/templates/OPNsense/SophosFrontpanel"
rm -rf "$PREFIX/opnsense/mvc/app/controllers/OPNsense/SophosFrontpanel"
rm -rf "$PREFIX/opnsense/mvc/app/models/OPNsense/SophosFrontpanel"
rm -rf "$PREFIX/opnsense/mvc/app/views/OPNsense/SophosFrontpanel"
rm -f "$PREFIX/opnsense/version/sophos-frontpanel"
rm -f /var/run/sophos_frontpanel.pid /var/run/sophos_frontpanel.status.json
rm -f /tmp/opnsense_menu_cache.xml /tmp/opnsense_acl_cache.json

# Keep any old XML settings in /conf/config.xml intentionally. Configuration
# backups remain valid and no unrelated firewall configuration is touched.
if [ -x /usr/local/etc/rc.d/configd ]; then
    /usr/local/etc/rc.d/configd restart >/dev/null 2>&1 || true
fi
if [ -x /usr/local/sbin/pluginctl ]; then
    /usr/local/sbin/pluginctl -cq cache_flush >/dev/null 2>&1 || true
fi

echo "Legacy Sophos Frontpanel files removed."
echo "Existing settings in /conf/config.xml were intentionally preserved."
