<!-- tools/README.md, Version: 1.00 -->
# Tools

[Deutsch](README.DE.md) · [Project instructions](../README.md)

Run commands from the repository root. Prerequisites and environment variables are described in the project instructions. Build scripts do not upload to devices; writes belong to explicitly started PC takeover procedures.

| Tool | Purpose |
| --- | --- |
| [CheckEnvironment.sh](CheckEnvironment.sh) | Checks the build environment and required external configuration. |
| [SetupToolchain.sh](SetupToolchain.sh) | Checks or installs the tools pinned in Toolchain.lock.json. |
| [VerifyToolchain.py](VerifyToolchain.py) | Checks SDK commit, submodules and compilers against the lock file. |
| [BuildBootloader.sh](BuildBootloader.sh) | Builds the final bootloader for shelly or nous. |
| [BuildRescue.sh](BuildRescue.sh) | Builds and signs the standalone Rescue. |
| [BuildTakeover.sh](BuildTakeover.sh) | Builds the Takeover app with embedded, checked payloads. |
| [BuildExample.sh](BuildExample.sh) | Builds the MiniMain example for the selected device family. |
| [ShellyTakeover.py](ShellyTakeover.py) | Shelly PC flow: preflight, optional stock update, one-time upload and Rescue verification. |
| [NousTakeover.py](NousTakeover.py) | NOUS PC flow: preflight, one-time SafeBoot upload and Rescue verification. |
| [StockFirmware.py](StockFirmware.py) | Helpers for validated manufacturer packages and stock updates. |
| [PackageShelly.py](PackageShelly.py) | Creates the Shelly OTA package in the supported manufacturer format. |
| [ValidateTakeoverPackage.py](ValidateTakeoverPackage.py) | Validates the Shelly Takeover package and embedded payloads. |
| [ValidateNousTakeover.py](ValidateNousTakeover.py) | Validates the NOUS SafeBoot upload image and embedded payloads. |
| [PreparePrivate.py](PreparePrivate.py) | Validates external credentials/keys and generates private build headers without printing their values. |
| [DeviceTypeArtifacts.py](DeviceTypeArtifacts.py) | Generates DeviceType metadata, update artifacts and the public-key header. |
| [BuildFiles.py](BuildFiles.py) | Writes generated build inputs only when content changes, preserving incremental builds. |
| [VerifyBuild.py](VerifyBuild.py) | Checks built images, chip/SDK geometry and signed Rescue payloads. |

The remaining `Verify*.py` scripts are host checks for device preflight, migration flow, Rescue guards and build helpers. Simulated-flash tests do not replace device tests. Additional low-level checks are located beside the relevant Bootloader, LoaderWriter and Migration components.

[stock/](stock/README.md) describes manufacturer package checks and file transfer. `certificates/` contains certificates used to verify manufacturer firmware. Generated files and test reports remain local; private configuration and keys are outside the repository.
