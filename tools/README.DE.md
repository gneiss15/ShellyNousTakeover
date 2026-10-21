<!-- tools/README.DE.md, Version: 1.01 -->
# Werkzeuge

[English](README.md) · [Projektanleitung](../README.de.md)

Alle Aufrufe erfolgen vom Repository-Stamm. Voraussetzungen und Umgebungsvariablen stehen in der Projektanleitung. Buildskripte übertragen nichts auf Geräte; Schreibvorgänge gehören zu den ausdrücklich gestarteten PC-Übernahmeabläufen.

| Werkzeug | Funktion |
| --- | --- |
| [CheckEnvironment.sh](CheckEnvironment.sh) | Prüft Build-Umgebung und erforderliche externe Konfiguration. |
| [SetupToolchain.sh](SetupToolchain.sh) | Prüft bzw. installiert die in Toolchain.lock.json festgelegten Werkzeuge. |
| [VerifyToolchain.py](VerifyToolchain.py) | Prüft SDK-Commit, Submodule und Compiler gegen die Lockdatei. |
| [BuildBootloader.sh](BuildBootloader.sh) | Baut den finalen Bootloader für shelly oder nous. |
| [BuildRescue.sh](BuildRescue.sh) | Baut und signiert die eigenständige Rescue. |
| [BuildTakeover.sh](BuildTakeover.sh) | Baut die Takeover-App mit eingebetteten, geprüften Payloads. |
| [BuildExample.sh](BuildExample.sh) | Baut das MiniMain-Beispiel für die gewählte Gerätefamilie. |
| [ShellyTakeover.py](ShellyTakeover.py) | Shelly-PC-Ablauf: Vorprüfung, optionales Herstellerupdate, einmaliger Upload und Rescue-Prüfung. |
| [NousTakeover.py](NousTakeover.py) | Nous-PC-Ablauf: Vorprüfung, einmaliger SafeBoot-Upload und Rescue-Prüfung. |
| [StockFirmware.py](StockFirmware.py) | Hilfsfunktionen für geprüfte Herstellerpakete und Stock-Updates. |
| [PackageShelly.py](PackageShelly.py) | Erzeugt das Shelly-OTA-Paket im unterstützten Herstellerformat. |
| [ValidateTakeoverPackage.py](ValidateTakeoverPackage.py) | Prüft das Shelly-Takeover-Paket und eingebettete Payloads. |
| [ValidateNousTakeover.py](ValidateNousTakeover.py) | Prüft das Nous-SafeBoot-Uploadimage und eingebettete Payloads. |
| [PreparePrivate.py](PreparePrivate.py) | Validiert externe Zugangsdaten/Schlüssel und erzeugt private Build-Header ohne Ausgabe der Werte. |
| [DeviceTypeArtifacts.py](DeviceTypeArtifacts.py) | Erzeugt DeviceType-Metadaten, Update-Artefakte und den Public-Key-Header. |
| [BuildFiles.py](BuildFiles.py) | Schreibt generierte Build-Eingaben nur bei geändertem Inhalt; erhält inkrementelle Builds. |
| [VerifyBuild.py](VerifyBuild.py) | Prüft gebaute Images, Chip-/SDK-Geometrie und signierte Rescue-Payloads. |

Die übrigen `Verify*.py` sind Hostprüfungen für Geräte-Vorprüfungen, Migrationsabläufe, Rescue-Schutzmechanismen und Build-Hilfen. Prüfungen mit simuliertem Flash ersetzen keinen Gerätetest. Weitere Low-Level-Tests liegen bei den jeweiligen Bootloader-/LoaderWriter-/Migration-Komponenten.

[stock/](stock/README.DE.md) beschreibt Herstellerpaket-Prüfung und Dateiübertragung. `certificates/` enthält Zertifikate für die Prüfung der Herstellerfirmware. Generierte Dateien und Prüfberichte bleiben lokal; private Konfiguration und Schlüssel liegen außerhalb des Repositorys.
