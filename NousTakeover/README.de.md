English version is [here](README.md).

# NousTakeover

Version: 1.06

Bootloader, Rescue und automatische Takeover-App sind eigenständige ESP-IDF-Projekte.
Environment und private Konfiguration: ../README.md. Nach deren Einrichtung im
Projektverzeichnis bauen:

```bash
bash tools/BuildTakeover.sh nous
```

Ausgabe ist `generated/NousTakeover/App/Takeover.bin` für den Tasmota-SafeBoot-
Herstellerupload. Dieses Eingangsformat ist das rohe ESP-App-Image; spätere Rescue-
Uploads verlangen signierte Artefakte. Das Buildskript führt keinen Geräteupload aus.
Ablauf und offene Tests: [Design](../Design.de.md) und [TODO](../TODO.de.md).

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
neuen Rescue-Status einschließlich unveränderter Geräte-MAC. Die PC-Schnittstellen
sind hostgeprüft; ohne frischen NOUS wurde der neue Gesamtweg nicht am Gerät geprüft.
Keine Gerätefreigabe allein aus dem Build oder den Hosttests ableiten.

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
