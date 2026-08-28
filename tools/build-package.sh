#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VERSION=$(cat "$ROOT/VERSION")
NAME=os-sophos-frontpanel
PLUGIN_NAME=sophos-frontpanel
COMMENT="Sophos SG/XG chassis LCD and button integration"
MAINTAINER=${PLUGIN_MAINTAINER:-sophos-frontpanel@users.noreply.github.com}
PROJECT_URL=${PROJECT_URL:-https://github.com/testbild-media/opnsense-sophos-frontpanel}
PKG=/usr/local/sbin/pkg
OUTDIR="$ROOT/packages"
WORKBASE="/tmp/${NAME}-build.$$"
STAGE="$WORKBASE/stage"
META="$WORKBASE/meta"

cleanup()
{
    rm -rf "$WORKBASE"
}
trap cleanup EXIT INT TERM

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: run as root on OPNsense." >&2
    exit 1
fi
if [ ! -x "$PKG" ] || [ ! -d /usr/local/opnsense ]; then
    echo "ERROR: native OPNsense pkg tooling not found." >&2
    exit 1
fi
if [ ! -d "$ROOT/src" ]; then
    echo "ERROR: plugin src/ directory not found." >&2
    exit 1
fi

echo "Running plugin self-tests..."
PYTHONDONTWRITEBYTECODE=1 /usr/local/bin/python3 -B "$ROOT/tools/test-display-layout.py"
PYTHONDONTWRITEBYTECODE=1 /usr/local/bin/python3 -B "$ROOT/tools/test-serial-devices.py"
PYTHONDONTWRITEBYTECODE=1 /usr/local/bin/python3 -B "$ROOT/tools/test-plugin-schema.py"
PYTHONDONTWRITEBYTECODE=1 /usr/local/bin/python3 -B -c 'import pathlib; [compile(p.read_text(), str(p), "exec") for p in [pathlib.Path("'$ROOT'/src/opnsense/scripts/sophos_frontpanel/frontpaneld.py"), pathlib.Path("'$ROOT'/src/opnsense/scripts/sophos_frontpanel/list_serial_devices.py")]]'

mkdir -p "$STAGE/usr/local" "$META" "$OUTDIR"

# Stage exactly like an OPNsense plugin: src/ is rooted below /usr/local.
(cd "$ROOT/src" && tar -cf - .) | (cd "$STAGE/usr/local" && tar -xpf -)

# Ensure executable bits are correct even when the source archive was unpacked
# on a filesystem that did not preserve them.
chmod 755 "$STAGE/usr/local/etc/rc.d/sophos_frontpanel"
chmod 755 "$STAGE/usr/local/etc/rc.syshook.d/start/50-sophos-frontpanel"
chmod 755 "$STAGE/usr/local/opnsense/scripts/sophos_frontpanel/frontpaneld"
chmod 755 "$STAGE/usr/local/opnsense/scripts/sophos_frontpanel/frontpaneld.py"
chmod 755 "$STAGE/usr/local/opnsense/scripts/sophos_frontpanel/list_serial_devices.py"

# OPNsense plugin version annotation. A local package is intentionally tier 4.
ABI=$(/usr/local/sbin/opnsense-version -a 2>/dev/null || echo unknown)
ARCH=$(uname -p 2>/dev/null || uname -m)
mkdir -p "$STAGE/usr/local/opnsense/version"
cat > "$STAGE/usr/local/opnsense/version/$PLUGIN_NAME" <<EOF_VERSION
{
    "product_abi": "$ABI",
    "product_arch": "$ARCH",
    "product_conflicts": "os-sophos-frontpanel-devel",
    "product_email": "$MAINTAINER",
    "product_hash": "local",
    "product_id": "$NAME",
    "product_name": "$PLUGIN_NAME",
    "product_tier": "4",
    "product_version": "$VERSION",
    "product_website": "$PROJECT_URL"
}
EOF_VERSION

cat > "$META/+MANIFEST" <<EOF_MANIFEST
name: $NAME
version: "$VERSION"
origin: opnsense/$NAME
comment: "$COMMENT"
maintainer: "$MAINTAINER"
categories: [ "sysutils" ]
www: "$PROJECT_URL"
prefix: "/usr/local"
licenselogic: "single"
licenses: [ "BSD2CLAUSE" ]
arch: "freebsd:*:*"
abi: "FreeBSD:*:*"
annotations: {
    product_abi: "$ABI",
    product_arch: "$ARCH",
    product_conflicts: "os-sophos-frontpanel-devel",
    product_email: "$MAINTAINER",
    product_hash: "local",
    product_id: "$NAME",
    product_name: "$PLUGIN_NAME",
    product_tier: "4",
    product_version: "$VERSION",
    product_website: "$PROJECT_URL"
}
EOF_MANIFEST

cat "$ROOT/pkg-descr" > "$META/+DESC"

cat > "$META/+POST_INSTALL" <<'EOF_POST'
#!/bin/sh
set -u

# Register service hooks first, then reload configd so dynamic MVC fields can
# use this package's newly installed configd actions during model migration.
if [ -x /usr/local/etc/rc.configure_plugins ]; then
    /usr/local/etc/rc.configure_plugins POST_INSTALL >/dev/null 2>&1 || true
fi
if [ -x /usr/local/etc/rc.d/configd ]; then
    /usr/local/etc/rc.d/configd restart >/dev/null 2>&1 || true
fi
if [ -x /usr/local/opnsense/mvc/script/run_migrations.php ]; then
    /usr/local/opnsense/mvc/script/run_migrations.php OPNsense/SophosFrontpanel >/dev/null 2>&1 || true
fi
rm -f /tmp/opnsense_menu_cache.xml /tmp/opnsense_acl_cache.json
if [ -x /usr/local/sbin/pluginctl ]; then
    /usr/local/sbin/pluginctl -cq cache_flush >/dev/null 2>&1 || true
fi

# Render the plugin-specific config after configd knows the new template.
if [ -x /usr/local/sbin/configctl ]; then
    /usr/local/sbin/configctl template reload OPNsense/SophosFrontpanel >/dev/null 2>&1 || true
fi

# Start only when the MVC setting is enabled.
if [ -x /usr/local/opnsense/scripts/sophos_frontpanel/frontpaneld ] && \
   /usr/local/opnsense/scripts/sophos_frontpanel/frontpaneld --is-enabled >/dev/null 2>&1; then
    /usr/local/etc/rc.d/sophos_frontpanel start >/dev/null 2>&1 || true
fi
exit 0
EOF_POST

cat > "$META/+PRE_DEINSTALL" <<'EOF_PRE'
#!/bin/sh
if [ -x /usr/local/etc/rc.d/sophos_frontpanel ]; then
    /usr/local/etc/rc.d/sophos_frontpanel stop >/dev/null 2>&1 || true
fi
exit 0
EOF_PRE

cat > "$META/+POST_DEINSTALL" <<'EOF_POSTDE'
#!/bin/sh
rm -f /usr/local/etc/sophos_frontpanel.conf
rm -f /var/run/sophos_frontpanel.pid /var/run/sophos_frontpanel.status.json
rm -f /tmp/opnsense_menu_cache.xml /tmp/opnsense_acl_cache.json
if [ -x /usr/local/etc/rc.configure_plugins ]; then
    /usr/local/etc/rc.configure_plugins POST_DEINSTALL >/dev/null 2>&1 || true
fi
if [ -x /usr/local/etc/rc.d/configd ]; then
    /usr/local/etc/rc.d/configd restart >/dev/null 2>&1 || true
fi
if [ -x /usr/local/sbin/pluginctl ]; then
    /usr/local/sbin/pluginctl -cq cache_flush >/dev/null 2>&1 || true
fi
exit 0
EOF_POSTDE

chmod 755 "$META/+POST_INSTALL" "$META/+PRE_DEINSTALL" "$META/+POST_DEINSTALL"

# pkg create expects paths as they appear inside the stage root.
(
    cd "$STAGE"
    find usr/local -type f -print | sed 's#^#/#' | sort
) > "$META/plist"

rm -f "$OUTDIR/${NAME}-${VERSION}.pkg" "$OUTDIR/${NAME}-${VERSION}.txz"

echo "Building native package with OPNsense pkg(8)..."
"$PKG" create -m "$META" -r "$STAGE" -p "$META/plist" -o "$OUTDIR"

PACKAGE=$(find "$OUTDIR" -maxdepth 1 -type f \( -name "${NAME}-${VERSION}.pkg" -o -name "${NAME}-${VERSION}.txz" \) | head -n 1)
if [ -z "$PACKAGE" ]; then
    echo "ERROR: pkg create completed but package file was not found." >&2
    exit 1
fi

echo "Package created: $PACKAGE"
"$PKG" info -F "$PACKAGE" 2>/dev/null || true
