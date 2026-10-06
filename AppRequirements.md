Deutsche Version [hier](AppRequirements.de.md).

# Requirements for a Future Main App

Version: 1.03

The geometries below match the standalone bootloader/rescue builds. The new runtime still needs device testing. Addresses are absolute flash addresses; sizes are bytes. Do not flash a partition table or bootloader from a generic board profile.

## Shelly Plug M Gen3: ESP32-C3, 8 MiB

| Use | Offset | Size |
|---|---:|---:|
| Final dual bootloader, bounded write area | 0x000000 | 0x006000 |
| Partition table, sector | 0x010000 | 0x001000 |
| Old boot state, read-only | 0x011000 | 0x002000 |
| Old NVS, read-only | 0x014000 | 0x00C000 |
| Preserved stock app, read-only | 0x020000 | 0x2A0000 |
| LittleFS (`spiffs`) | 0x2C0000 | 0x0E0000 |
| Main (`app0`, ota_0) | 0x3A0000 | 0x2A0000 |
| Rescue (`safeboot`, factory) | 0x640000 | 0x180000 |
| NVS | 0x7C0000 | 0x020000 |
| OTA boot selection | 0x7E0000 | 0x002000 |
| Previous migration checkpoints, reserved | 0x7E2000 | 0x008000 |
| Factory/calibration data (`shelly`), read-only | 0x7F0000 | 0x010000 |

Unlisted gaps are not approved app/filesystem areas. In particular, do not erase factory data or replace it with data from another device. The **linked SDK runtime** must read the partition table at 0x10000; a matching CSV alone is not sufficient. Prebuilt SDKs using 0x8000 are incompatible.

## NOUS A8T: ESP32, 4 MiB

| Use | Offset | Size |
|---|---:|---:|
| ROM pre-area, not part of loader write | 0x000000 | 0x001000 |
| Final bootloader, bounded write area | 0x001000 | 0x007000 |
| Partition table, sector | 0x008000 | 0x001000 |
| NVS | 0x009000 | 0x005000 |
| OTA boot selection | 0x00E000 | 0x002000 |
| Rescue (`safeboot`, factory) | 0x010000 | 0x0D0000 |
| Main (`app0`, ota_0) | 0x0E0000 | 0x2D0000 |
| LittleFS (`spiffs`) | 0x3B0000 | 0x050000 |

The SDK runtime uses partition-table offset 0x8000. Preserve device-specific calibration in NVS; do not erase all NVS during Main/FS updates.

## Upload and app contract of the existing Rescue

- Native ESP app for the respective chip; the entire app binary must fit in the Main partition. Main updates do not overwrite Rescue.
- No A/B app OTA: Main requests Rescue; Rescue writes Main and LittleFS. Normal Arduino OTA to the “other” app does not fit this geometry.
- Upload firmware and LittleFS as separate, correctly typed, RSA-signed artifacts. The signing key must match the public key compiled into Rescue; an arbitrary raw `.bin` is not accepted as a normal update.
- New DeviceTypes: Shelly defaults to `TmrSwShellyC3V1`, Nous to `TakeoverNousA8TV1` (explicitly adjustable through `TAKEOVER_DEVICE_TYPE`). The manifest, artifact type, and DeviceType must match the target.
- The new Rescue does not require a particular Main project name. It checks the ESP image and rejects known transition/takeover project names. Signed artifacts must still match the new DeviceType and verification key.
- `spiffs` is the partition name/subtype; LittleFS is currently used there. A SPIFFS image is therefore not automatically compatible.
- The app checks geometry before NVS/flash/hardware access. Do not copy button/relay/LED assignments from other board profiles. Main starts with the relay safely OFF.

After takeover, treat Main as not installed. The future app must operate independently of Takeover. The new Rescue uses the stated DeviceTypes; older signed artifacts with different DeviceTypes are incompatible. A successful build does not establish that the new Rescue has been tested on hardware.
