English version is [here](TODO.md).

# Offene Arbeiten

Version: 1.01

- [ ] Neue NOUS-Übernahme vollständig an einem noch nicht umgestellten Gerät testen,
  einschließlich Rescue-Uploads und Taster-Safe-Boot. Historische Umstellungen
  testen diesen Code nicht.
- [ ] Beide MiniMain-Beispiele an Hardware prüfen: Start, dauerhaft ausgeschaltetes
  Relais, Webstatus und Rückwechsel zu Rescue. Builds und Signaturen sind geprüft.
- [ ] Kontinuierliche Stock-Bereitschaft nach einem echten Shelly-Stock-Update prüfen.
  Die ergänzte Wartephase ist hostgeprüft, nicht in einer neuen Migration getestet.
- [ ] Hardwareprüfung ungültiger Main-Images und unbrauchbarer Dateisysteme ergänzen;
  Host-Fehlerinjektion und tatsächliche Gerätetests getrennt ausweisen.
- [ ] Separate TmrSwShelly- und TmrSwA8T-Beispiel-Repositories erstellen und verlinken.
- [x] Vor Veröffentlichung den endgültigen Repository-Export auf private Daten,
  generierte Artefakte und erforderliche Fremdkomponenten-Hinweise prüfen.

Aktueller Prüfumfang:
[Hardware](HardwareTestResults.json), [Hostprüfungen](HostTestResults.json),
[Builds](BuildResults.json), [Beispiel-Builds](ExampleBuildResults.json) und
[Quellenprüfung zur Veröffentlichung](PublicationCheckResults.json).
