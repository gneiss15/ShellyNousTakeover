English version is [here](README.md).

# ShellyNousTakeover

Dokumentversion: 1.29

ShellyNousTakeover überführt einen unterstützten Shelly Plug M Gen3 oder Nous A8T
in ein System mit eigenständiger Rescue App und Hardware-Safe-Boot. Die Takeover enthält
den finalen Bootloader und die Rescue. Nach erfolgreicher Übernahme kann eine
passende Haupt-App über die Rescue installiert werden.

**Auf Hardware getestet:** Der Tag [hardware-tested-2026-10-21](https://github.com/gneiss15/ShellyNousTakeover/tree/hardware-tested-2026-10-21) verweist auf den bisherigen GitHub-Stand, den der Projektbetreuer mit Shelly und Nous getestet hat.

**Aktueller Stand: noch nicht auf Hardware getestet.** Der Shelly-Build erkennt das ursprüngliche Stock-Layout und das größere Layout von PlugMG3 2.2.0 Stable. Takeover wählt die passende Rescue und den passenden Dual-Bootloader. Jeder Bootloader enthält nur seine eigene Stock- und Zielpartitionstabelle. Die Hardwareprüfung des neuen Layouts und der automatischen Rückkehr zu Stock steht aus.

Produktversionen stehen zentral in `Versions.txt` im Repository-Stamm: Shelly- und Nous-App/Rescue sowie das MiniMain-Beispiel haben jeweils einen eigenen Eintrag. IDF-Projektkennung, Rescue-Status, Paketprüfung und PC-seitige Checks lesen diese Werte. Generierte Artefakte werden nicht direkt bearbeitet und Produktversionen nicht zusätzlich an anderer Stelle eingetragen.

## Rückmeldungen willkommen

Ich freue mich ausdrücklich über Rückmeldungen: Erfahrungen mit unterstützten Geräten, Probleme, unklare Anleitungen und Verbesserungsvorschläge. Bitte dafür die [GitHub Issues](https://github.com/gneiss15/ShellyNousTakeover/issues) nutzen. Bei technischen Rückmeldungen helfen Gerätemodell, ursprüngliche Firmware-Version/Build, der betroffene Schritt und die Fehlermeldung. Auch erfolgreiche Tests sind willkommen. Vor dem Teilen von Logs oder Anhängen WLAN-Zugangsdaten, Passwörter und private Schlüssel entfernen.

## AquariumControl

Die vollständigen Aquarium-Anwendungen liegen in [AquariumControl](https://github.com/gneiss15/AquariumControl): [TmrSwShelly](https://github.com/gneiss15/AquariumControl/tree/main/TmrSwShelly), [TmrSwA8T](https://github.com/gneiss15/AquariumControl/tree/main/TmrSwA8T), Feeder, MultiTimer und Dashboard. ShellyNousTakeover übernimmt die Erstübernahme und den Rescue-Einstieg; AquariumControl liefert die Main-Anwendungen. AquariumControl ist Work in progress; Anmerkungen und Testergebnisse sind willkommen.

## Lizenz

Required Notice: Copyright 2026 Günter Neiß

Die eigenen Projektbestandteile stehen unter der
[PolyForm Noncommercial License 1.0.0](LICENSE.md). Nichtkommerzielle Nutzung ist
nach deren Bedingungen erlaubt; kommerzielle Nutzung außerhalb der dort erlaubten
Zwecke benötigt eine gesonderte Lizenz von Günter Neiß. Die Lizenz enthält eigene
Regelungen für gemeinnützige und öffentliche Einrichtungen.

Diese Lizenz gilt nur für eigene Projektbestandteile. Fremdkomponenten unterliegen
weiterhin ihren jeweiligen Lizenzen; deren Hinweise und Bedingungen bleiben erhalten.
Siehe [THIRD_PARTY.md](THIRD_PARTY.de.md). Keine Garantie; es gelten auch die unten
beschriebenen Hardware- und Stromausfallrisiken.

## Beispiel-Apps

Die [Mini-Examples für Shelly und Nous](Examples/README.de.md) zeigen eine baubare
Main-App mit eigenem Webstatus, sicher ausgeschaltetem Relais und Rückwechsel zu
Rescue. Sie verwenden dieselbe Toolchain, private Konfiguration und Signierung.
Die vollständigen TmrSw-Anwendungen werden in AquariumControl gepflegt, siehe oben.

**Noch nicht praktisch geprüft:** eine frische Shelly-Übernahme mit der beschreibbaren Kalibrierpartition, MiniMain auf beiden Gerätefamilien, der vollständige Nous-Ablauf sowie zusätzliche Fehlerfälle mit ungültiger Main oder unbrauchbarem Dateisystem. Hosttests ersetzen diese Gerätetests nicht.

Die Kalibrierpartition ist im Ziel-Layout beschreibbar. Das tatsächliche Schreiben geänderter Shelly-Kalibrierwerte und ihre Wiederherstellung sind noch nicht am Gerät geprüft.

## DeviceType

Der DeviceType beschreibt die Upload-Kompatibilität, unabhängig von Gerätename und
Takeover-Projektname. Standard: Shelly `TmrSwShellyC3V1`, Nous `TmrSwA8T`.
Ein anderer Typ wird vor dem Build und dem PC-Übernahmeaufruf ausdrücklich gesetzt:

```bash
export TAKEOVER_DEVICE_TYPE='TmrSwShellyC3V1'
```

Der Wert muss aus höchstens 31 ASCII-Buchstaben/Ziffern bestehen und mit einem
Buchstaben beginnen. Rescue-Build, signierte Artefakte, späterer Main-Build und
PC-Abschlussprüfung müssen denselben Typ verwenden. Eine Environment-Änderung
ändert keine bereits installierte Rescue.

## Hardware-Safe-Boot und Rescue

Der Bootloader startet die Rescue App, wenn der Gerätetaster beim Einschalten bzw.
Reset mindestens eine Sekunde gehalten wird. Zur sicheren Bedienung den Taster
mindestens zwei Sekunden halten. Taster: Shelly GPIO7, Nous A8T GPIO4, jeweils LOW
bei gedrücktem Taster.

Dieser Rettungsweg funktioniert unabhängig von der Haupt-App und ihrem Dateisystem.
Eine defekte, nicht startende oder im Betrieb hängende Haupt-App muss dafür keinen
Netzwerkdienst mehr bereitstellen: Gerät mit gedrücktem Taster neu einschalten.
Das Gerät bootet dann in die Rescue App, NVS und Dateisystem werden dabei nicht verändert.

Die Rescue:

- läuft in einer eigenen App-Partition mit eigener WLAN-Konfiguration und eingebauter
  Weboberfläche; benötigt keine Dateien oder Webserver der Haupt-App;
- verbindet sich mit dem einkompilierten WLAN und stellt zusätzlich einen Access Point
  bereit; der Linux-PC kann über LAN im selben Heimnetz auf sie zugreifen;
- nimmt getrennte, signierte Firmware-/Dateisystem-Uploads entgegen, prüft Zieltyp,
  Signatur und Payload und liest geschriebene Daten zur Prüfung zurück;
- startet die Haupt-App erst nach den vorgesehenen Image-/Aktivierungsprüfungen;
- zeigt ihren Betrieb durch SOS-Blinken an, beim Shelly in Rot.

Dies ist ein unabhängiger Rettungsweg für Haupt-App und Dateisystem. Ein beschädigter
Bootloader, eine beschädigte Partitionstabelle oder eine beschädigte Rescue selbst
können ihn verhindern. Safe Boot beseitigt nicht das Risiko während der Übernahme.

## Voraussetzungen

- Linux-PC mit Bash, Python 3, Git, CMake, Ninja und OpenSSL.
- ESP-IDF 5.5.1 mit SDK-Pythonumgebung und den Espressif-Compilern für ESP32-C3
  (RISC-V) und/oder ESP32 (Xtensa), entsprechend dem gewählten Gerät.
- Unterstütztes Ausgangsgerät im Heimnetz; feste IPv4-Adresse als DHCP-Reservierung.
- Passende WLAN-Konfiguration und ein eigenes Signierschlüsselpaar außerhalb des Projekts.

Shelly-Ausgangspunkt: Plug M Gen3 / S3PL-30110EU, ESP32-C3 Revision 4, 8 MiB,
Stock PlugMG3 in `app_0`. Der PC prüft Modell, Sicherheitszustand und aktiven
Stock-Slot. Takeover prüft vor dem Schreiben die tatsächliche Partitionstabelle
und den Bootloader.
Nous-Ausgangspunkt: A8T mit der passenden Tasmota-Partitionstabelle gemäß
[AppRequirements.md](AppRequirements.de.md).

Der PC darf per Ethernet verbunden sein. Beim Shelly muss auch das Gerät den
lokalen OTA-HTTP-Server des PCs erreichen können. Takeover und Rescue verwenden DHCP;
die Routerreservierung hält ihre Adresse gleich.

## Toolchain prüfen oder einrichten

Die SDK- und Compilerstände sind in `Toolchain.lock.json` festgelegt. Vor der
Prüfung oder Installation die Installationsziele wählen:

```bash
export TAKEOVER_IDF_PATH="$HOME/tools/esp-idf-v5.5.1"
export TAKEOVER_IDF_TOOLS_PATH="$HOME/tools/espressif"
```

`TAKEOVER_IDF_PATH` bezeichnet das SDK-Quellverzeichnis; `TAKEOVER_IDF_TOOLS_PATH`
enthält Compiler, Werkzeuge und die SDK-Pythonumgebung. Die Beispielpfade durch
eigene Zielpfade außerhalb des Repositories ersetzen. Diese Installationen können
auch andere ESP-IDF-Projekte verwenden: dasselbe SDK nutzen und vor dem Einlesen
seiner `export.sh` den Wert `IDF_TOOLS_PATH` auf dasselbe Werkzeugverzeichnis setzen.
Bei passenden Toolchain-Anforderungen ist keine separate Installation je Projekt
nötig. Logs bleiben im Verzeichnis `generated/` dieses Repositories.

Die reine Prüfung benötigt weder private Konfiguration noch eine Geräteadresse:

```bash
bash tools/SetupToolchain.sh --check
```

Bei fehlender Installation lädt folgender ausdrücklich gewählter Aufruf das
festgelegte ESP-IDF und installiert dessen Werkzeuge für beide Geräte:

```bash
bash tools/SetupToolchain.sh --install
```

Für die Installation werden Internetzugang und die Linux-Buildvoraussetzungen
von [Espressif](https://docs.espressif.com/projects/esp-idf/en/v5.5.1/esp32/get-started/linux-macos-setup.html)
benötigt, insbesondere Python-Venv/Pip, Flex, Bison, Gperf und die dort genannten
Systembibliotheken. Das Skript installiert keine Systempakete. Bestehende SDKs
mit abweichendem Commit, Änderungen oder fehlenden/abweichenden Submodulen werden
abgewiesen und nicht zurückgesetzt. Einen neuen, noch nicht vorhandenen SDK-Pfad
verwenden, wenn die vorhandene Installation davon abweicht.

Die offiziellen Werkzeugdownloads werden durch den festgelegten SDK-Installer
und dessen Prüfsummenmanifest geprüft. Die Python-Abhängigkeiten werden nach den
Requirements/Constraints dieses SDKs aufgelöst; ein vollständiger Python-Paketlock
ist damit nicht zugesichert. Installations-/Aktivierungslogs liegen in `generated/`.
Die Buildskripte prüfen den SDK- und jeweiligen Compilerstand erneut vor dem Build.

## Externe Einstellungen

Vor einem Aufruf die Beispielpfade und Geräteadresse ersetzen:

```bash
export TAKEOVER_PRIVATE_DIR="$HOME/takeover-private"
export TAKEOVER_IDF_PATH="$HOME/tools/esp-idf-v5.5.1"
export TAKEOVER_IDF_TOOLS_PATH="$HOME/tools/espressif"
# Optionaler DeviceType für Shelly; für Nous siehe unten.
export TAKEOVER_DEVICE_TYPE="TmrSwShellyC3V1"
export SHELLY_IP="192.168.1.50"
# Für Nous statt SHELLY_IP:
export NOUS_IP="192.168.1.51"
```

TAKEOVER_PRIVATE_DIR enthält Secrets.local.json sowie private.key/public.key.

`TAKEOVER_DEVICE_TYPE` ist optional und gilt für den jeweiligen Build und
PC-Übernahmeaufruf. Ohne gesetzte Variable wird der Typ aus `<Ziel>/DeviceType.txt`
verwendet: Shelly `TmrSwShellyC3V1`, Nous `TmrSwA8T`.
Für Nous den obigen Shelly-Wert vor dessen Build/Aufruf ersetzen:

```bash
export TAKEOVER_DEVICE_TYPE="TmrSwA8T"
```

Oder `unset TAKEOVER_DEVICE_TYPE` ausführen, um wieder den jeweiligen Projektstandard
zu verwenden. Der DeviceType muss zum gewünschten späteren Main-/Rescue-Uploadformat
passen; er ist kein Gerätename. Siehe [DeviceType](#devicetype).


### Secrets.local.json anlegen

Nach Setzen von TAKEOVER_PRIVATE_DIR die Vorlage dorthin kopieren; eine bereits
vorhandene Secrets.local.json nicht überschreiben:

```bash
mkdir -p "$TAKEOVER_PRIVATE_DIR"
(umask 077; cp -n Secrets.example.json "$TAKEOVER_PRIVATE_DIR/Secrets.local.json")
chmod 600 "$TAKEOVER_PRIVATE_DIR/Secrets.local.json"
```

Die Platzhalter aus [Secrets.example.json](Secrets.example.json) vor dem Build
im externen Verzeichnis ersetzen. Die JSON-Datei enthält:

| Feld | Bedeutung |
|---|---|
| `WlanSsid` | Name des Haupt-WLANs, erforderlich, höchstens 31 UTF-8-Bytes |
| `WlanPw` | Haupt-WLAN-Passwort; leer ausschließlich bei offenem WLAN |
| `WlanSsid2` | Optionales Ersatz-WLAN; leer deaktiviert dieses Profil |
| `WlanPw2` | Passwort des Ersatz-WLANs; ohne Ersatz-WLAN leer lassen |

WPA-Passwörter: 8–63 UTF-8-Bytes oder ein 64-stelliger hexadezimaler WPA-Schlüssel.
JSON-Sonderzeichen wie Anführungszeichen und Backslash entsprechend escapen.
`Common` gilt für beide Geräte. `ShellyTakeover` bzw. `NousTakeover` kann einzelne
Felder überschreiben. Priorität, aufsteigend: Felder direkt im JSON-Root → Common
→ gerätespezifischer Abschnitt → Projects/ShellyTakeover bzw. Projects/NousTakeover.
Die letzten beiden Projects-Abschnitte sind optional; die Vorlage braucht sie nicht.

Schlüssel gehören nicht als JSON-Inhalt in diese Datei: private.key enthält den
privaten RSA-Schlüssel im PEM-Format, public.key den passenden öffentlichen
PEM-Schlüssel. Passphrasegeschützte private Schlüssel werden vom unbeaufsichtigten
Build derzeit nicht unterstützt. Beide Dateien neben Secrets.local.json ablegen;
private.key nur für den Besitzer lesbar halten. Keine echte private Datei in das
Projektverzeichnis kopieren oder ins Repository aufnehmen.

Der private Schlüssel dient ausschließlich dem Signieren am PC; die Rescue erhält
den öffentlichen Prüfschlüssel. WLAN-Daten werden in Takeover und Rescue einkompiliert,
nicht im Bootloader. Generierte Header und Firmware können private Daten enthalten
und dürfen nicht veröffentlicht werden.

Die beiden IDF-Pfade bezeichnen SDK-Quellen und heruntergeladene SDK-Werkzeuge.
Beide Gerätewege verwenden ESP-IDF.

Umgebung ohne Download, Build oder Geräteanfrage prüfen:

```bash
bash tools/CheckEnvironment.sh shelly
# oder:
bash tools/CheckEnvironment.sh nous
```

## PC-Vorprüfung und Übernahme

Nach Setzen der Pfade und Geräte-IP die vollständige Takeover bauen:

```bash
bash tools/BuildTakeover.sh shelly
# Für Nous stattdessen:
bash tools/BuildTakeover.sh nous
```

Lesende Vorprüfung am Gerät, ohne Neustart oder Upload:

```bash
python3 tools/ShellyTakeover.py
# Für Nous:
python3 tools/NousTakeover.py
```

Für die direkte Übernahme muss Stock in `app_0` laufen. Der PC akzeptiert jede
Stock-Version und Build-ID. Ob das Layout passt, prüft die Takeover nach dem Start
direkt am Gerät. Der Standardaufruf liest nur den Gerätestatus.
Der Nous-Check verlangt die bekannte Tasmota-Version samt Build aus
[NousTakeover/README.md](NousTakeover/README.de.md), 4 MiB Flash, aktives A8T-GPIO-Template,
LAN-Adresse und den SafeBoot-/Datei-Uploadweg. Original-Bootloader und Partitionstabelle
prüft anschließend die Takeover direkt am Gerät.

Der folgende Aufruf verändert das Gerät und startet die Übernahme. Erst verwenden,
wenn der Geräteeinsatz für den gewünschten Stand geprüft ist; aktuell gilt der
Entwicklungsstand oben. Zuvor eine stabile Stromversorgung sicherstellen und
angeschlossene Verbraucher trennen:

```bash
python3 tools/ShellyTakeover.py --execute
# Für Nous stattdessen:
python3 tools/NousTakeover.py --execute
```

Wer zuerst die aktuelle stabile Stock-Firmware installieren möchte, kann das normale Shelly-Update verwenden oder es über das Skript anstoßen.

```bash
python3 tools/ShellyTakeover.py --execute --update-stock
```

Das Skript fragt das Stable-Angebot am Gerät ab und nutzt Shellys Stable-Kanal. Danach wartet es, bis dasselbe Gerät den angebotenen Build 120 Sekunden lang in `app_0` mit fortschreitender Laufzeit meldet. Meldet Shelly kein Stable-Update, bleibt Stock unverändert und das Skript führt die normale Vorprüfung aus. Ob das Layout passt, prüft Takeover vor dem Schreiben direkt am Gerät. [Shelly-Dokumentation zu Firmware-Updates](https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/Shelly/)

Shelly: Das Skript stellt ausschließlich das gebaute OTA-Paket an einem lokalen
HTTP-Port bereit und sendet einmal Shelly.Update. Die passende LAN-Adresse des PCs
wird automatisch gewählt; bei mehreren Netzen kann TAKEOVER_HTTP_HOST die erreichbare
IPv4-Adresse festlegen. Die Firewall muss diesen vom Skript gewählten Port erlauben.
Nous: Das Skript wechselt zuerst nach SafeBoot, bestätigt diesen Zustand und lädt
danach einmal die Takeover-Datei hoch. Es sendet keinen Upload an die normale Main.

Beide Skripte warten auf den JSON-Status der neuen Rescue und prüfen Geräte-MAC,
Projekt/DeviceType/Version, gültige Geometrie, laufendes/gewähltes Rescue-Bootziel und
noch nicht installierte Main. Eine erfolgreiche HTTP-Uploadantwort allein zählt
nicht als erfolgreiche Übernahme. Verbindungsabbruch löst weder erneuten Upload noch
Reset aus; bei App-Fehler oder fehlender Abschlussbestätigung bleibt eine Fehlermeldung.
Rücknahme wird innerhalb der Takeover ausgeführt, soweit ihr geprüfter Zustand dies erlaubt.

Optional vorhandene Web-Anmeldung über SHELLY_USER/SHELLY_PASSWORD bzw.
NOUS_USER/NOUS_PASSWORD setzen; Standardbenutzer ist admin. Passwörter nicht in
Projektdateien oder Kommandozeilenargumenten ablegen. Skripte geben keine vollständigen
Geräteantworten oder Authentifizierungsdaten aus. Rescue-Status: GET /status, rein lesend.

## Migrationsprüfungen und Bootloader

Vor dem Schreiben prüft Takeover Hardware/Security, Original-Bootloader, Partitionstabelle, laufende App und eingebettete Payloads. Die Webdiagnose startet vor diesen Prüfungen und meldet Fehler per HTTP und UDP-Broadcast (Port 45678). Nach verifizierter Bootauswahl für Stock-`app_0` startet Takeover neu. In anderen Fehlerfällen bleibt die Diagnose erreichbar. Jeder Migrations-Schreibvorgang wird rückgelesen und geprüft; Rücknahme setzt eine bestätigte Ausgangsbasis und einen eindeutigen Schreibzustand voraus. Die originale Firmware prüft der PC vor dem Upload, da die laufende Takeover deren Version nicht aus ihrer eigenen Version ableiten kann.

Der Shelly-Dual-Bootloader bleibt der finale Bootloader und unterstützt die originale sowie die migrierte Partitionstabelle. Ein späterer Bootloader-Austausch ist nicht erforderlich. Die dokumentierten Build- und Migrationsskripte verwenden; generisches `idf.py flash` kann die benötigte Partitionierung oder Rescue überschreiben. Das Repository baut unabhängig von den älteren Prjs-Projektbäumen.

Beim Shelly installiert Stock-OTA zuerst Takeover und deren leeres Dateisystem. Takeover prüft und schreibt bei Bedarf den finalen Bootloader, bereitet Rescue und NVS-/OTA-Metadaten vor, schreibt die neue Partitionstabelle und startet Rescue. Beim Nous schreibt und prüft Takeover zuerst Rescue, danach Bootloader und Rescue-Bootauswahl; die unterstützte Partitionstabelle bleibt unverändert.

Nach geprüftem Rescue-Start ist die Übernahme abgeschlossen und Main gilt als leer. Rescue bietet keinen Stock-Rollback-Service. Die Migrationsrücknahme beschränkt sich auf Fehler vor diesem Abschluss und die für das jeweilige Gerät verfügbaren geprüften Daten; sie garantiert keine Wiederherstellung der originalen Hersteller-Firmware.

## Struktur

Werkzeugbeschreibungen: [Werkzeugübersicht](tools/README.DE.md).

- ShellyTakeover/: Shelly-Takeover, Bootloader, Rescue und Partitionstabellen.
- NousTakeover/: Nous-Takeover, Bootloader und Rescue.
- common/: gemeinsame Konfiguration und Updatebausteine.
- tools/: Toolchain-Einrichtung, Build und Hersteller-Upload.
- generated/: lokale Build-/Diagnoseausgaben; nicht veröffentlichen.
- .tools/: lokal heruntergeladene Toolchains; nicht veröffentlichen.

Flashadressen, Partitionsgrößen und Anforderungen an eine spätere Haupt-App stehen
in [AppRequirements.md](AppRequirements.de.md).

## Risiken – KEINE GARANTIE

Die Übernahme greift in Bootloader, Partitionstabelle und Flashinhalte ein.
Stromausfall, Unterbrechung oder Schreibfehler während kritischer Writes können
zu einem Gerät führen, das nicht mehr startet und per Netzwerk nicht mehr
wiederherstellbar ist. Dann kann serieller Hardwarezugriff erforderlich sein;
eine Wiederherstellung ist nicht garantiert. Prüfungen und mögliche Rücknahme
beseitigen dieses Risiko nicht. Während der Übernahme stabile Stromversorgung
sicherstellen und keinen Verbraucher betreiben.

**KEINE GARANTIE** für Erfolg, Fehlerfreiheit oder Wiederherstellbarkeit.
Verwendung auf eigenes Risiko.

## Rescue und Bootloader bauen

Nach Setzen der Pfade und vollständiger privater WLAN-Konfiguration:

```bash
bash tools/BuildBootloader.sh shelly
bash tools/BuildRescue.sh shelly
# Für Nous:
bash tools/BuildBootloader.sh nous
bash tools/BuildRescue.sh nous
python3 tools/VerifyBuild.py
```

Die abschließende Prüfung erwartet Builds beider Geräte. Ergebnisse liegen unter
`generated/<ShellyTakeover|NousTakeover>/<Bootloader|Rescue>/`. Kein Buildkommando
lädt etwas auf das Gerät. SDK-Compiler: Espressif GCC esp-14.2.0_20241119.

In Secrets.local.json werden WlanSsid/WlanPw und optional WlanSsid2/WlanPw2 aus
Root-Feldern, Common und gerätespezifischen Abschnitten zusammengeführt.
ShellyTakeover bzw. NousTakeover überschreiben Common; Projects/<Name> hat Vorrang.
Eine Haupt-SSID muss ausdrücklich angegeben sein. Passwort leer für offenes WLAN,
sonst gültige WPA-Länge; Schlüsselpaar muss zusammenpassen.
