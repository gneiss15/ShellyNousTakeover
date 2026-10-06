English version is [here](README.md).

# ShellyTakeover

Version: 1.03

App/ enthält die automatische Takeover, Bootloader/ den finalen Dual-Bootloader,
Rescue/ die eigenständige Rescue. Migration/ und LoaderWriter/ enthalten die
begrenzten Writer und Host-Fehlerinjektion.

Lokaler Build aus ShellyNousTakeover nach Setzen der privaten/IDF-Pfade:

```bash
bash tools/BuildTakeover.sh shelly
python3 tools/ValidateTakeoverPackage.py
```

Das baut Loader, Rescue und App und erzeugt generated/ShellyTakeover/App/
PlugMG3-ShellyTakeover.zip. Kein Upload durch diese Kommandos.

Die App wartet nach AP+STA/Webstart auf eine LAN-IP und beginnt danach selbständig
mit ihren Guards und der Übernahme. Das Paket deshalb noch nicht für einen
unverifizierten Hardwareeinsatz verwenden. Entwicklungsstand: [TODO](../TODO.de.md).
