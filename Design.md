Deutsche Version [hier](Design.de.md).

# Takeover Workflow and Cleanup

Version: 1.05
Stand: 2026-10-05

## Responsibilities

PC: obtain and verify toolchain/dependencies, validate private configuration/keys, build and check payloads, check the manufacturer device before upload, upload the suitable OTA package, show status, and verify final Rescue reachability. The PC does not control individual flash writes later.

App: start AP+STA and web diagnostics first, perform real flash/chip/security/partition and image checks, write automatically only after full approval, read everything back, check protected areas, roll back errors where possible, select the boot target, and start Rescue. The web interface shows phase, errors, and rollback status. Unclear flash/protection state forbids reboot and further normal writes.

Not every provenance check can be reconstructed after upload. The running app is then Takeover, not the previous manufacturer firmware. Shelly Takeover can inspect the preserved stock app_0; Nous/Tasmota can have its previous app replaced by OTA. The PC must therefore check the supported manufacturer path before upload. Chip/flash alone prove neither device model nor safe GPIO assignment.

## Shelly: required final workflow

1. Manufacturer OTA installs only Takeover app_1 and its associated empty fs_1. It does not install the bootloader or partition table.
2. Takeover checks chip, flash, security, old partition table, running slot, known original bootloader identity, SH0S, stock app, and embedded payloads.
3. Write the final dual bootloader only if needed and read it all back. Do not rewrite an already byte-identical loader. Retain verified original bytes for bounded rollback; no test reboot is needed.
4. Then prepare Rescue, NVS/OTA partitions, and bounded rollback metadata; read them back and check preserved areas. The existing MigrationStage writer already requires the final loader and seals its hash in the baseline. Changing the loader after staging would invalidate that baseline.
5. Write/read back the new partition table; check final invariants and select Rescue as boot target. On errors before reboot, restore only confirmed original data through bounded writers.
6. Rescue starts, accepts signed uploads, and rejects old Takeover as Main.

The dual bootloader is not temporary. With the old partition table it knows SH0S/Stock; with the new partition table it knows the factory Rescue/Main path and GPIO7. After the switch, the stock path is inactive. The loader does not need replacement with a second “normal” loader. A loader tailored only to the new partition table would require additional development/testing and make rollback harder without improving the user workflow.

## What can be removed from the previous workflow

- Readout first install, GPIO discovery, padding write test, and test-node steps were development/hardware identification, not user migration steps.
- Original → StockLayoutBootloader → DualLayoutBootloader: fresh devices can receive the final dual bootloader directly. Previous loaders need not be embedded/supported for the fresh published path.
- Separate loader test reboot before the new partition table is not inherently required for the final flow; readback/identity/area checks remain.
- Repeated independent 8 MiB PC dumps between every phase and PC-controlled individual buttons can be removed from the user workflow. Existing writers do require baselines/checkpoints, however; those requirements must be deliberately met in the app. Do not simply comment out existing checks.
- Stock round-trip and another Takeover upload to update the development app are unnecessary for a freshly built final Takeover.
- Manufacturer packages, chats, and real captures as build prerequisites should be replaced by reproducible payloads from approved sources and verified identity metadata. The original loader need not be stored as a proprietary binary in the repo: rollback needs verified original bytes from the actual device.

## What remains

- PC precheck of manufacturer/upload path; payload/signature/geometry checks during build.
- Authoritative app guards; SDK partition table must use the actual offset.
- Known original loader, safe stock boot selection, protected factory data.
- Erase/write/readback and restoration of the SDK write-protection configuration.
- Unambiguous phase, bounded baseline/original data, protected-area checks, error diagnosis, and rollback where evidence permits.
- Final Rescue reachability from the PC. Takeover cannot by itself confirm its successful reboot into another app.

There is no stock rollback service after Rescue starts. Main is considered empty even though Takeover bytes remain. Power loss while writing the loader/partition table remains the accepted risk; do not claim atomicity.

## Nous: differences and existing gaps

The existing TasmotaMigration already uses the target partition table: Rescue safeboot 0x10000/0xD0000, Main app0 0xE0000/0x2D0000, FS 0x3B0000/0x50000. It writes/verifies Rescue, replaces/verifies the loader at 0x1000, then selects Rescue. No Shelly dual loader, SH0S, or partition-table change is required for this supported input geometry.

However, the old TasmotaMigration lacks network diagnostics before error guards: StopWithError waits indefinitely, and web service is mainly provided in AlreadyMigrated mode. Before reuse, safe model detection/bootloader identity/Secure Boot checks, persistent diagnostics, and phase-appropriate rollback need review or implementation. Past success does not justify copying it unchanged.

The new Nous app starts network/web diagnostics before guards and uses the known original loader identity from OriginalFirmware.json and the exact partition table. It writes Rescue first, verifies payload and erased remainder as well as the SDK image, then replaces the loader and only afterward selects Rescue. NVS, running Main, and FS are preserved and checked with independent area hashes. Original loader and OTA partition are kept in RAM for rollback. Old SafeBoot is not saved; bounded rollback preserves a boot path to the running Takeover, not the original Tasmota. Do not roll back with unclear protection/flash state. Hardware and SDK image checks are mocked in host tests; build/host test is not a new device test.

## Next implementation

1. Bring only the firmware/Rescue/update sources needed into this project; adjust relative build paths to the new structure, with no references back to Prjs.
2. Use one private configuration and toolchain download/version check; do not silently mix SDK 5.5.1 with the current Nous bootloader requirement 5.5.5 through ALLOW_IDF_VERSION_MISMATCH. Define and test compatibility concretely.
3. Reduce the app-internal automatic state machine, web status, baseline, and rollback specifically for the final path. Continue testing host fault injection separately.
4. Build standalone, then use a test node and a suitable fresh device. Do not derive new hardware approval from previous checks.

## Clarification of Nous error outcomes

A guard error before flash writes causes a wait loop that cannot be diagnosed over the web, but does not automatically mean a damaged bootloader. The previous bootloader and running Takeover may still be present. Rebooting does not fix the error; the app may encounter it again.

After a faulty loader erase/write, bootability is uncertain. The previous code does not restore a saved original loader in that case. Do not say “every error bricks it” or promise network recovery.

## Unified toolchain

Use ESP-IDF exclusively for both device paths, including Rescue. The existing small IDF adapter from Shelly Rescue replaces the few Arduino API calls (String/GPIO/delay); no Arduino core/CLI build is required. The old Nous Rescue build remains a reference, not a new external prerequisite. A Nous IDF build is not a device test established by this decision.

## Development checks

VerifyRescueGuards.py needs g++ and OpenSSL development headers (e.g. libssl-dev) for its host test. VerifyMigration.py needs host cc and these headers. These are test prerequisites, not an additional firmware toolchain. Migration fault injection checks synthetic flash using real SHA256 hashes; with `--shelly-geometry` it uses the 8 MiB geometry, otherwise the 4 MiB test geometry.
