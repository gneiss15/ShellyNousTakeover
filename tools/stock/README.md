<!-- tools/stock/README.md, Version: 1.02 -->
# Prepare Shelly manufacturer firmware

[Deutsch](README.DE.md)

These tools support preparation of the pinned Shelly stock firmware. The normal operating procedure is in the [main README](../../README.md); use [ShellyTakeover.py](../ShellyTakeover.py) as the entry point.

## Tools and policy files

| File | Purpose |
| --- | --- |
| [ValidateFirmwareLayout.py](ValidateFirmwareLayout.py) | Checks a stock package, its components and partition layout against the pinned package identity. |
| [ServeFirmware.py](ServeFirmware.py) | Serves exactly one specified package over HTTP; helper for a controlled local transfer. |
| [StockFirmware.py](../StockFirmware.py) | Retrieves and validates the pinned manufacturer firmware and checks the update flow. |
| [StockUpdatePolicy.json](../../ShellyTakeover/StockUpdatePolicy.json) | Specifies accepted source builds and the exact update target. |
| [StockFirmware.layout.json](../../ShellyTakeover/StockFirmware.layout.json) | Specifies package identity, components and partition layout. |

## Procedure

1. Select the device through `SHELLY_IP` and check its model, firmware version and build.
2. Continue with takeover preflight if the build is already accepted. For an allowed older build, offer only the explicitly supported manufacturer update path. Unknown intermediate builds and downgrades remain blocked.
3. Retrieve the exact target package over certificate-verified HTTPS, or supply an existing official package with `--stock-package`.
4. Check package identity, manifest, components and partition layout. Cached packages are checked again before every use.
5. Perform a manufacturer update only with `--execute --update-stock`. Recheck version, build and device identity before continuing takeover.

The cache is under the ignored `generated/` directory. Changing stable descriptors do not replace a pinned package identity; there is no insecure TLS fallback. A validated download alone does not establish a supported update path: the actual source build must also match the policy. Manufacturer updates may change the bootloader or partition layout.
