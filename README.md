Deutsche Version [hier](README.de.md).

# ShellyNousTakeover

Version: 1.15

ShellyNousTakeover converts a supported Shelly Plug M Gen3 or NOUS A8T to a system with a standalone Rescue app and hardware Safe Boot. Takeover contains the final bootloader and Rescue. After successful takeover, a compatible Main app can be installed through Rescue.

**Development status:** Shelly takeover through verified Rescue startup has been performed on a fresh device. The exact test scope is in [HardwareTestResults.json](HardwareTestResults.json); current work is tracked in [TODO.md](TODO.md).

## License

Required Notice: Copyright 2026 Günter Neiß

The project’s own components are under the [PolyForm Noncommercial License 1.0.0](LICENSE.md). Noncommercial use is permitted under its terms; commercial use outside the permitted purposes requires a separate license from Günter Neiß. The license has specific provisions for nonprofit and public institutions.

This license applies only to project-owned components. Third-party components remain subject to their own licenses; their notices and terms remain in force. See [THIRD_PARTY.md](THIRD_PARTY.md). No warranty; the hardware and power-loss risks described below also apply.

## Example apps

The [Mini Examples for Shelly and NOUS](Examples/README.md) show a buildable Main app with its own web status, safely switched-off relay, and return to Rescue. They use the same toolchain, private configuration, and signing setup. Separate repositories for complete **TmrSwShelly** and **TmrSwA8T** examples are planned but not yet published. Links will be added when they are created.

## DeviceType

DeviceType describes upload compatibility independently of device name and Takeover project name. Defaults: Shelly `TmrSwShellyC3V1`, NOUS `TakeoverNousA8TV1`. Explicitly set a different type before the build and PC takeover command:

```bash
export TAKEOVER_DEVICE_TYPE='TmrSwShellyC3V1'
```

The value must contain at most 31 ASCII letters/digits and begin with a letter. Rescue build, signed artifacts, later Main build, and PC completion check must use the same type. Changing the environment does not change an already installed Rescue. The previously used `TakeoverShellyC3V1` is a different type and requires a deliberate migration.

## Hardware Safe Boot and Rescue

The bootloader starts the Rescue app if the device button is held for at least one second during power-on or reset. For reliable operation, hold it for at least two seconds. Button pins: Shelly GPIO7, NOUS A8T GPIO4; each is LOW while pressed.

This recovery path works independently of Main and its filesystem. A broken, non-starting, or hung Main app does not need to provide a network service: restart the device while holding the button. It then boots into Rescue; NVS and filesystem are not changed.

Rescue:

- runs in its own app partition with its own WLAN configuration and built-in web interface; it needs no files or web server from Main;
- connects to the compiled-in WLAN and also provides an access point; a Linux PC on the same home network can reach it over LAN;
- accepts separate signed firmware/filesystem uploads, checks target type, signature, and payload, and reads written data back for verification;
- starts Main only after the specified image/activation checks;
- indicates operation with SOS blinking, red on Shelly.

This is an independent recovery path for Main and the filesystem. A damaged bootloader, partition table, or Rescue itself can prevent it. Safe Boot does not remove the risk during takeover.

## Prerequisites

- Linux PC with Bash, Python 3, Git, CMake, Ninja, and OpenSSL.
- ESP-IDF 5.5.1 with its SDK Python environment and Espressif compilers for ESP32-C3 (RISC-V) and/or ESP32 (Xtensa), according to the selected device.
- Supported source device on the home network; reserve a fixed IPv4 address in DHCP.
- Matching WLAN configuration and a private signing key pair outside the project.

Shelly source: Plug M Gen3 / S3PL-30110EU, ESP32-C3 revision 4, 8 MiB, Stock PlugMG3 2.0.0 / 20260710-101147/2.0.0-g87fbfa4 or 2.0.1 / 20260923-075548/2.0.1-ge1a198b in app_0. Both exact builds are accepted directly; no prior stock update is required for 2.0.0. NOUS source: A8T with the matching Tasmota partition table as described in [AppRequirements.md](AppRequirements.md).

The PC may use Ethernet. For Shelly, the device must also be able to reach the PC’s local OTA HTTP server. Takeover and Rescue use DHCP; the router reservation keeps their address stable.

## Check or install the toolchain

SDK and compiler versions are pinned in `Toolchain.lock.json`. First set `TAKEOVER_IDF_PATH` and `TAKEOVER_IDF_TOOLS_PATH` to the desired external directories (see below). Checking requires neither private configuration nor a device address:

```bash
bash tools/SetupToolchain.sh --check
```

If the installation is missing, this explicitly selected command fetches the pinned ESP-IDF and installs tools for both devices:

```bash
bash tools/SetupToolchain.sh --install
```

Installation requires internet access and Espressif’s Linux build prerequisites [as documented](https://docs.espressif.com/projects/esp-idf/en/v5.5.1/esp32/get-started/linux-macos-setup.html), especially Python venv/pip, Flex, Bison, Gperf, and the listed system libraries. The script does not install system packages. Existing SDKs with a different commit, modifications, or missing/different submodules are rejected and not reset. Use a new, nonexistent SDK path if an existing installation differs.

Official tool downloads are checked by the pinned SDK installer and its checksum manifest. Python dependencies are resolved using that SDK’s requirements/constraints; a complete Python package lock is not guaranteed. Installation/activation logs are stored in `generated/`. Build scripts recheck the SDK and relevant compiler version before building.

## External settings

Replace the example paths and device address before running commands:

```bash
export TAKEOVER_PRIVATE_DIR="$HOME/takeover-private"
export TAKEOVER_IDF_PATH="$HOME/tools/esp-idf-v5.5.1"
export TAKEOVER_IDF_TOOLS_PATH="$HOME/tools/espressif"
# Optional Shelly DeviceType; for NOUS see below.
export TAKEOVER_DEVICE_TYPE="TmrSwShellyC3V1"
export SHELLY_IP="192.168.1.50"
# For NOUS instead of SHELLY_IP:
export NOUS_IP="192.168.1.51"
```

TAKEOVER_PRIVATE_DIR contains Secrets.local.json and private.key/public.key.

`TAKEOVER_DEVICE_TYPE` is optional and applies to the selected build and PC takeover
command. If unset, the type is read from `<target>/DeviceType.txt`: Shelly
`TmrSwShellyC3V1`, NOUS `TakeoverNousA8TV1`.
For NOUS, replace the Shelly value above before its build/command:

```bash
export TAKEOVER_DEVICE_TYPE="TakeoverNousA8TV1"
```

Alternatively, run `unset TAKEOVER_DEVICE_TYPE` to use the selected project's default
again. DeviceType must match the intended future Main/Rescue upload format; it is not
a device name. See [DeviceType](#devicetype).


### Create Secrets.local.json

After setting TAKEOVER_PRIVATE_DIR, copy the template there; do not overwrite an existing Secrets.local.json:

```bash
mkdir -p "$TAKEOVER_PRIVATE_DIR"
(umask 077; cp -n Secrets.example.json "$TAKEOVER_PRIVATE_DIR/Secrets.local.json")
chmod 600 "$TAKEOVER_PRIVATE_DIR/Secrets.local.json"
```

Replace the placeholders from [Secrets.example.json](Secrets.example.json) in the external directory before building. The JSON file contains:

| Field | Meaning |
|---|---|
| `WlanSsid` | Main WLAN name, required, at most 31 UTF-8 bytes |
| `WlanPw` | Main WLAN password; empty only for an open WLAN |
| `WlanSsid2` | Optional backup WLAN; empty disables this profile |
| `WlanPw2` | Backup WLAN password; leave empty if there is no backup WLAN |

WPA passwords: 8–63 UTF-8 bytes or a 64-character hexadecimal WPA key. Escape JSON special characters such as quotation marks and backslashes as required. `Common` applies to both devices. `ShellyTakeover` or `NousTakeover` can override individual fields. Precedence, from lower to higher: fields directly in the JSON root → Common → device-specific section → Projects/ShellyTakeover or Projects/NousTakeover. The last two Projects sections are optional; the template does not need them.

Keys do not belong in the JSON file: private.key contains the private RSA key in PEM format, public.key the matching public PEM key. Passphrase-protected private keys are not supported by unattended builds. Store both files alongside Secrets.local.json; keep private.key readable only by its owner. Do not copy a real private file into the project directory or repository.

The private key is used only for signing on the PC; Rescue receives the public verification key. WLAN data is compiled into Takeover and Rescue, not the bootloader. Generated headers and firmware may contain private data and must not be published.

The two IDF paths identify SDK sources and downloaded SDK tools. Both device paths use ESP-IDF.

Check the environment without downloading, building, or contacting a device:

```bash
bash tools/CheckEnvironment.sh shelly
# or:
bash tools/CheckEnvironment.sh nous
```

## PC precheck and takeover

After setting paths and device IP, build the complete Takeover:

```bash
bash tools/BuildTakeover.sh shelly
# For NOUS instead:
bash tools/BuildTakeover.sh nous
```

Read-only device precheck, without reboot or upload:

```bash
python3 tools/ShellyTakeover.py
# For NOUS:
python3 tools/NousTakeover.py
```

The Shelly check requires the model and supported security setting above. Stock must be running in slot 0 for Takeover. The known factory build may run in slot 1 before its prerequisite stock update; slot 0 is checked again as mandatory after the update. For the known factory build `1.8.99-plugmg3prod0` / `20251209-070625/geeb7eab`, it offers a verified update to the exact stock build 2.0.1. Without a write option it performs neither download nor update. Unknown intermediate states, other builds, and downgrades are rejected. The NOUS check requires the known Tasmota version/build from [NousTakeover/README.md](NousTakeover/README.md), 4 MiB flash, active A8T GPIO template, LAN address, and SafeBoot/file upload path. Takeover then checks the original bootloader and partition table directly on the device.

The following command modifies the device and starts takeover. Use it only after reviewing the device deployment for the intended version; the development status above currently applies. First ensure stable power and disconnect attached loads:

```bash
python3 tools/ShellyTakeover.py --execute
# For NOUS instead:
python3 tools/NousTakeover.py --execute
```

If the known factory update is needed, use this command instead under the same prerequisites and device approval:

```bash
python3 tools/ShellyTakeover.py --execute --update-stock
```

This command first checks the built Takeover, obtains and verifies the specified official stock package, performs the one-time update, and confirms the same device MAC and exact target version/build. The device must then remain reachable in app_0 for 120 seconds and report advancing uptime. A reboot, missing uptime, or failed query resets the observation; it aborts after 420 seconds. This is a stability check, not a readout of manufacturer commit status. Slot/security and the remaining takeover prerequisites are checked again before Takeover upload starts. A failed or unconfirmed stock update prevents takeover.

The official stock package can be prepared in advance without contacting a device:

```bash
python3 tools/StockFirmware.py
```

It is stored in ignored `generated/StockFirmware/`. The downloader uses the public Allterco CA at `tools/certificates/Allterco.crt`, extracted from `shelly_cloud.pem` in a confirmed original-device dump. Origin and identity are documented in `Allterco.json`. The CA is used only for this download path; the system/browser certificate store is not changed. HTTPS certificates remain checked; there is no HTTP/TLS-insecure fallback. Download aborts if the certificate chain cannot be verified. Alternatively, supply an existing official target package; it is fully validated too:

```bash
python3 tools/ShellyTakeover.py --execute --update-stock --stock-package /path/to/PlugMG3-2.0.1.zip
```

Shelly: the script serves only the built OTA package on a local HTTP port and sends Shelly.Update once. It automatically selects the suitable PC LAN address; on multiple networks, `TAKEOVER_HTTP_HOST` can set the reachable IPv4 address. The firewall must allow the port selected by the script. NOUS: the script first switches to SafeBoot and confirms that state, then uploads the Takeover file once. It does not upload to normal Main.

Both scripts wait for the new Rescue JSON status and check device MAC, project/DeviceType/version, valid geometry, running/selected Rescue boot target, and that Main is not installed yet. A successful HTTP upload response alone does not count as a successful takeover. A connection loss triggers neither another upload nor a reset; app errors or missing completion confirmation remain errors. Takeover performs rollback within its verified limits.

Optionally set existing web login through SHELLY_USER/SHELLY_PASSWORD or NOUS_USER/NOUS_PASSWORD; the default user is admin. Do not put passwords in project files or command-line arguments. Scripts do not print full device responses or authentication data. Rescue status: read-only GET /status.

## Structure

- ShellyTakeover/: Shelly takeover, bootloader, Rescue, and partition tables.
- NousTakeover/: NOUS takeover, bootloader, and Rescue.
- common/: shared configuration and update components.
- tools/: toolchain setup, build, and manufacturer upload.
- generated/: local build/diagnostic output; do not publish.
- .tools/: locally downloaded toolchains; do not publish.

Flash addresses, partition sizes, and future Main app requirements are in [AppRequirements.md](AppRequirements.md).

## Risks — NO WARRANTY

Takeover modifies the bootloader, partition table, and flash contents. A power loss, interruption, or write error during critical writes can leave a device unable to start or recover over the network. Serial hardware access may then be required; recovery is not guaranteed. Checks and possible rollback do not eliminate this risk. Ensure stable power during takeover and do not operate a connected load.

**NO WARRANTY** of success, error-free operation, or recoverability. Use at your own risk.

## Build Rescue and bootloader

After setting paths and complete private WLAN configuration:

```bash
bash tools/BuildBootloader.sh shelly
bash tools/BuildRescue.sh shelly
# For NOUS:
bash tools/BuildBootloader.sh nous
bash tools/BuildRescue.sh nous
python3 tools/VerifyBuild.py
```

The final check expects builds for both devices. Results are under `generated/<ShellyTakeover|NousTakeover>/<Bootloader|Rescue>/`. No build command uploads anything to the device. SDK compiler: Espressif GCC esp-14.2.0_20241119.

In Secrets.local.json, WlanSsid/WlanPw and optional WlanSsid2/WlanPw2 are merged from root fields, Common, and device-specific sections. ShellyTakeover or NousTakeover override Common; Projects/<Name> takes precedence. A main SSID must be explicitly provided. Leave the password empty for an open WLAN; otherwise use a valid WPA length. The key pair must match.
