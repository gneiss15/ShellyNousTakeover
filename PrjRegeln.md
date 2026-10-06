Deutsche Version [hier](PrjRegeln.de.md).

# ShellyNousTakeover — Project Rules

Version: 1.05
Stand: 2026-10-05

- Standalone project for Shelly Plug M Gen3 and NOUS A8T takeover; no TmrSw Main. Small independent Main examples may demonstrate the documented Rescue contract.
- Private configuration and keys only through `TAKEOVER_PRIVATE_DIR`, outside this project. No private default paths and no secrets in logs.
- Select the target device only through `SHELLY_IP` or `NOUS_IP`; do not provide preset device addresses.
- Build both devices, including Rescue, with ESP-IDF. Toolchains use `TAKEOVER_IDF_PATH` and `TAKEOVER_IDF_TOOLS_PATH`. No Arduino CLI dependency or fixed mount paths.
- Before writes, Takeover checks real hardware, security, partition table, bootloader, running app, and embedded payloads. Network diagnostics must be available before migration checks and remain available on errors.
- The PC checks the manufacturer device and compatible upload path before upload. Once started, Takeover cannot determine the previous manufacturer firmware from its own app version alone. Do not pretend to verify provenance.
- Run automatically after successful guards; do not write when state is unknown or unclear. Read back and verify every write in full.
- Roll back errors only with a confirmed baseline and unambiguous write state. Do not claim successful rollback when device or flash state is unclear.
- The Shelly dual bootloader is the final loader for both partition tables. Do not replace it with a second loader solely to remove the stock path.
- State supported input geometries explicitly. Do not use generic `idf.py flash`.
- Use “partition table” in user instructions/documentation instead of the vague word “table.”
- Build/download products belong only in `generated/` or `.tools/`, not in the source tree.
- Old Prjs trees are porting references, not later runtime/build dependencies.

- README documents user operation, prerequisites, and Safe Boot. Public open work and release checks belong in TODO.md/TODO.de.md. ToDo.txt is local development history and is excluded from Git; public documents must not link to it.
