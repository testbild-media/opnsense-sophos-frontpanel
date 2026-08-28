# Troubleshooting

## WebGUI entry opens an OPNsense crash report

Check that the MVC form exists and belongs to the package:

```sh
ls -l /usr/local/opnsense/mvc/app/controllers/OPNsense/SophosFrontpanel/forms/general.xml
pkg which /usr/local/opnsense/mvc/app/controllers/OPNsense/SophosFrontpanel/forms/general.xml
```

Then clear/rebuild plugin caches by reinstalling the package or running the
normal post-install flow.

## Serial dropdown is empty

Inspect available callout devices:

```sh
ls -la /dev | grep -E 'cuau|cuaU'
configctl sophos_frontpanel list_serial_devices
```

Check console assignments:

```sh
sysctl kern.console
kenv console
kenv comconsole_port
kenv hw.uart.console
ps ax -o command= | grep getty
```

A port actively used as a serial console is intentionally excluded.

## UART opens but the display does not react

Run:

```sh
configctl sophos_frontpanel check
```

Then verify the actual hardware UART in `dmesg`. On the confirmed SG330 Rev.1
the front panel is uart1 / `/dev/cuau1`.

The protocol is 2400 8N2. Do not use flow control.

## Display shifts after button polling

The controller has a known side effect after `FE 06`. The daemon must always
perform:

```text
FE 06
read FD xx
FE 02
wait ~40 ms
FE 0C
wait ~20 ms
```

If the display visibly shifts, confirm you are running the repository daemon
and that no second process is sharing the UART.

## `None` is shown instead of `igbX`

Current code resolves the configured physical interface primarily from:

```text
interfaces.<identifier>.if
```

and treats the runtime `pluginctl -4` device field only as a fallback when it is
a real string. JSON `null` must never be rendered as the string `None`.

Useful checks:

```sh
/usr/local/sbin/pluginctl -g interfaces.wan.if
/usr/local/sbin/pluginctl -g interfaces.wan.descr
/usr/local/sbin/pluginctl -4 wan
```

Replace `wan` with the logical OPNsense identifier as required.

## Service status and logs

```sh
configctl sophos_frontpanel status
ps auxww | grep sophos_frontpanel
tail -f /var/log/sophos_frontpanel.log
cat /var/run/sophos_frontpanel.status.json
```

## Full install verification

From the checked-out/source directory:

```sh
sh tools/verify-install.sh
```
