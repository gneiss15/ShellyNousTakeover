English version is [here](THIRD_PARTY.md).

# Fremdkomponenten und Lizenzumfang

Version: 1.02
Stand: 2026-10-05

Required Notice: Copyright 2026 Günter Neiß

Die eigene Projektlizenz gilt nur für eigene Quellen. Sie ersetzt keine Lizenz
oder Rechtehinweise einer Fremdkomponente. Fremdkomponenten können Nutzungen
zulassen, die die eigene Projektlizenz nicht zulässt.

## Build-Abhängigkeiten

ESP-IDF v5.5.1 wird aus dem in `Toolchain.lock.json` festgelegten offiziellen
Espressif-Repository geladen. SDK, Submodule und Compiler werden außerhalb des
öffentlichen Quellbestands gehalten. ESP-IDF verwendet überwiegend Apache-2.0;
Subkomponenten besitzen eigene Lizenzdateien. Insbesondere verwendet das Projekt
Mbed TLS (Apache-2.0 als angebotene Lizenzalternative) und cJSON (MIT).

- [ESP-IDF-Lizenz](https://github.com/espressif/esp-idf/blob/v5.5.1/LICENSE)
- Die tatsächlich verwendeten Mbed-TLS-/cJSON-Versionen ergeben sich aus den
  festgelegten SDK-Submodulen. Deren Lizenztexte liegen in der installierten SDK
  unter `components/mbedtls/mbedtls/LICENSE` und `components/json/cJSON/LICENSE`.
- Compiler und Laufzeitbibliotheken behalten ihre eigenen Lizenzen und gegebenenfalls
  Laufzeit-Ausnahmen. Die Toolchain wird nicht unter der Projektlizenz neu lizenziert.

Diese Abhängigkeiten werden beim Build verwendet; sie sind keine mitgelieferten
SDK-Quellkopien. Bei separater Veröffentlichung fertiger Firmware müssen zusätzlich
alle Bedingungen der tatsächlich eingebundenen SDK-Komponenten berücksichtigt werden.
Die bisherige Quellenprüfung ist keine pauschale Freigabe einer Binary-Veröffentlichung.

## Herstellerdaten

Shelly- und Tasmota-Firmware werden nicht als eigene Projektsoftware lizenziert.
Im Quellbestand liegen Identitäts-/Geometriedaten, keine Hersteller-Firmwarepakete
oder privaten Gerätedumps. Offizielle Shelly-Pakete werden nur lokal heruntergeladen
und geprüft; `generated/` bleibt ausgeschlossen.

`tools/certificates/Allterco.crt` enthält ein öffentliches Hersteller-CA-Zertifikat
für den geprüften HTTPS-Download. Herkunft und Zweck stehen in `Allterco.json`.
Es enthält keinen privaten Schlüssel und steht nicht unter der eigenen Projektlizenz.
Besondere Herstellerbedingungen zur Weiterverteilung wurden nicht gefunden. Daraus
wird weder ein Verbot noch eine ausdrückliche Lizenzfreigabe abgeleitet. Das öffentliche
Zertifikat ist kein Secret; Herkunft und begrenzter Vertrauenszweck bleiben dokumentiert.

## Eigene Adapter und Schnittstellen

`common/IdfAdapter/Arduino.h` ist ein schmaler eigener IDF-Adapter und kein
mitgelieferter Arduino-Core. Die Takeovers und Rescue werden ohne Arduino-CLI gebaut.
Tasmota/Shelly-Dokumentation beschreibt die verwendeten Geräteschnittstellen;
die Herstellerprogramme werden nicht als eigene Quellen übernommen.

Der öffentliche Repository-Inhalt muss ausschließlich Quellen, Dokumentation und
nicht private Vorlagen enthalten. Generierte Firmware, WLAN-Header, Schlüssel,
Werkzeuginstallationen und lokale Gerätekonfigurationen gehören nicht hinein.
