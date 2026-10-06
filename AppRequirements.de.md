English version is [here](AppRequirements.md).

# Anforderungen an eine spätere Main-App

Version: 1.04

Die folgenden Geometrien entsprechen den eigenständigen Bootloader-/Rescue-Builds.
Die neue Laufzeit ist noch am Gerät zu prüfen. Adressen sind absolute Flashadressen; Größen in Bytes.
Keine Partitionstabelle oder Bootloader aus einem generischen Boardprofil flashen.

## Shelly Plug M Gen3: ESP32-C3, 8 MiB

| Verwendung | Offset | Größe |
|---|---:|---:|
| Finaler Dual-Bootloader, begrenzter Schreibbereich | 0x000000 | 0x006000 |
| Partitionstabelle, Sektor | 0x010000 | 0x001000 |
| Alter Bootstate, read-only | 0x011000 | 0x002000 |
| Alte NVS, read-only | 0x014000 | 0x00C000 |
| Erhaltene Stock-App, read-only | 0x020000 | 0x2A0000 |
| LittleFS (`spiffs`) | 0x2C0000 | 0x0E0000 |
| Main (`app0`, ota_0) | 0x3A0000 | 0x2A0000 |
| Rescue (`safeboot`, factory) | 0x640000 | 0x180000 |
| NVS | 0x7C0000 | 0x020000 |
| OTA-Bootauswahl | 0x7E0000 | 0x002000 |
| Bisherige Migrations-Checkpoints, reserviert | 0x7E2000 | 0x008000 |
| Factory-/Kalibrierungsdaten (`shelly`), read-only | 0x7F0000 | 0x010000 |

Nicht aufgeführte Lücken sind keine freigegebenen App-/Dateisystembereiche.
Insbesondere Factory-Daten nicht löschen oder durch Daten eines anderen Geräts ersetzen.
Die **gelinkte SDK-Laufzeit** muss die Partitionstabelle bei 0x10000 lesen;
allein eine passende CSV reicht nicht. Vorgebaute SDKs mit 0x8000 passen nicht.

## NOUS A8T: ESP32, 4 MiB

| Verwendung | Offset | Größe |
|---|---:|---:|
| ROM-Vorbereich, nicht Bestandteil des Loader-Writes | 0x000000 | 0x001000 |
| Finaler Bootloader, begrenzter Schreibbereich | 0x001000 | 0x007000 |
| Partitionstabelle, Sektor | 0x008000 | 0x001000 |
| NVS | 0x009000 | 0x005000 |
| OTA-Bootauswahl | 0x00E000 | 0x002000 |
| Rescue (`safeboot`, factory) | 0x010000 | 0x0D0000 |
| Main (`app0`, ota_0) | 0x0E0000 | 0x2D0000 |
| LittleFS (`spiffs`) | 0x3B0000 | 0x050000 |

Die SDK-Laufzeit verwendet Partitionstabellenoffset 0x8000. Exemplarbezogene
Kalibrierung im NVS erhalten; kein pauschales NVS-Löschen bei Main-/FS-Updates.

## Upload-/App-Vertrag der bestehenden Rescue

- Native ESP-App für den jeweiligen Chip; gesamtes App-Binary muss in die
  Main-Partition passen. Rescue wird nicht von Main-Updates überschrieben.
- Keine A/B-App-OTA: Main fordert Rescue an; Rescue schreibt Main und LittleFS.
  Normales Arduino-OTA zur „anderen“ App ist für diese Geometrie nicht passend.
- Firmware und LittleFS als getrennte, korrekt typisierte und RSA-signierte
  Artefakte hochladen. Signierschlüssel muss zum einkompilierten öffentlichen
  Rescue-Schlüssel passen; beliebiges raw .bin wird nicht als normales Update akzeptiert.
- Neue DeviceTypes: Shelly standardmäßig `TmrSwShellyC3V1`, Nous `TmrSwA8T`
  (über `TAKEOVER_DEVICE_TYPE` ausdrücklich anpassbar).
  Manifest, Artefakttyp und DeviceType müssen zum Ziel passen.
- Die neue Rescue verlangt keinen bestimmten Main-Projektnamen. Sie prüft das
  ESP-Image und weist bekannte Übergangs-/Takeover-Projektnamen ab. Signierte
  Artefakte müssen trotzdem zum neuen DeviceType und Prüfschlüssel passen.
- `spiffs` ist der Partitionsname/Subtyp; aktuell wird dort LittleFS verwendet.
  Ein SPIFFS-Image ist deswegen nicht automatisch kompatibel.
- App prüft Geometrie vor NVS-/Flash-/Hardwarezugriffen. Taster/Relais/LED nicht aus
  fremden Boardprofilen übernehmen. Main startet sicher mit Relais AUS.

Nach Takeover ist Main als noch nicht installiert zu behandeln. Die spätere App
muss unabhängig von Takeover funktionieren. Die neue Rescue verwendet die angegebenen DeviceTypes; alte signierte Artefakte
mit anderen DeviceTypes sind nicht kompatibel. Kein Hardwaretest der neuen Rescue
ist aus dem erfolgreichen Build abzuleiten.
