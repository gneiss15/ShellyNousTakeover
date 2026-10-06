English version is [here](README.md).

# ShellyTakeover

Version: 1.04

App/ enthält die automatische Takeover, Bootloader/ den finalen Dual-Bootloader,
Rescue/ die eigenständige Rescue. Migration/ und LoaderWriter/ enthalten die
begrenzten Writer und Host-Fehlerinjektion.

Lokaler Build aus ShellyNousTakeover nach Setzen der privaten/IDF-Pfade:

```bash
bash tools/BuildTakeover.sh shelly
python3 tools/ValidateTakeoverPackage.py
```

Das baut Loader, Rescue und App und erzeugt generated/ShellyTakeover/App/
PlugMG3-ShellyTakeover.zip. Kein Upload durch diese Kommandos.

## Paketinhalt und Installation

Das ZIP ist ein OTA-Paket für die originale Shelly-Firmware. Es enthält:

- `manifest.json`: Modell/Plattform, Paketversion sowie Größen und Prüfsummen von App und Dateisystem.
- `ShellyTakeover.bin`: die Takeover-App mit eingebettetem neuem Bootloader, Rescue sowie alter und neuer Partitionstabelle als Payloads.
- `fs.img`: ein mit `0xFF` gefülltes leeres Dateisystem-Image, das dieses Paketformat benötigt.

Das ZIP enthält keinen separaten Bootloader- oder Partitionstabellen-OTA-Teil. Stock installiert das App-/Dateisystempaket; die laufende Takeover führt anschließend selbst die geprüften Migrations-Schreibvorgänge aus.

Das ZIP über das PC-Skript verwenden und am oben genannten generierten Pfad belassen. Seine Dateien nicht einzeln entpacken und hochladen. Nach Erfüllen der Voraussetzungen und Setzen der Env-Variablen einschließlich `SHELLY_IP` gemäß [Haupt-README](../README.de.md#pc-vorprüfung-und-übernahme) diese Befehle aus dem Repository-Hauptverzeichnis ausführen:

```bash
# Rein lesende Gerätevorprüfung:
python3 tools/ShellyTakeover.py
```

Vor dem nächsten Befehl stabile Stromversorgung sicherstellen und angeschlossene Verbraucher entfernen. Dieser Befehl verändert das Gerät:

```bash
python3 tools/ShellyTakeover.py --execute
```

Das Skript prüft das ZIP, stellt es vorübergehend per HTTP vom PC bereit und fordert einmal `Shelly.Update` an. Der Shelly lädt das Paket herunter; das Skript wartet auf den anschließenden Rescue-Status und prüft ihn. PC und Skript bis zum Abschluss laufen lassen. Meldet die Vorprüfung ein erforderliches Stock-Update, zunächst der [Stock-Update-Anleitung](../README.de.md#pc-vorprüfung-und-übernahme) folgen.

Die App wartet nach AP+STA/Webstart auf eine LAN-IP und beginnt danach selbständig
mit ihren Guards und der Übernahme. Das Paket deshalb noch nicht für einen
unverifizierten Hardwareeinsatz verwenden. Entwicklungsstand: [TODO](../TODO.de.md).
