# Sophos Frontpanel unter OPNsense – LCD + Tasten über RS232

## Ziel dieses Dokuments

Dieses Dokument beschreibt ausschließlich, wie das originale Sophos-Frontpanel
(16x2-LCD + UP/DOWN/ENTER/ESC) direkt aus **OPNsense / FreeBSD** angesprochen
werden kann.

Es gibt zwei mögliche Betriebsarten:

1. **OPNsense direkt auf der Sophos-Hardware**
   - OPNsense läuft ohne Proxmox direkt auf dem Gerät.
   - OPNsense greift direkt auf den physischen seriellen Port des Frontpanels zu.

2. **OPNsense als VM unter Proxmox**
   - Der physische serielle Port des Sophos-Frontpanels wird vom Proxmox-Host
     direkt an die OPNsense-VM durchgereicht.
   - OPNsense spricht danach den virtuellen UART direkt an.

Es ist kein Debian-System nötig.

---

# 1. Hardware

Auf der Frontpanel-Platine wurden folgende Bauteile identifiziert:

```text
Microcontroller:
PIC16F628A

RS232 Transceiver:
SIPEX SP232EEN
```

Die Frontpanel-Platine besitzt als relevante Verbindungen:

```text
RS232
Power
```

Die vier Tasten sind intern mit dem PIC16F628A verbunden.

Damit werden sowohl

```text
LCD
+
UP / DOWN / ENTER / ESC
```

vollständig über dieselbe RS232-Verbindung übertragen.

Separate GPIO-Leitungen sind nicht notwendig.

---

# 2. Serielles Protokoll

Serielle Parameter:

```text
Baudrate:    2400 Baud
Datenbits:   8
Parität:     keine
Stopbits:    2
Flowcontrol: aus
```

Kurz:

```text
2400 8N2
```

---

# 3. FreeBSD / OPNsense Gerätenamen

OPNsense basiert auf FreeBSD.

Serielle UARTs erscheinen typischerweise als:

```text
/dev/ttyu0
/dev/ttyu1
...
```

und als Callout-Devices:

```text
/dev/cuau0
/dev/cuau1
...
```

Für einen eigenen dauerhaft laufenden Frontpanel-Dienst ist normalerweise das
Callout-Device sinnvoll:

```text
/dev/cuauX
```

Der exakte Index muss auf dem jeweiligen System ermittelt werden.

Prüfen mit:

```sh
dmesg | grep -i uart
```

und:

```sh
ls -la /dev | grep -E 'ttyu|ttyU|cuau|cuaU'
```

Zusätzlich:

```sh
sysctl dev.uart
```

Wichtig:

```text
Nicht hart davon ausgehen, dass das Frontpanel immer /dev/cuau0 ist.
```

---

# 4. Variante A – OPNsense direkt auf der Sophos-Hardware

Wenn OPNsense direkt auf der Sophos-Hardware installiert wird, erkennt FreeBSD
die eingebauten UARTs direkt.

Auf der getesteten Hardware existierten unter Linux zwei reale 16550A-UARTs:

```text
COM1:
I/O 0x3F8
IRQ 4

COM2:
I/O 0x2F8
IRQ 3
```

Das Frontpanel war am zweiten seriellen Port angebunden.

Unter FreeBSD ist daher sehr wahrscheinlich einer der UARTs:

```text
uart0
uart1
```

das Frontpanel.

Ermitteln:

```sh
dmesg | grep -i uart
```

Danach die Kandidaten testen, beispielsweise:

```text
/dev/cuau0
/dev/cuau1
```

## Achtung auf die OPNsense-Konsole

OPNsense darf den Frontpanel-Port nicht gleichzeitig als serielle Systemkonsole
verwenden.

Prüfen, ob eine serielle Konsole aktiviert ist.

Der Frontpanel-Port muss exklusiv für den Frontpanel-Dienst frei sein.

Es darf immer nur **ein Prozess gleichzeitig** auf diesen UART zugreifen.

---

# 5. Variante B – Proxmox → OPNsense Serial Passthrough

Der physische Port des Frontpanels liegt auf dem Proxmox-Host beispielsweise als:

```text
/dev/ttyS1
```

vor.

Dieser Port kann direkt an die OPNsense-VM durchgereicht werden.

Beispiel für VM 100:

```sh
qm set 100 -serial0 /dev/ttyS1
```

Kontrolle:

```sh
qm config 100 | grep serial
```

Erwartet:

```text
serial0: /dev/ttyS1
```

Danach OPNsense neu starten.

In OPNsense prüfen:

```sh
dmesg | grep -i uart
```

und:

```sh
ls -la /dev | grep -E 'ttyu|ttyU|cuau|cuaU'
```

Der von QEMU bereitgestellte serielle Port erscheint dann als FreeBSD-UART.

Für die Anwendung sollte anschließend das passende:

```text
/dev/cuauX
```

verwendet werden.

## Wichtig

Der Proxmox-Host darf diesen Port nicht zusätzlich selbst verwenden.

Prüfen:

```sh
fuser -v /dev/ttyS1
```

Während die OPNsense-VM läuft, sollte im Wesentlichen nur der QEMU-Prozess der
VM den Port geöffnet haben.

---

# 6. LCD-Befehle

Das Frontpanel verwendet das Byte:

```text
FE
```

als Befehlspräfix.

Bekannte und praktisch bestätigte Befehle:

| Funktion | Bytes |
|---|---|
| LCD löschen | `FE 01` |
| Home / Display-Shift zurücksetzen | `FE 02` |
| Tastenstatus abfragen | `FE 06` |
| Display an, Cursor aus, Blinken aus | `FE 0C` |
| Schreibposition Zeile 1 | `FE 80` |
| Schreibposition Zeile 2 | `FE C0` |

---

# 7. Text anzeigen

Das Display besitzt:

```text
16 Zeichen
x
2 Zeilen
```

## Erste Zeile

```text
FE 80
```

danach 16 ASCII-Zeichen.

Beispiel:

```text
FE 80 + "TESTBILD.MEDIA   "
```

## Zweite Zeile

```text
FE C0
```

danach 16 ASCII-Zeichen.

Beispiel:

```text
FE C0 + "BONDING ROUTER  "
```

## Kein Nullbyte anhängen

Sehr wichtig:

```text
00
```

darf nicht als C-String-Terminator mitgesendet werden.

Das Frontpanel interpretiert `00` als darstellbares Zeichen.

Beim Test erschien dadurch ein Herzsymbol.

Also:

```text
richtig:
"TESTBILD.MEDIA   "

falsch:
"TESTBILD.MEDIA\0"
```

---

# 8. Tasten abfragen

Die Tasten senden nicht von selbst.

Der PIC muss regelmäßig gepollt werden.

Poll-Befehl:

```text
TX: FE 06
```

Der Controller antwortet mit:

```text
RX: FD xx
```

Zuordnung:

| Zustand | Antwort |
|---|---|
| keine Taste | `FD BF` |
| UP | `FD BE` |
| DOWN | `FD BD` |
| ENTER | `FD BB` |
| ESC | `FD B7` |

---

# 9. Tastenbitmaske

Grundzustand:

```text
BF = 1011 1111
```

Aktive-low:

```text
BE = 1011 1110 = UP
BD = 1011 1101 = DOWN
BB = 1011 1011 = ENTER
B7 = 1011 0111 = ESC
```

Daraus:

```text
Bit 0 = UP
Bit 1 = DOWN
Bit 2 = ENTER
Bit 3 = ESC
```

---

# 10. Wichtiger Nebeneffekt des Tasten-Polls

Der Befehl:

```text
FE 06
```

pollt zwar die Tasten korrekt, verändert jedoch gleichzeitig den internen
LCD-Zustand.

Ohne Gegenmaßnahme verschiebt sich der Displayinhalt.

Deshalb muss **nach jedem Tasten-Poll** zwingend gesendet werden:

```text
FE 02
```

danach ungefähr:

```text
40 ms warten
```

anschließend:

```text
FE 0C
```

danach ungefähr:

```text
20 ms warten
```

Komplette Restore-Sequenz:

```text
FE 06
↓
FD xx lesen
↓
FE 02
↓
40 ms
↓
FE 0C
↓
20 ms
```

`FE 02` setzt Home-Position und Display-Shift zurück.

`FE 0C` schaltet den Cursor und dessen Blinken wieder aus.

Ohne `FE 0C` blinkt nach dem Restore ein Cursor auf dem ersten Zeichen.

---

# 11. Nicht verwenden: FE 18 als Restore

Es wurde getestet, den durch `FE 06` verursachten Shift mit:

```text
FE 18
```

auszugleichen.

Das funktioniert nicht.

Der gesamte Displayinhalt scrollt dadurch sichtbar von rechts nach links.

Für die Tastenabfrage deshalb ausschließlich:

```text
FE 06
→ Antwort lesen
→ FE 02
→ FE 0C
```

verwenden.

---

# 12. Bewährte Timings

Praktisch bestätigte Werte:

```text
Tastenpoll:
ca. alle 100 ms

Antwortfenster:
ca. 60 ms

Pause nach FE 02:
ca. 40 ms

Pause nach FE 0C:
ca. 20 ms
```

Damit wurden alle vier Tasten zuverlässig erkannt.

---

# 13. Tastendruck nur einmal auslösen

Beim Halten einer Taste liefert jeder Poll weiterhin denselben Tastencode.

Beispiel:

```text
FD BF
FD BE
FD BE
FD BE
FD BF
```

Nur dieser Übergang ist ein neues UP-Event:

```text
FD BF → FD BE
```

Die weiteren:

```text
FD BE → FD BE
```

werden ignoriert.

Das Loslassen:

```text
FD BE → FD BF
```

ist ebenfalls kein Menüevent.

Damit entsteht genau ein Event pro physischem Tastendruck.

---

# 14. Display-Refresh

Das Frontpanel zeigt bei einem tatsächlichen Neuschreiben des Displayinhalts
kurz einen leeren Zwischenzustand.

Dieser Effekt stammt offenbar vom Frontpanel-Controller selbst.

Empfohlene Regel für Livewerte:

```text
Display höchstens alle 2 Sekunden aktualisieren.
```

Zusätzlich:

```text
Nur neu schreiben, wenn sich der sichtbare Inhalt geändert hat.
```

Beispiel:

```text
WAN1 ONLINE
```

wird nicht alle zwei Sekunden neu übertragen, solange der Wert unverändert ist.

Erst bei:

```text
WAN1 OFFLINE
```

erfolgt ein neuer LCD-Write.

---

# 15. Empfohlener OPNsense-Dienst

Für eine direkte Integration in OPNsense sollte ein eigener Dienst verwendet werden.

Beispielname:

```text
frontpaneld
```

Aufgaben:

```text
frontpaneld
├── seriellen UART exklusiv öffnen
├── LCD schreiben
├── Tasten alle ~100 ms pollen
├── Tastenevents erzeugen
├── Menü verwalten
├── OPNsense-Statuswerte lesen
└── LCD-Livewerte maximal alle 2 s aktualisieren
```

Nur dieser Dienst darf auf:

```text
/dev/cuauX
```

zugreifen.

---

# 16. OPNsense-Plugin-Struktur

Eine mögliche Plugin-Struktur:

```text
os-frontpanel/
├── src/
│   └── opnsense/
│       ├── service/
│       │   └── frontpaneld
│       ├── mvc/
│       │   └── app/
│       │       ├── controllers/
│       │       ├── models/
│       │       └── views/
│       └── scripts/
│           └── frontpanel/
└── Makefile
```

Das Plugin könnte in der OPNsense-WebGUI beispielsweise anbieten:

```text
Services
└── Frontpanel
    ├── Enable
    ├── Serial Device
    ├── Baudrate
    ├── Home Text
    ├── Refresh Interval
    └── Status
```

Serielles Device auswählbar:

```text
/dev/cuau0
/dev/cuau1
...
```

Default:

```text
2400 8N2
```

---

# 17. Zugriff auf OPNsense-Daten bei direkter Integration

Wenn der Frontpanel-Dienst direkt in OPNsense läuft, müssen die eigenen
OPNsense-Daten nicht zwingend über die externe HTTPS-API abgefragt werden.

Mögliche Quellen:

```text
configd
lokale OPNsense-API
FreeBSD sysctl
lokale Systembefehle
OPNsense Backend-Skripte
```

Der Vorteil:

```text
kein externer API-Benutzer nötig
keine HTTPS-Verbindung zur eigenen Firewall nötig
keine API-Secrets für lokale Systemdaten
```

Speedify und Proxmox würden weiterhin extern abgefragt werden, wenn diese
Komponenten auf separaten Systemen laufen.

---

# 18. Direkte Installation vs. Proxmox-Passthrough

## OPNsense direkt auf Hardware

```text
Sophos Frontpanel
       │
       │ RS232
       ▼
physischer UART
       │
       ▼
FreeBSD / OPNsense
/dev/cuauX
       │
       ▼
frontpaneld
```

## OPNsense unter Proxmox

```text
Sophos Frontpanel
       │
       │ RS232
       ▼
Proxmox /dev/ttyS1
       │
       │ serial passthrough
       ▼
OPNsense VM
       │
       ▼
FreeBSD /dev/cuauX
       │
       ▼
frontpaneld
```

Das Frontpanel-Protokoll ist in beiden Fällen identisch.

Nur das serielle Device unterscheidet sich.

---

# 19. Minimaler Initialisierungsvorgang

Beim Start des Dienstes:

```text
1. UART mit 2400 8N2 öffnen

2. FE 01
   Display löschen

3. ca. 100 ms warten

4. FE 0C
   Display an
   Cursor aus
   Blinken aus

5. Zeile 1 schreiben

6. Zeile 2 schreiben

7. Tastenpolling starten
```

Beispiel:

```text
FE 01
100 ms
FE 0C

FE 80 + "TESTBILD.MEDIA   "
FE C0 + "BONDING ROUTER  "
```

---

# 20. Minimaler Polling-Zyklus

```text
RX Buffer leeren

TX:
FE 06

RX:
FD BF / BE / BD / BB / B7

TX:
FE 02

40 ms

TX:
FE 0C

20 ms

Tastenzustand auswerten
```

---

# 21. Zusammenfassung

## UART

```text
2400 8N2
```

## LCD

```text
FE 01 = Clear
FE 02 = Home / Shift Reset
FE 0C = Display On, Cursor Off
FE 80 = Zeile 1
FE C0 = Zeile 2
```

## Tasten

```text
FE 06 = Poll

FD BF = keine Taste
FD BE = UP
FD BD = DOWN
FD BB = ENTER
FD B7 = ESC
```

## Nach jedem Tasten-Poll

```text
FE 02
40 ms
FE 0C
20 ms
```

## FreeBSD / OPNsense

Physischer oder durchgereichter UART:

```text
/dev/cuauX
```

Exakten Port immer mit:

```sh
dmesg | grep -i uart
ls -la /dev/ttyu* /dev/cuau*
```

ermitteln.

## Live-Displaywerte

```text
nicht häufiger als alle 2 Sekunden
```

und nur schreiben, wenn sich der sichtbare Inhalt geändert hat.

Damit kann das originale Sophos-Frontpanel vollständig direkt aus OPNsense
gesteuert werden – sowohl bei Bare-Metal-Installation als auch bei Serial
Passthrough aus Proxmox.
