Deutsche Version [hier](README.de.md).

# ShellyTakeover

Version: 1.03

`App/` contains the automatic Takeover, `Bootloader/` the final dual bootloader, and `Rescue/` the standalone Rescue. `Migration/` and `LoaderWriter/` contain the bounded writers and host fault injection.

Build locally from ShellyNousTakeover after setting the private/IDF paths:

```bash
bash tools/BuildTakeover.sh shelly
python3 tools/ValidateTakeoverPackage.py
```

This builds Loader, Rescue, and App and creates `generated/ShellyTakeover/App/PlugMG3-ShellyTakeover.zip`. These commands do not upload anything.

After starting AP+STA/web, the app waits for a LAN IP and then begins its guards and takeover automatically. Do not use the package on unverified hardware. Development status: [../TODO.md](../TODO.md).
