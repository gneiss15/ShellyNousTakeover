English version is [here](README.md).

# Mini-Examples: Shelly und NOUS

Version: 1.01

`MiniMain/` ist eine kleine ESP-IDF-App, die für beide Zielgeräte separat gebaut wird.
Sie zeigt den Vertrag mit Rescue ohne Abhängigkeit von TmrSw oder Arduino:

- Chip, Flashgröße, Security, tatsächliche SDK-Partitionstabelle und Main-/Rescue-/
  LittleFS-/NVS-/OTA-Geometrie vor Hardware- und Netzwerkinitialisierung prüfen;
- Relais sicher AUS initialisieren und dauerhaft AUS lassen;
- WLAN aus der externen privaten Konfiguration, ohne WLAN-/PHY-NVS-Persistenz;
- eingebaute Weboberfläche, `GET /status` und `POST /Rescue` zum Rescue-Neustart;
- Main als korrekt typisiertes, RSA-signiertes Artefakt für die installierte Rescue.

Die App benötigt und verändert kein LittleFS. Sie misst keine Leistung, enthält
keinen Timer und keinen eigenen Firmware-Updater. Updates erfolgen über Rescue.
Hardware-Safe-Boot bleibt die Funktion des bereits installierten Bootloaders.

## Voraussetzungen und Build

Zuerst die Environment-Variablen, Toolchain und privaten Dateien gemäß
[Projekt-README](../README.de.md) einrichten. Der DeviceType muss mit der tatsächlich
installierten Rescue übereinstimmen; das Schlüsselpaar muss zu deren Prüfschlüssel passen.
Die WLAN-Felder stammen aus demselben ShellyTakeover-/NousTakeover-Abschnitt wie bei Rescue.
Danach aus dem Projektverzeichnis:

```bash
# Shelly-Standard ist TmrSwShellyC3V1.
export TAKEOVER_DEVICE_TYPE='TmrSwShellyC3V1'
bash tools/BuildExample.sh shelly

# NOUS-Standard der neuen Takeover-Rescue ist TakeoverNousA8TV1.
export TAKEOVER_DEVICE_TYPE='TakeoverNousA8TV1'
bash tools/BuildExample.sh nous
```

Ausgabe: `generated/ShellyTakeover/MiniMain/MiniMain.signed` beziehungsweise
`generated/NousTakeover/MiniMain/MiniMain.signed`. Der Build prüft Image, Chip,
Descriptor, SDK-Einstellungen und Signatur. Er führt keine Geräteaktion aus.
Die aktuellen MiniMain-Beispiele wurden für beide Chips gebaut und signiert. Sie wurden nicht auf Hardware hochgeladen oder getestet. Diese Prüfung ersetzt keinen Hardwaretest.

## Installation in einer bereits laufenden Rescue

Die Installation ersetzt die vorhandene Main-App. Zuerst das richtige Gerät und
Rescue-DeviceType in der Rescue-Statusseite prüfen. Dann ausschließlich die passende
`MiniMain.signed` über den **Firmware**-Upload der Rescue installieren. Für dieses
Beispiel ist kein Dateisystem-Upload nötig. Nach erfolgreicher Upload-/Readback-
Prüfung Main starten. Die Seite `/` zeigt das Beispiel, `/status` seinen Zustand.
Der Button **Start Rescue** wählt die Rescue-Partition als nächsten Boot und startet neu.
Die App löscht keine NVS, keinen Bootloader und keine Partitionstabelle.

Kein `idf.py flash` verwenden: der generische Factory-App-Upload kann Rescue treffen.
Raw `MiniMain.bin` ist kein signiertes Netzwerk-Update.

## Vollständige Anwendungsbeispiele

Separate Repositories für **TmrSwShelly** und **TmrSwA8T** sind geplant. Sie sollen
Timer, Heizungsprofile, Konfiguration, LittleFS und weitere Gerätefunktionen zeigen.
Sie sind noch nicht veröffentlicht; deshalb gibt es hier noch keine Repository-Links.
Die Mini-Examples sind unabhängig davon baubar und zeigen die minimale Main-Integration.
