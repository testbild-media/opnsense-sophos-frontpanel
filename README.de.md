# OPNsense Sophos Frontpanel

Ein natives OPNsense-Plugin für das originale Frontpanel von Sophos SG/XG
Appliances. Es steuert das **16x2-LCD** und die vier Gehäusetasten
**UP / DOWN / ENTER / ESC** über den internen RS232-UART.

> **Stand:** öffentliche Version **1.0.0**. Getestet auf einer
> **Sophos SG330 Rev.1** mit **OPNsense 26.7** auf Bare Metal.

Das Projekt ist unabhängig von Sophos und OPNsense/Deciso. Siehe
[NOTICE.md](NOTICE.md).

Repository: [https://github.com/testbild-media/opnsense-sophos-frontpanel](https://github.com/testbild-media/opnsense-sophos-frontpanel)

[English README](README.md)

## Funktionen

- echte OPNsense-MVC-Integration unter **Services -> Sophos Frontpanel**
- als `os-sophos-frontpanel` über `pkg` verwaltet
- dynamisches Dropdown für serielle Devices
  - `/dev/cuau*` und `/dev/cuaU*`
  - aktive Kernel-/Loader-/Login-Konsolen werden ausgeschlossen
- konsequentes **16x2-Layout**
- LCD-Titel in GUI und Model auf **16 Zeichen** begrenzt
- WAN- und LAN-Interfaces jeweils als Mehrfachauswahl
- pro Gruppe wählbar: OPNsense **Description** oder **Identifier**
- echtes FreeBSD-Device rechtsbündig im Kopf, z. B. `WANSL       igb2`
- je ausgewähltem WAN/LAN eine eigene IPv4-Seite
- CPU, Load, RAM, Uptime und Gateway-Status
- automatische Seitenrotation
- Bedienung über die Fronttasten
- keine zusätzlichen Python-Pakete
- nativer lokaler Paketbau direkt auf OPNsense mit `pkg create`
- Regressionstests für 16x2-Ausgabe, MVC-Schema und UART-Konsolenerkennung

## Schnellinstallation

Source-Release auf die Firewall kopieren und z. B. nach
`/root/opnsense-sophos-frontpanel` entpacken:

```sh
cd /root/opnsense-sophos-frontpanel
sh build-and-install.sh
```

Danach prüfen:

```sh
pkg info os-sophos-frontpanel
sh tools/verify-install.sh
```

Anschließend in der WebGUI:

**Services -> Sophos Frontpanel**

Für die getestete SG330 Rev.1 ist `/dev/cuau1` der Frontpanel-UART. Das Plugin
sollte das Device automatisch im Dropdown anbieten, sofern es nicht von einer
seriellen Konsole belegt ist.

Ausführliche Anleitung: [docs/INSTALLATION.md](docs/INSTALLATION.md)

## LCD-Beispiele

```text
WANSL       igb2
100.64.12.34
```

```text
CPU  12% L  0.2
MEM 34% 4.1G/12G
```

Jede sichtbare Zeile wird bereits beim Erzeugen auf maximal 16 Zeichen
beschränkt; es wird nicht einfach erst am Ende blind abgeschnitten.

## Bedienung

| Taste | Funktion |
|---|---|
| UP | vorherige Seite |
| DOWN | nächste Seite |
| ENTER | automatische Rotation ein/aus |
| ESC | zurück zur Startseite |

## Diagnose

```sh
configctl sophos_frontpanel status
configctl sophos_frontpanel check
configctl sophos_frontpanel restart
configctl sophos_frontpanel list_serial_devices

tail -f /var/log/sophos_frontpanel.log
cat /usr/local/etc/sophos_frontpanel.conf
```

## Versionshinweis

Die öffentliche Versionsreihe startet bewusst bei **1.0.0**. Die vorherigen
1.1.x-Stände waren interne Hardware-/Entwicklungsversionen.

Für den öffentlichen Release v1.0.0 ist auch die MVC-Schemaversion **1.0.0**.
Paketversion und MVC-Schema werden für diesen ersten öffentlichen Release bewusst
gleich gehalten. Künftige Schema-Migrationen können die Model-Version bei Bedarf
erhöhen.

## Weitere Dokumentation

- [Installation](docs/INSTALLATION.md)
- [Konfiguration](docs/CONFIGURATION.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Protokollreferenz](docs/Protocol-Reference.md)
- [Hardware-Kompatibilität](docs/HARDWARE.md)
- [Architektur](docs/ARCHITECTURE.md)
- [Entwicklung](docs/DEVELOPMENT.md)
- [Release-Prozess](docs/RELEASING.md)
- [GitHub-Veröffentlichung](docs/GITHUB.md)
