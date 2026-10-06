Deutsche Version [hier](README.de.md).

# ShellyTakeover

Version: 1.04

`App/` contains the automatic Takeover, `Bootloader/` the final dual bootloader, and `Rescue/` the standalone Rescue. `Migration/` and `LoaderWriter/` contain the bounded writers and host fault injection.

Build locally from ShellyNousTakeover after setting the private/IDF paths:

```bash
bash tools/BuildTakeover.sh shelly
python3 tools/ValidateTakeoverPackage.py
```

This builds Loader, Rescue, and App and creates `generated/ShellyTakeover/App/PlugMG3-ShellyTakeover.zip`. These commands do not upload anything.

## Package contents and installation

The ZIP is an OTA package for the original Shelly firmware. It contains:

- `manifest.json`: model/platform, package version, and app/filesystem sizes and checksums.
- `ShellyTakeover.bin`: the Takeover app, with the new bootloader, Rescue, and old/new partition tables embedded as payloads.
- `fs.img`: a blank filesystem image filled with `0xFF`, required by this package format.

The ZIP contains no separate bootloader or partition-table OTA part. Stock installs the app/filesystem package; the running Takeover then performs the checked migration writes itself.

Use the ZIP through the PC script; keep it at the generated path above. Do not unpack or upload its individual files. With the prerequisites, environment variables, and `SHELLY_IP` set as described in the [main README](../README.md#pc-precheck-and-takeover), run these commands from the repository root:

```bash
# Read-only device precheck:
python3 tools/ShellyTakeover.py
```

Before the next command, ensure stable power and disconnect attached loads. This command changes the device:

```bash
python3 tools/ShellyTakeover.py --execute
```

The script validates the ZIP, serves it temporarily from the PC over HTTP, and requests `Shelly.Update` once. The Shelly downloads the package; the script waits for and verifies the resulting Rescue status. Keep the PC/script running until completion. If the precheck reports a required stock update, follow the [stock-update instructions](../README.md#pc-precheck-and-takeover) first.

After starting AP+STA/web, the app waits for a LAN IP and then begins its guards and takeover automatically. Do not use the package on unverified hardware. Development status: [../TODO.md](../TODO.md).
