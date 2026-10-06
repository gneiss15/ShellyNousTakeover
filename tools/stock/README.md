# Shelly-Stock-Firmware vorbereiten

Version: 1.01

Die geprüfte Paketidentität steht in ../../ShellyTakeover/StockFirmware.layout.json,
die erlaubten Eingangs-Builds in ../../ShellyTakeover/StockUpdatePolicy.json.
ValidateFirmwareLayout.py prüft Paket, Komponenten und Partitionierung.
StockFirmware.py und ShellyTakeover.py sind der eigenständige PC-Ablauf; keine
externen Projektquellen oder Capture-Dateien werden zur Laufzeit benötigt.

Der Startablauf:

1. SHELLY_IP lesen und unterstütztes Herstellergerät/Firmware feststellen.
2. Exakte Zielversion samt Build feststellen, nicht „neueste Version“ verwenden.
3. Bei identischem Ziel direkt fortfahren; bei älterer Version einen geprüften
   Hersteller-Updateweg anbieten. Andere Builds derselben Version separat behandeln.
4. Bei neuerer Version Downgrade nur anbieten, wenn Herstellerweg, Paket und
   Ausgangsversion dafür ausdrücklich geprüft sind. Sonst klar abbrechen.
5. Zielpaket über authentifiziertes HTTPS beschaffen und gegen festgelegte
   Paketidentität/Manifest/Partitionierung prüfen; nicht auf veränderliche
   Stable-Descriptorangaben als alleinige Vertrauensquelle verlassen.
6. Update nur nach Nutzerwahl, anschließend Version/Build/Geräteidentität erneut
   prüfen. Erst dann Takeover bauen/hochladen bzw. den Upload freigeben.

Update/Downgrade kann bereits herstellerseitig Bootloader oder Partitionstabelle
ändern. Der erfolgreiche Download beweist daher keinen sicheren Geräteweg.
Die Versionsvorbereitung ist jetzt in `../StockFirmware.py` und
`../ShellyTakeover.py` implementiert. Bedienung: Projekt-README.
`StockUpdatePolicy.json` erlaubt ausschließlich die beobachtete Factory-Version
`1.8.99-plugmg3prod0 / 20251209-070625/geeb7eab` als Eingang zum gepinnten Ziel.
Unbekannte Zwischenstände und Downgrades bleiben gesperrt.

Kein veränderlicher Stable-Descriptor und keine alten Capture-Dateien als neue
Buildvoraussetzung. Das Zielpaket wird per zertifikatsgeprüftem HTTPS geladen,
gegen die festgelegte vollständige Paketidentität und danach gegen Manifest,
Komponenten und Partitionierung geprüft. Erst dann wird es atomar in den ignorierten
Cache übernommen; bei Fehlern werden temporäre Dateien entfernt. Vorhandene Pakete
werden bei jeder Nutzung geprüft. Kein unsicherer TLS-Fallback.

Der reale HTTPS-Test auf diesem PC scheiterte an einer nicht prüfbaren Issuer-Kette.
Das schon vorhandene offizielle Paket wurde separat vollständig geprüft und als
lokaler generierter Cache wiederverwendet. Dies ist kein bestätigter neuer Download
und kein neuer Gerätetest. Ein Paketpfad kann alternativ explizit angegeben werden.
