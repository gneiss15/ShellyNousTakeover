English version is [here](Design.md).

# Übernahmeablauf und Bereinigung

Version: 1.05
Stand: 2026-10-05

## Aufgabenverteilung

PC: Toolchain/Abhängigkeiten beschaffen und prüfen, private Konfiguration/Schlüssel
validieren, Payloads bauen und prüfen, Herstellergerät vor dem Upload prüfen,
passendes OTA-Paket hochladen, Status anzeigen und abschließende Rescue-Erreichbarkeit
prüfen. Der PC steuert später keine einzelnen Flash-Writes.

App: AP+STA und Webdiagnose zuerst starten, echte Flash-/Chip-/Security-/Partitions-
und Imageprüfungen durchführen, nur nach vollständiger Freigabe selbständig schreiben,
vollständig rücklesen, geschützte Bereiche prüfen, möglichen Fehler-Rollback durchführen,
Bootziel setzen und Rescue starten. Web zeigt Phase, Fehler und Rücknahmestatus.
Eine unklare Flash-/Schutzlage verbietet Neustart und weitere normale Writes.

Nicht jede Herkunftsprüfung lässt sich nach dem Upload rekonstruieren. Die laufende
App ist dann Takeover, nicht die vorherige Hersteller-Firmware. Beim Shelly kann
Takeover das erhaltene Stock-app_0 prüfen; Nous/Tasmota kann seine vorherige App durch
OTA ersetzen. Der PC muss deshalb vor dem Upload den unterstützten Herstellerweg
prüfen. Chip/Flash allein beweisen weder Gerätemodell noch sichere GPIO-Belegung.

## Shelly: notwendiger finaler Weg

1. Hersteller-OTA installiert ausschließlich Takeover-app_1 und das zugehörige
   leere fs_1. Bootloader/Partitionstabelle werden damit nicht installiert.
2. Takeover prüft Chip, Flash, Security, alte Partitionstabelle, laufenden Slot,
   bekannte Original-Bootloader-Identität, SH0S, Stock-App und eingebettete Payloads.
3. Finalen Dual-Bootloader nur bei Bedarf schreiben und vollständig rücklesen.
   Bereits bytegleich vorhandenen Loader nicht neu schreiben. Verifiziert gesicherte
   Originalbytes für begrenzte Rücknahme behalten; kein Testneustart erforderlich.
4. Danach Rescue, NVS-/OTA-Partitionen und begrenzte Rücknahme-Metadaten vorbereiten,
   rücklesen und erhaltene Bereiche prüfen. Der bestehende MigrationStage-Writer
   verlangt bereits den finalen Loader und versiegelt dessen Hash in der Baseline.
   Ein Loaderwechsel nach dem Staging würde diese Baseline ungültig machen.
5. Neue Partitionstabelle schreiben/rücklesen; finale Invarianten prüfen und Rescue
   als Bootziel verwenden. Bei Fehlern vor Neustart nur bestätigte Originaldaten
   über begrenzte Writer wiederherstellen.
6. Rescue startet, bietet signierte Uploads an und weist alte Takeover als Main ab.

Der Dual-Bootloader ist nicht temporär. Unter alter Partitionstabelle kennt er
SH0S/Stock, unter neuer Partitionstabelle den Factory-Rescue-/Main-Weg und GPIO7.
Nach dem Wechsel ist der Stock-Pfad inaktiv. Der Loader muss nicht durch einen
zweiten „normalen“ Loader ersetzt werden. Ein nur auf die neue Partitionstabelle
zugeschnittener Loader wäre zusätzliche Entwicklung/Prüfung und erschwert die
Rücknahme, ohne den Nutzerablauf zu verbessern.

## Was aus dem bisherigen Ablauf wegfallen kann

- Readout-Erstinstallation, GPIO-Ermittlung, Padding-Schreibtest und Testnodeabläufe:
  waren Entwicklung/Hardwareidentifikation, keine Nutzer-Migrationsschritte.
- Original -> StockLayoutBootloader -> DualLayoutBootloader: frische Geräte können
  direkt den finalen Dual-Bootloader erhalten. Vorgänger-Loader müssen für den
  frischen veröffentlichten Weg nicht eingebettet/unterstützt werden.
- Separater Loader-Testneustart vor der neuen Partitionstabelle: für den finalen
  Ablauf nicht grundsätzlich nötig; Readback/Identitäts-/Bereichsprüfungen bleiben.
- Wiederholte unabhängige 8-MiB-PC-Dumps zwischen jeder Phase und PC-gesteuerte
  Einzelbuttons: können aus dem Nutzerablauf entfallen. Bisherige Writer verlangen
  aber Baselines/Checkpoints; diese Voraussetzungen müssen gezielt in der App neu
  erfüllt werden. Nicht einfach vorhandene Prüfungen auskommentieren.
- Stock-Roundtrip und erneuter Takeover-Upload zur Aktualisierung der Entwicklungs-
  App: für eine frisch gebaute finale Takeover entfallen.
- Herstellerpakete, Chats und echte Captures als Buildvoraussetzung: durch aus
  freigegebenen Quellen reproduzierbare Payloads und geprüfte Identitätsmetadaten
  ersetzen. Original-Loader muss nicht als proprietäres Binary im Repo liegen:
  Rücknahme benötigt verifiziert gesicherte Originalbytes des konkreten Geräts.

## Was erhalten bleibt

- Hersteller-/Uploadweg-Vorprüfung am PC; Payload-/Signatur-/Geometrieprüfungen beim Build.
- Autoritative App-Guards; SDK-Partitionstabelle muss zum wirklichen Offset passen.
- Bekannter Original-Loader, sichere Stock-Bootauswahl, geschützte Factory-Daten.
- Erase/Write/Readback und Wiederherstellung der SDK-Schreibschutzkonfiguration.
- Eindeutige Phase, begrenzte Baseline/Originaldaten, geschützte-Bereiche-Prüfung,
  Fehlerdiagnose und Rücknahme soweit belegbar möglich.
- Abschließende Rescue-Erreichbarkeit vom PC. Die Takeover kann ihren eigenen
  erfolgreichen Neustart in eine andere App nicht allein bestätigen.

Nach Rescue-Start kein Stock-Rollback-Service. Main gilt als leer,
obwohl noch Takeover-Bytes vorhanden sind. Stromausfall beim Loader-/Partitions-
Write bleibt das bereits akzeptierte Risiko; keine Atomaritätsbehauptung.

## Nous: Unterschiede und vorhandene Lücken

Die vorhandene TasmotaMigration verwendet bereits die Ziel-Partitionstabelle:
Rescue safeboot 0x10000/0xD0000, Main app0 0xE0000/0x2D0000, FS 0x3B0000/0x50000.
Sie schreibt/verifiziert Rescue, ersetzt/verifiziert den Loader bei 0x1000 und
wählt Rescue. Kein Shelly-Dual-Loader, kein SH0S und kein Partitionstabellenwechsel
bei dieser unterstützten Eingangsgeometrie erforderlich.

Der bisherigen TasmotaMigration fehlt jedoch Netzwerkdiagnose vor Fehlerguards:
StopWithError wartet dauerhaft, Web wird hauptsächlich im AlreadyMigrated-Modus
bereitgestellt. Vor Wiederverwendung sind sichere Modellerkennung/Bootloader-
Identität/Secure-Boot-Prüfung, dauerhafte Diagnose und phasengerechte Rücknahme
zu prüfen bzw. ergänzen. Bisherige Erfolge rechtfertigen kein unverändertes Kopieren.

Die neue Nous-App startet Netzwerk/Webdiagnose vor Guards und verwendet die bekannte
Original-Loaderidentität aus OriginalFirmware.json sowie die exakte Partitionstabelle.
Sie schreibt zuerst Rescue, verifiziert Payload und gelöschten Rest sowie das SDK-Image,
ersetzt dann den Loader und wählt erst danach Rescue. NVS, laufende Main und FS bleiben
erhalten und werden per unabhängigen Bereichshashes geprüft. Original-Loader und
OTA-Partition liegen für Rücknahme im RAM. Alte SafeBoot ist nicht gesichert; die
begrenzte Rücknahme erhält den Bootweg zur laufenden Takeover, keine ursprüngliche
Tasmota-Wiederherstellung. Keine Rücknahme bei unklarer Schutz-/Flashlage. Hardware und
SDK-Imageprüfungen sind in Hosttests gemockt; Build/Hosttest ist kein neuer Gerätetest.

## Nächste Umsetzung

1. Minimal benötigte Firmware-/Rescue-/Updatequellen in dieses Projekt übernehmen;
   relative Buildpfade auf neue Struktur umstellen, keine Rückverweise auf Prjs.
2. Einheitliche private Konfiguration und Toolchain-Download/Versionsprüfung; keine
   Mischung aus SDK 5.5.1 und der derzeitigen Nous-Bootloader-Vorgabe 5.5.5 über
   stilles ALLOW_IDF_VERSION_MISMATCH. Kompatibilität konkret festlegen/testen.
3. App-interne automatische Zustandsmaschine und Webstatus, Baseline/Rücknahme
   gezielt auf finalen Weg reduzieren. Host-Fehlerinjektion weiterhin separat testen.
4. Eigenständiger Build, dann Testnode und geeignetes frisches Gerät. Keine neue
   Hardwarefreigabe aus der bisherigen Prüfung ableiten.

## Präzisierung der Nous-Fehlerfolgen

Ein Guardfehler vor Flash-Writes verursacht eine nicht per Web diagnostizierbare
Warteschleife, aber nicht automatisch einen beschädigten Bootloader. Der bisherige
Bootloader und die laufende Takeover können noch vorhanden sein. Ein Neustart ist
keine Fehlerbehebung; die App kann denselben Fehler wieder erreichen.
Nach fehlerhaftem Loader-Erase/Write ist dagegen die Bootfähigkeit ungesichert.
Der bisherige Code restauriert dann keinen gesicherten Original-Loader. Kein
pauschales „jeder Fehler brickt“ und keine zugesicherte Netzwerkwiederherstellung.

## Einheitliche Toolchain

Für beide Gerätewege einschließlich Rescue ausschließlich ESP-IDF einsetzen.
Der bestehende schmale IDF-Adapter aus der Shelly-Rescue ersetzt die wenigen
Arduino-API-Aufrufe (String/GPIO/delay); kein Arduino-Core-/CLI-Build erforderlich.
Der bisherige Nous-Rescue-Build bleibt Referenz, keine neue externe Voraussetzung.
Ein Nous-IDF-Build ist noch kein durch diese Entscheidung nachgewiesener Gerätetest.

## Entwicklungsprüfungen

VerifyRescueGuards.py benötigt als Hosttest g++ und OpenSSL-Entwicklungsheader
(z.B. libssl-dev). VerifyMigration.py benötigt Host-cc und diese Header.
Das sind Voraussetzungen der Tests, keine zusätzliche Firmware-Toolchain.
Die Migration-Fehlerinjektion prüft synthetischen Flash mit echten SHA256-Hashes;
mit --shelly-geometry verwendet sie die 8-MiB-Geometrie, sonst die 4-MiB-Testgeometrie.
