<!-- tools/stock/README.DE.md, Version: 1.00 -->
# Shelly-Herstellerfirmware vorbereiten

[English](README.md)

Diese Werkzeuge unterstützen die Vorbereitung der festgelegten Shelly-Stock-Firmware. Der reguläre Bedienablauf steht in der [Haupt-README](../../README.de.md); Einstiegspunkt ist [ShellyTakeover.py](../ShellyTakeover.py).

## Werkzeuge und Vorgaben

| Datei | Funktion |
| --- | --- |
| [ValidateFirmwareLayout.py](ValidateFirmwareLayout.py) | Prüft ein Stock-Paket, seine Komponenten und die Partitionierung gegen die festgelegte Paketidentität. |
| [ServeFirmware.py](ServeFirmware.py) | Stellt genau eine angegebene Paketdatei per HTTP bereit; Hilfswerkzeug für einen kontrollierten lokalen Transfer. |
| [StockFirmware.py](../StockFirmware.py) | Beschafft und prüft die festgelegte Herstellerfirmware und kontrolliert den Updateablauf. |
| [StockUpdatePolicy.json](../../ShellyTakeover/StockUpdatePolicy.json) | Legt erlaubte Eingangs-Builds und das genaue Updateziel fest. |
| [StockFirmware.layout.json](../../ShellyTakeover/StockFirmware.layout.json) | Legt Paketidentität, Komponenten und Partitionierung fest. |

## Ablauf

1. Zielgerät über `SHELLY_IP` festlegen und Modell, Firmwareversion und Build prüfen.
2. Bei einem bereits akzeptierten Build direkt mit der Takeover-Vorprüfung fortfahren. Für einen erlaubten älteren Build nur den ausdrücklich freigegebenen Hersteller-Updateweg anbieten. Unbekannte Zwischenstände und Downgrades bleiben gesperrt.
3. Das genaue Zielpaket per zertifikatsgeprüftem HTTPS laden oder mit `--stock-package` ein vorhandenes offizielles Paket angeben.
4. Paketidentität, Manifest, Komponenten und Partitionierung prüfen. Bereits gespeicherte Pakete werden vor jeder Nutzung erneut geprüft.
5. Ein Herstellerupdate nur mit `--execute --update-stock` ausführen. Anschließend Version, Build und Geräteidentität erneut prüfen und erst danach den Takeover-Ablauf fortsetzen.

Der Cache liegt im ignorierten Verzeichnis `generated/`. Veränderte Stable-Deskriptoren ersetzen keine feste Paketidentität; es gibt keinen unsicheren TLS-Fallback. Ein erfolgreich geprüfter Download allein belegt keinen sicheren Updateweg: Auch die konkrete Ausgangsversion muss zur Policy passen. Herstellerupdates können Bootloader oder Partitionierung verändern.
