Deutsche Version [hier](README.de.md).

# Mini Examples: Shelly and NOUS

Version: 1.01

`MiniMain/` is a small ESP-IDF app built separately for both target devices. It demonstrates the Rescue contract without depending on TmrSw or Arduino:

- Check chip, flash size, security, actual SDK partition table, and Main/Rescue/LittleFS/NVS/OTA geometry before hardware and network initialization.
- Initialize the relay safely OFF and keep it OFF.
- Use WLAN from the external private configuration, without WLAN/PHY NVS persistence.
- Provide a built-in web interface, `GET /status`, and `POST /Rescue` to reboot into Rescue.
- Provide Main as a correctly typed, RSA-signed artifact for the installed Rescue.

The app neither needs nor modifies LittleFS. It does not measure power, contain a timer, or have its own firmware updater. Updates go through Rescue. Hardware Safe Boot is a function of the already installed bootloader.

## Prerequisites and build

First set up environment variables, toolchain, and private files as described in the [project README](../README.md). DeviceType must match the installed Rescue; the key pair must match its verification key. WLAN fields come from the same ShellyTakeover/NousTakeover section as for Rescue. Then, from the project directory:

```bash
# Shelly default is TmrSwShellyC3V1.
export TAKEOVER_DEVICE_TYPE='TmrSwShellyC3V1'
bash tools/BuildExample.sh shelly

# The new NOUS Takeover Rescue defaults to TakeoverNousA8TV1.
export TAKEOVER_DEVICE_TYPE='TakeoverNousA8TV1'
bash tools/BuildExample.sh nous
```

Output: `generated/ShellyTakeover/MiniMain/MiniMain.signed` or `generated/NousTakeover/MiniMain/MiniMain.signed`. The build checks the image, chip, descriptor, SDK settings, and signature. It performs no device action. The current MiniMain examples have been built and signed for both chips. They have not been uploaded to hardware or tested on hardware. This check does not replace a hardware test.

## Install into a running Rescue

Installation replaces the existing Main app. First check the correct device and Rescue DeviceType on the Rescue status page. Then install only the matching `MiniMain.signed` through Rescue’s **Firmware** upload. No filesystem upload is needed for this example. Start Main after successful upload/readback verification. `/` shows the example and `/status` its state. The **Start Rescue** button selects the Rescue partition as the next boot target and reboots. The app does not erase NVS, the bootloader, or the partition table.

Do not use `idf.py flash`: a generic factory-app upload can hit Rescue. Raw `MiniMain.bin` is not a signed network update.

## Complete application examples

Separate repositories for **TmrSwShelly** and **TmrSwA8T** are planned. They are intended to demonstrate timers, heating profiles, configuration, LittleFS, and other device functions. They have not been published yet, so repository links are not available here. The Mini Examples are independently buildable and show the minimal Main integration.
