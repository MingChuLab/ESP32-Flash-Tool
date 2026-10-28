# Firmware Release Format

A release directory enables the tool's full anti-fault checks (file
existence, size, SHA256, embedded version) and release traceability.

## Directory Contents

| File | Purpose |
| :--- | :--- |
| `manifest.json` | version, target chip, factory image file name, SHA256 (required) |
| `<name>_factory.bin` | single merged image from `esptool merge_bin` (required) |
| `flasher_args.json` | flash mode/size/frequency (optional; chip defaults otherwise) |

## manifest.json

```json
{
  "project": "myapp",
  "target": "esp32c6",
  "version": "1.2.3",
  "factory_bin": "myapp_esp32c6_v1.2.3_factory.bin",
  "factory_sha256": "<sha256 of the factory image>",
  "factory_size_bytes": 2402304
}
```

Optional keys: `git_commit`, `build_time` (displayed in the firmware
info panel when the image itself carries no compile time).

## Generating a Release Directory

Run in the ESP-IDF build directory:

```bash
# Merge the individual bins into one factory image
esptool.py --chip esp32c6 merge_bin -o myapp_esp32c6_vX.Y.Z_factory.bin \
    --flash-mode dio --flash-size 4MB --flash-freq 80m @flash_args
# Then generate manifest.json with the version, target, sha256 and size
# of the merged image.
```

## Other Accepted Firmware Sources

- **IDF build directory**: pick the app `.bin` (e.g. `build/xxx.bin`).
  The sibling `flasher_args.json` (or `flash_args`) supplies the
  bootloader and partition table, which are flashed together at their
  proper offsets — no manual merge step.
- **Merged factory `.bin`**: chip, version and project are read from
  the image header and app descriptor. A manual chip choice is only
  needed for v0 headers without a chip id (e.g. classic ESP32).
- **Bare app image without boot components**: rejected, because the
  device cannot boot without a bootloader.

## How Verification Works

- Chip names are compared normalized: `ESP32-C6` (esptool) and
  `esp32c6` (manifest) are lowercased with `-`/`_` stripped;
- The app descriptor (`esp_app_desc_t`) is read at offset 0x10000 for
  merged images and at 0x0 for bare app images, auto-adapting to
  24-byte v1 / 8-byte v0 image headers;
- After flashing, the device is reset and the boot log captured;
  success requires the reported app version to match the manifest
  version (when a version is known).
