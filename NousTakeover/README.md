Deutsche Version [hier](README.de.md).

# NousTakeover

Version: 1.09

The bootloader, Rescue, and automatic Takeover app are standalone ESP-IDF projects. Environment and private configuration: [../README.md](../README.md). After setting them up, build from the repository root (`ShellyNousTakeover/`):

```bash
bash tools/BuildTakeover.sh nous
```

Output is `generated/NousTakeover/App/Takeover.bin` for the Tasmota SafeBoot manufacturer upload. This input format is the raw ESP app image; later Rescue uploads require signed artifacts. The build script does not upload to a device. Installation is described below; open tests: [TODO](../TODO.md).

## Artifact contents and installation

`generated/NousTakeover/App/Takeover.bin` is relative to the repository root. It is a raw ESP app image containing the automatic Takeover, new bootloader, Rescue, and expected partition-table data as embedded payloads. NOUS uses this single `.bin` file rather than a ZIP package. The existing partition table is checked and preserved.

Keep the image at this generated path; use the PC script to install it through Tasmota SafeBoot. With the prerequisites and environment variables, including `NOUS_IP`, set according to the [main README](../README.md#pc-precheck-and-takeover), run from the repository root:

```bash
# Read-only device precheck; no restart or upload:
python3 tools/NousTakeover.py
```

If Tasmota requires authentication, set `NOUS_PASSWORD` and optionally `NOUS_USER` (default `admin`) before the PC commands. These are Tasmota web credentials, separate from the compiled WLAN settings.

Before the next command, ensure stable power and disconnect attached loads. This command changes the device:

```bash
python3 tools/NousTakeover.py --execute
```

The script validates the image, rechecks the device, switches it to Tasmota SafeBoot, and confirms its identity and upload route. It then uploads `Takeover.bin` once. Takeover starts automatically and performs its guards and migration; the script waits for the new Rescue and checks device MAC, DeviceType, geometry, boot selection, and that Main is not yet installed. Keep the PC/script running until completion. An uncertain upload is not repeated automatically. Later Main/filesystem uploads use signed artifacts through Rescue, as described in [AppRequirements](../AppRequirements.md).

The bounded bootloader writer in `LoaderWriter/` saves the actual original bytes in RAM and writes only `0x1000` through `0x7FFF`. It requires prior identity approval and verified Rescue. The partition table and OTA partition are compared before and after writing. On write errors, it restores and verifies the original bootloader while these invariants remain unchanged. Failed rollback, write-protection restoration, or invariant checks block reboot. The writer does not replace device/firmware/bootloader provenance checks.

Host check without a device:

```bash
python3 NousTakeover/LoaderWriter/VerifyLoaderWriter.py
```

The shared state machine supports the Nous order Rescue → bootloader → Rescue boot selection without writing a partition table. The app starts AP+STA and web diagnostics before the guards and begins automatically after obtaining a LAN IP. Diagnostics and status remain available on errors; there is no forced reboot.

The app checks real chip/flash/security/slot data, original bootloader identity, partition table, existing SafeBoot image, boot selection, and payloads. Rescue is checked in full, including the erased remainder. Preserved areas (flash pre-area, partition table/NVS, running Main, and filesystem) are independently compared before and after the flow. The bootloader and OTA partition are saved for bounded error rollback. The old SafeBoot app is not saved: rollback means a verified boot path to the running Takeover, not restoration of the original Tasmota or its old SafeBoot app.

The PC precheck and one-time SafeBoot upload are implemented in `tools/NousTakeover.py`; see the project README for operation. Final verification requires the new Rescue status, including an unchanged device MAC. I successfully converted four NOUS A8T devices with the earlier migration procedure. The latest standalone implementation in this repository has been built and host-tested; only this new overall flow still lacks a test on an unmodified device, because all four available NOUS devices are already converted. Those earlier successes are practical experience with the predecessor, not a hardware test of this latest implementation.

## Supported input baseline

Tasmota with an actual SafeBoot layout is required. Tasmota introduced SafeBoot in version 12; the version number alone does not approve a layout. Other SafeBoot partition layouts and custom builds exist: [Tasmota SafeBoot documentation](https://tasmota.github.io/docs/Safeboot/). For NOUS A8T, only the 4 MiB geometry in `partitions.csv` is supported.

The historically used input baseline was `14.3.0.1 (tasmota32)`, build `2024-11-05T10:09:04`. `OriginalFirmware.json` contains the verified original bootloader and partition-table identity from the original dump at that time, not manufacturer binaries or configuration. The version/build value comes from the archived console log; the corresponding fields in the ESP app descriptor in the dump are empty. The bootloader was verified as an ESP32-DIO image with checksum, appended digest, and erased remainder; the partition table and MD5 exactly match `partitions.csv`.

This identifies one specific input baseline. Other SafeBoot versions require evidence of a compatible bootloader/layout identity. A normal Tasmota app update does not prove the bootloader changed. Takeover must inspect the existing loader and layout directly; before OTA, the PC checks the still-running Tasmota and SafeBoot upload path. Historical HTML files and the original dump are not build prerequisites.
