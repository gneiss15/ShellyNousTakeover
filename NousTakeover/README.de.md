English version is [here](README.md).

# NousTakeover

Version: 1.09

Bootloader, Rescue und automatische Takeover-App sind eigenständige ESP-IDF-Projekte.
Environment und private Konfiguration: [Haupt-README](../README.de.md). Nach deren
Einrichtung aus dem Repository-Hauptverzeichnis (`ShellyNousTakeover/`) bauen:

```bash
bash tools/BuildTakeover.sh nous
```

Ausgabe ist `generated/NousTakeover/App/Takeover.bin` für den Tasmota-SafeBoot-
Herstellerupload. Dieses Eingangsformat ist das rohe ESP-App-Image; spätere Rescue-
Uploads verlangen signierte Artefakte. Das Buildskript führt keinen Geräteupload aus.
Installation siehe unten; offene Tests: [TODO](../TODO.de.md).

## Artefaktinhalt und Installation

`generated/NousTakeover/App/Takeover.bin` ist relativ zum Repository-Hauptverzeichnis angegeben. Das rohe ESP-App-Image enthält die automatische Takeover, den neuen Bootloader, Rescue und die erwarteten Partitionstabellendaten als eingebettete Payloads. NOUS verwendet diese einzelne `.bin`-Datei statt eines ZIP-Pakets. Die vorhandene Partitionstabelle wird geprüft und beibehalten.

Das Image am generierten Pfad belassen und über das PC-Skript durch Tasmota SafeBoot installieren. Nach Erfüllen der Voraussetzungen und Setzen der Env-Variablen einschließlich `NOUS_IP` gemäß [Haupt-README](../README.de.md#pc-vorprüfung-und-übernahme) aus dem Repository-Hauptverzeichnis ausführen:

```bash
# Rein lesende Gerätevorprüfung; kein Neustart oder Upload:
python3 tools/NousTakeover.py
```

Bei aktivierter Tasmota-Authentifizierung vor den PC-Aufrufen `NOUS_PASSWORD` und optional `NOUS_USER` (Standard `admin`) setzen. Das sind die Tasmota-Webzugangsdaten, getrennt von den einkompilierten WLAN-Einstellungen.

Vor dem nächsten Befehl stabile Stromversorgung sicherstellen und angeschlossene Verbraucher entfernen. Dieser Befehl verändert das Gerät:

```bash
python3 tools/NousTakeover.py --execute
```

Das Skript prüft das Image und das Gerät erneut, schaltet auf Tasmota SafeBoot um und bestätigt dessen Identität und Uploadweg. Dann lädt es `Takeover.bin` einmal hoch. Takeover startet automatisch und führt ihre Prüfungen und Migration aus; das Skript wartet auf die neue Rescue und prüft Geräte-MAC, DeviceType, Geometrie, Bootauswahl und dass noch keine Main installiert ist. PC und Skript bis zum Abschluss laufen lassen. Ein unbestätigter Upload wird nicht automatisch wiederholt. Spätere Main-/Dateisystem-Uploads erfolgen als signierte Artefakte über Rescue, siehe [App-Anforderungen](../AppRequirements.de.md).

Der begrenzte Bootloader-Writer in `LoaderWriter/` sichert die konkreten Originalbytes
im RAM und schreibt ausschließlich `0x1000` bis `0x7FFF`. Er verlangt eine vorherige
Identitätsfreigabe und verifizierte Rescue. Partitionstabelle und OTA-Partition werden
vor und nach dem Schreiben verglichen. Bei Schreibfehlern restauriert und prüft er
den Original-Bootloader, solange diese Invarianten unverändert sind. Fehlgeschlagene
Rücknahme, Schreibschutzwiederherstellung oder Invariantenprüfung sperren den Neustart.
Der Writer ersetzt keine Geräte-/Firmware-/Bootloader-Herkunftsprüfung.

Hostprüfung ohne Gerät:

```bash
python3 NousTakeover/LoaderWriter/VerifyLoaderWriter.py
```

Die gemeinsame Zustandsmaschine unterstützt die Nous-Reihenfolge Rescue → Bootloader
→ Rescue-Bootauswahl, ohne eine Partitionstabelle zu schreiben. Die App startet
AP+STA und Webdiagnose vor den Guards und beginnt nach einer LAN-IP automatisch.
Bei Fehlern bleiben Diagnose und Status erreichbar; kein erzwungener Neustart.

Die App prüft reale Chip-/Flash-/Security-/Slotdaten, Original-Loaderidentität,
Partitionstabelle, vorhandenes SafeBoot-Image, Bootauswahl und Payloads. Rescue wird
vollständig einschließlich gelöschtem Restbereich geprüft. Erhaltene Bereiche
(Flash-Vorbereich, Partitionstabelle/NVS, laufende Main und Dateisystem) werden
unabhängig vor/nach dem Ablauf verglichen. Bootloader und OTA-Partition werden für
begrenzte Fehler-Rücknahme gesichert. Die alte SafeBoot-App wird nicht gesichert:
Rücknahme bedeutet einen verifizierten Bootweg zur laufenden Takeover, keine
Wiederherstellung der ursprünglichen Tasmota oder ihrer alten SafeBoot-App.

Die PC-Vorprüfung und der einmalige SafeBoot-Upload sind in `tools/NousTakeover.py`
implementiert; Bedienung im Projekt-README. Die abschließende Prüfung verlangt den
neuen Rescue-Status einschließlich unveränderter Geräte-MAC. Mit dem früheren Migrationsverfahren habe ich vier NOUS A8T erfolgreich übernommen.
Die letzte, eigenständige Implementierung dieses Repositories wurde gebaut und
hostgeprüft; nur dieser neue Gesamtpfad ist noch nicht an einem unveränderten Gerät
getestet, da alle vier verfügbaren NOUS bereits umgestellt sind. Die bisherigen
Erfolge sind praktische Erfahrungen mit dem Vorgänger, kein Gerätetest dieser
letzten Implementierung.

## Unterstützte Eingangsbasis

Erforderlich ist Tasmota mit tatsächlich vorhandenem SafeBoot-Layout. Tasmota führte
SafeBoot in Version 12 ein; die Versionsnummer allein ist keine Layoutfreigabe.
Es gibt abweichende SafeBoot-Partitionierungen und benutzerdefinierte Builds:
[Tasmota SafeBoot-Dokumentation](https://tasmota.github.io/docs/Safeboot/).
Für NOUS A8T gilt ausschließlich die 4-MiB-Geometrie aus `partitions.csv`.

Die historisch verwendete Eingangsbasis war `14.3.0.1 (tasmota32)`, Build
`2024-11-05T10:09:04`. `OriginalFirmware.json` enthält die geprüfte Original-Bootloader-
und Partitionstabellenidentität aus dem damaligen Originaldump, keine Herstellerbinaries
oder Konfiguration. Die Versions-/Buildangabe stammt aus dem archivierten Konsolenlog;
die entsprechenden Felder des ESP-App-Descriptors im Dump sind leer. Der Bootloader
ist als ESP32-DIO-Image samt Checksumme, angehängtem Digest und gelöschtem Restbereich
geprüft; die Partitionstabelle samt MD5 entspricht exakt `partitions.csv`.

Damit ist eine konkrete Eingangsbasis identifiziert. Andere SafeBoot-Versionen benötigen
eine belegte kompatible Bootloader-/Layoutidentität. Ein normaler Tasmota-App-Update
beweist keinen Wechsel des Bootloaders. Die Takeover muss den vorhandenen Loader und
das Layout direkt prüfen; der PC prüft vor OTA die noch laufende Tasmota und den
SafeBoot-Uploadweg. Historische HTML-Dateien und Originaldump sind keine Buildvoraussetzung.
