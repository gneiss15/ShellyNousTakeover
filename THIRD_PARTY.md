Deutsche Version [hier](THIRD_PARTY.de.md).

# Third-Party Components and License Scope

Version: 1.02
Stand: 2026-10-05

Required Notice: Copyright 2026 Günter Neiß

The project’s own license applies only to its own sources. It does not replace a third-party component’s license or notices. Third-party components may permit uses that the project’s own license does not.

## Build dependencies

ESP-IDF v5.5.1 is fetched from the official Espressif repository specified in `Toolchain.lock.json`. The SDK, submodules, and compiler are kept outside the public source tree. ESP-IDF is predominantly Apache-2.0; subcomponents have their own license files. In particular, the project uses Mbed TLS (Apache-2.0 as an offered license alternative) and cJSON (MIT).

- [ESP-IDF license](https://github.com/espressif/esp-idf/blob/v5.5.1/LICENSE)
- The actual Mbed TLS/cJSON versions used are determined by the pinned SDK submodules. Their license texts are in the installed SDK at `components/mbedtls/mbedtls/LICENSE` and `components/json/cJSON/LICENSE`.
- Compilers and runtime libraries retain their own licenses and any runtime exceptions. The toolchain is not relicensed under the project license.

These dependencies are used during builds; they are not bundled SDK source copies. A separate release of finished firmware must also comply with all terms of the SDK components actually included. The source review performed so far is not blanket approval to publish binaries.

## Manufacturer data

Shelly and Tasmota firmware are not licensed as project software. The source tree contains identity/geometry data, not manufacturer firmware packages or private device dumps. Official Shelly packages are downloaded and checked locally only; `generated/` remains excluded.

`tools/certificates/Allterco.crt` contains a public manufacturer CA certificate for the verified HTTPS download. Its origin and purpose are documented in `Allterco.json`. It contains no private key and is not covered by the project’s own license. No special manufacturer redistribution terms were found. This establishes neither a prohibition nor an explicit license grant. The public certificate is not a secret; its origin and limited trust purpose remain documented.

## Own adapters and interfaces

`common/IdfAdapter/Arduino.h` is a small adapter of our own for IDF, not a bundled Arduino core. Takeover and Rescue are built without Arduino CLI. Tasmota/Shelly documentation describes the device interfaces used; manufacturer programs are not copied as project sources.

The public repository must contain only sources, documentation, and non-private templates. Generated firmware, WLAN headers, keys, tool installations, and local device configurations do not belong in it.
