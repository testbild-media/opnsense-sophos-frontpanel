# Hardware compatibility

## Confirmed

### Sophos SG330 Rev.1

Tested with OPNsense 26.7 on bare metal.

```text
uart0: <16550 or compatible> port 0x3f8-0x3ff irq 4 flags 0x10 on acpi0
uart1: <16550 or compatible> port 0x2f8-0x2ff irq 3 on acpi0
```

Confirmed frontpanel interface:

```text
/dev/cuau1
2400 baud
8 data bits
no parity
2 stop bits
no flow control
```

The original panel contains a PIC16F628A and an SP232EEN RS232 transceiver.
LCD control and all four buttons share the same serial connection.

## Reporting another model

A model should only be added to the confirmed table after LCD output and all
four keys have been tested. Please include:

```sh
dmesg | grep -i uart
ls -la /dev | grep -E 'cuau|cuaU|ttyu|ttyU'
sysctl kern.console
```

Also state the exact Sophos model/revision and the confirmed callout device.
