English version is [here](PrjRegeln.md).

# ShellyNousTakeover – Projektregeln

Version: 1.05
Stand: 2026-10-05

- Eigenständiges Projekt für Shelly Plug M Gen3 und NOUS A8T Takeover; keine TmrSw-Main.
  Kleine unabhängige Main-Beispiele dürfen den dokumentierten Rescue-Vertrag zeigen.
- Private Konfiguration und Schlüssel ausschließlich über TAKEOVER_PRIVATE_DIR,
  außerhalb dieses Projekts. Keine privaten Vorgabepfade und keine Secrets in Logs.
- Zielgerät ausschließlich über SHELLY_IP bzw. NOUS_IP; keine vorgegebenen Geräteadressen.
- Beide Geräte einschließlich Rescue werden mit ESP-IDF gebaut. Toolchains über
  TAKEOVER_IDF_PATH und TAKEOVER_IDF_TOOLS_PATH. Keine Arduino-CLI-Abhängigkeit
  und keine festen Mount-Pfade.
- Takeover prüft vor Writes reale Hardware, Sicherheit, Partitionstabelle,
  Bootloader, laufende App und eingebettete Payloads. Netzwerkdiagnose muss vor
  den Migrationsprüfungen erreichbar sein und bei Fehlern erreichbar bleiben.
- PC prüft vor dem Upload das Herstellergerät und den kompatiblen Uploadweg.
  Takeover kann nach ihrem Start die vorherige Hersteller-Firmware nicht allein
  anhand ihrer eigenen App-Version feststellen. Herkunftsprüfung nicht vortäuschen.
- Automatischer Ablauf nach erfolgreichen Guards; kein Schreibzugriff bei unbekanntem
  oder unklarem Zustand. Alle Writes vollständig rücklesen und prüfen.
- Fehler-Rücknahme nur bei bestätigter Baseline und eindeutigem Schreibzustand.
  Keine erfolgreiche Rücknahme behaupten, wenn Gerät oder Flashzustand unklar sind.
- Shelly-Dual-Bootloader ist der finale Loader für beide Partitionstabellen.
  Keine zweite Loader-Ersetzung allein zum Entfernen des Stock-Pfads.
- Unterstützte Eingangsgeometrien ausdrücklich festlegen. Kein generisches idf.py flash.
- Verwendung „Partitionstabelle“ statt unspezifischem „Tabelle“ in Bedienung/Dokumentation.
- Build-/Downloadprodukte nur generated/ bzw. .tools/, nicht im Quellbestand.
- Alte Prjs-Bäume sind für die Portierung Referenzen, keine späteren Laufzeit-/Buildabhängigkeiten.

- README beschreibt Nutzerbedienung, Voraussetzungen und Safe Boot. Öffentliche offene
  Arbeiten und Freigabeprüfungen gehören in TODO.md/TODO.de.md. ToDo.txt ist lokale
  Arbeitschronik und wird aus Git ausgeschlossen; öffentliche Dokumente verlinken sie nicht.
