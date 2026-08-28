#!/bin/sh
set -u

PKG=/usr/local/sbin/pkg
FAIL=0

check_file()
{
    if [ -f "$1" ]; then
        echo "OK   $1"
    else
        echo "MISS $1"
        FAIL=1
    fi
}

echo "== package =="
if "$PKG" info -e os-sophos-frontpanel >/dev/null 2>&1; then
    "$PKG" info os-sophos-frontpanel | sed -n '1,12p'
else
    echo "MISS pkg registration: os-sophos-frontpanel"
    FAIL=1
fi

echo
echo "== plugin files =="
check_file /usr/local/opnsense/mvc/app/controllers/OPNsense/SophosFrontpanel/IndexController.php
check_file /usr/local/opnsense/mvc/app/controllers/OPNsense/SophosFrontpanel/forms/general.xml
check_file /usr/local/opnsense/mvc/app/models/OPNsense/SophosFrontpanel/SophosFrontpanel.xml
check_file /usr/local/opnsense/mvc/app/views/OPNsense/SophosFrontpanel/index.volt
check_file /usr/local/opnsense/service/conf/actions.d/actions_sophos_frontpanel.conf
check_file /usr/local/opnsense/service/templates/OPNsense/SophosFrontpanel/+TARGETS
check_file /usr/local/opnsense/scripts/sophos_frontpanel/frontpaneld.py
check_file /usr/local/opnsense/scripts/sophos_frontpanel/list_serial_devices.py

echo
echo "== package ownership =="
"$PKG" which /usr/local/opnsense/mvc/app/controllers/OPNsense/SophosFrontpanel/forms/general.xml || FAIL=1

echo
echo "== rendered config =="
/usr/local/sbin/configctl template reload OPNsense/SophosFrontpanel || FAIL=1
[ -f /usr/local/etc/sophos_frontpanel.conf ] && cat /usr/local/etc/sophos_frontpanel.conf || FAIL=1

echo
echo "== serial device dropdown =="
/usr/local/sbin/configctl sophos_frontpanel list_serial_devices || FAIL=1

echo
echo "== configd/status =="
/usr/local/sbin/configctl sophos_frontpanel status || true

echo
echo "== UART check =="
/usr/local/sbin/configctl sophos_frontpanel check || FAIL=1

exit "$FAIL"
