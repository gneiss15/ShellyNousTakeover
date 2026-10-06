English version is [here](README.md).

# ShellyNousTakeover

Version: 1.15

ShellyNousTakeover überführt einen unterstützten Shelly Plug M Gen3 oder NOUS A8T
in ein System mit eigenständiger Rescue App und Hardware-Safe-Boot. Die Takeover enthält
den finalen Bootloader und die Rescue. Nach erfolgreicher Übernahme kann eine
passende Haupt-App über die Rescue installiert werden.

**Entwicklungsstand:** Die Shelly-Übernahme bis zum verifizierten Rescue-Start wurde
am frischen Gerät durchgeführt. Der genaue Testumfang steht in
[HardwareTestResults.json](HardwareTestResults.json), der Arbeitsstand in [TODO.de.md](TODO.de.md).

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

Die [Mini-Examples für Shelly und NOUS](Examples/README.de.md) zeigen eine baubare
Main-App mit eigenem Webstatus, sicher ausgeschaltetem Relais und Rückwechsel zu
Rescue. Sie verwenden dieselbe Toolchain, private Konfiguration und Signierung.
Separate Repositories für **TmrSwShelly** und **TmrSwA8T** als vollständige Beispiele
sind geplant, aber noch nicht veröffentlicht. Links werden nach deren Erstellung ergänzt.

## DeviceType

Der DeviceType beschreibt die Upload-Kompatibilität, unabhängig von Gerätename und
Takeover-Projektname. Standard: Shelly `TmrSwShellyC3V1`, NOUS `TakeoverNousA8TV1`.
Ein anderer Typ wird vor dem Build und dem PC-Übernahmeaufruf ausdrücklich gesetzt:

```bash
export TAKEOVER_DEVICE_TYPE='TmrSwShellyC3V1'
```

Der Wert muss aus höchstens 31 ASCII-Buchstaben/Ziffern bestehen und mit einem
Buchstaben beginnen. Rescue-Build, signierte Artefakte, späterer Main-Build und
PC-Abschlussprüfung müssen denselben Typ verwenden. Eine Environment-Änderung
ändert keine bereits installierte Rescue. Das bisher verwendete
`TakeoverShellyC3V1` ist ein anderer Typ und erfordert eine gezielte Umstellung.

## Hardware-Safe-Boot und Rescue

Der Bootloader startet die Rescue App, wenn der Gerätetaster beim Einschalten bzw.
Reset mindestens eine Sekunde gehalten wird. Zur sicheren Bedienung den Taster
mindestens zwei Sekunden halten. Taster: Shelly GPIO7, NOUS A8T GPIO4, jeweils LOW
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
Stock PlugMG3 2.0.0 / 20260710-101147/2.0.0-g87fbfa4 oder
2.0.1 / 20260923-075548/2.0.1-ge1a198b in app_0. Beide exakten Builds werden
direkt akzeptiert; bei 2.0.0 ist kein vorheriges Stock-Update erforderlich.
NOUS-Ausgangspunkt: A8T mit der passenden Tasmota-Partitionstabelle gemäß
[AppRequirements.md](AppRequirements.de.md).

Der PC darf per Ethernet verbunden sein. Beim Shelly muss auch das Gerät den
lokalen OTA-HTTP-Server des PCs erreichen können. Takeover und Rescue verwenden DHCP;
die Routerreservierung hält ihre Adresse gleich.

## Toolchain prüfen oder einrichten

Die SDK- und Compilerstände sind in `Toolchain.lock.json` festgelegt. Zuerst
`TAKEOVER_IDF_PATH` und `TAKEOVER_IDF_TOOLS_PATH` auf die gewünschten externen
Verzeichnisse setzen (siehe unten). Die reine Prüfung benötigt weder private
Konfiguration noch eine Geräteadresse:

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
# Optionaler DeviceType für Shelly; für NOUS siehe unten.
export TAKEOVER_DEVICE_TYPE="TmrSwShellyC3V1"
export SHELLY_IP="192.168.1.50"
# Für NOUS statt SHELLY_IP:
export NOUS_IP="192.168.1.51"
```

TAKEOVER_PRIVATE_DIR enthält Secrets.local.json sowie private.key/public.key.

`TAKEOVER_DEVICE_TYPE` ist optional und gilt für den jeweiligen Build und
PC-Übernahmeaufruf. Ohne gesetzte Variable wird der Typ aus `<Ziel>/DeviceType.txt`
verwendet: Shelly `TmrSwShellyC3V1`, NOUS `TakeoverNousA8TV1`.
Für NOUS den obigen Shelly-Wert vor dessen Build/Aufruf ersetzen:

```bash
export TAKEOVER_DEVICE_TYPE="TakeoverNousA8TV1"
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
# Für NOUS stattdessen:
bash tools/BuildTakeover.sh nous
```

Lesende Vorprüfung am Gerät, ohne Neustart oder Upload:

```bash
python3 tools/ShellyTakeover.py
# Für NOUS:
python3 tools/NousTakeover.py
```

Der Shelly-Check verlangt das oben genannte Modell und die unterstützte
Sicherheitseinstellung. Für die Takeover muss Stock in Slot 0 laufen. Der bekannte
Factory-Build darf vor seinem vorgeschalteten Stock-Update auch in Slot 1 laufen;
nach dem Update wird Slot 0 erneut zwingend geprüft. Beim bekannten Factory-Build `1.8.99-plugmg3prod0` /
`20251209-070625/geeb7eab` bietet er das geprüfte Update auf den exakten Stock-Build
2.0.1 an. Ohne Schreiboption führt er weder Download noch Update aus. Unbekannte
Zwischenstände, andere Builds und Downgrades werden abgewiesen.
Der NOUS-Check verlangt die bekannte Tasmota-Version samt Build aus
[NousTakeover/README.md](NousTakeover/README.de.md), 4 MiB Flash, aktives A8T-GPIO-Template,
LAN-Adresse und den SafeBoot-/Datei-Uploadweg. Original-Bootloader und Partitionstabelle
prüft anschließend die Takeover direkt am Gerät.

Der folgende Aufruf verändert das Gerät und startet die Übernahme. Erst verwenden,
wenn der Geräteeinsatz für den gewünschten Stand geprüft ist; aktuell gilt der
Entwicklungsstand oben. Zuvor eine stabile Stromversorgung sicherstellen und
angeschlossene Verbraucher trennen:

```bash
python3 tools/ShellyTakeover.py --execute
# Für NOUS stattdessen:
python3 tools/NousTakeover.py --execute
```

Falls das bekannte Factory-Update benötigt wird, stattdessen nach denselben
Voraussetzungen und derselben Gerätefreigabe verwenden:

```bash
python3 tools/ShellyTakeover.py --execute --update-stock
```

Dieser Aufruf prüft zuerst die gebaute Takeover, beschafft und prüft das festgelegte
offizielle Stock-Paket, aktualisiert einmalig und bestätigt dieselbe Geräte-MAC sowie
die exakte Zielversion samt Build. Anschließend muss das Gerät 120 Sekunden lang
in app_0 erreichbar bleiben und eine fortschreitende Laufzeit melden. Neustart,
fehlende Laufzeit oder fehlgeschlagene Abfrage setzen die Beobachtung zurück; nach
420 Sekunden wird abgebrochen. Dies ist eine Stabilitätsprüfung, kein ausgelesener
Hersteller-Commit-Status. Danach werden Slot/Security und die übrigen
Takeover-Voraussetzungen erneut geprüft, bevor der Takeover-Upload startet. Ein
fehlgeschlagenes oder unbestätigtes Stock-Update verhindert die Takeover.

Das offizielle Stock-Paket kann vorab ohne Geräteanfrage vorbereitet werden:

```bash
python3 tools/StockFirmware.py
```

Es liegt danach im ignorierten `generated/StockFirmware/`. Der Downloader verwendet
die öffentliche Allterco-CA unter `tools/certificates/Allterco.crt`, extrahiert aus
`shelly_cloud.pem` eines bestätigten Originalgeräte-Dumps. Herkunft und Identität
sind in `Allterco.json` dokumentiert. Die CA gilt nur für diesen Downloadpfad;
der System-/Browser-Zertifikatsspeicher wird nicht geändert. HTTPS-Zertifikate bleiben
geprüft; es gibt keinen HTTP-/TLS-Unsicherheitsfallback. Bei nicht prüfbarer
Zertifikatskette wird der Download abgebrochen. Alternativ ein bereits vorhandenes
offizielles Zielpaket angeben; auch dieses wird vollständig validiert:

```bash
python3 tools/ShellyTakeover.py --execute --update-stock --stock-package /path/to/PlugMG3-2.0.1.zip
```

Shelly: Das Skript stellt ausschließlich das gebaute OTA-Paket an einem lokalen
HTTP-Port bereit und sendet einmal Shelly.Update. Die passende LAN-Adresse des PCs
wird automatisch gewählt; bei mehreren Netzen kann TAKEOVER_HTTP_HOST die erreichbare
IPv4-Adresse festlegen. Die Firewall muss diesen vom Skript gewählten Port erlauben.
NOUS: Das Skript wechselt zuerst nach SafeBoot, bestätigt diesen Zustand und lädt
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

## Struktur

- ShellyTakeover/: Shelly-Takeover, Bootloader, Rescue und Partitionstabellen.
- NousTakeover/: NOUS-Takeover, Bootloader und Rescue.
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
# Für NOUS:
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
