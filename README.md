# ESP32 Flash Tool

**English | [简体中文](README.zh-CN.md)**

One-click ESP32 firmware flashing: plug in the device, pick the firmware
and the serial port, press one button. The tool auto-detects the chip,
refuses mismatched firmware, flashes via esptool, and confirms the device
boots with the expected version. **Prebuilt executables need no ESP-IDF,
Python, or build system** — unzip and run.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
![Platform: Windows / Linux / macOS](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)

<p align="center">
  <img src="docs/images/screenshot.png" alt="ESP32 Flash Tool" width="720">
</p>

## Download

Windows: grab `ESP32FlashTool.zip` from [Releases](../../releases),
unzip the whole folder and run — nothing to install.

## Features

- **One firmware button, three sources**: release `manifest.json`
  (full anti-fault checks), IDF build-directory app `.bin` (bootloader
  and partition table auto-included), or merged factory `.bin`;
- **Anti-fault checks**: file size, SHA256, embedded version, and
  connected-chip match are verified before flashing;
- **One-click pipeline**: chip detect → flash → reset & boot verify;
- **Firmware info panel**: project, version, compile time, IDF version
  and flash parameters parsed directly from the image;
- **Bilingual UI** (Chinese/English) with automatic dark/light theme;
- **Baud fallback**: 921600 by default, automatic retry at 115200.

## Quick Start

### Run from source

Requires Python 3.10+.

```bash
pip install -r requirements.txt
python flash_tool.py
```

### Flash a device

1. Click **Browse...** and pick a firmware file:
   - `manifest.json` of a release directory (recommended);
   - an app `.bin` inside an IDF build directory;
   - a merged factory `.bin`.
2. Connect the device, click **Refresh** and pick the serial port;
3. Click **Start Flashing** and wait for the three-step flow;
4. ✅ means the device booted with the expected version; on ❌ save
   the log and hand it to the developer.

> No auto-reset circuit on the board? Hold **BOOT** while plugging in
> USB, release once flashing starts.

> Drivers: native USB-Serial/JTAG chips (ESP32-C6/S3) need no driver on
> Windows 10+; boards with CH340/CP210x need the matching driver.

## Troubleshooting

| Symptom | Fix |
| :--- | :--- |
| Serial port list is empty | Driver missing / charge-only cable; install driver or change cable |
| No chip detected | Not in download mode; retry or hold BOOT while plugging in |
| Flash fails at both baud rates | Change USB port (avoid unpowered hubs) and cable |
| Device did not boot | Retry once; if persistent, check the firmware |
| Chip mismatch | Firmware does not match the board |
| Antivirus flags the exe | Common PyInstaller false positive — whitelist it |

## Documentation

- [Firmware release format](docs/firmware-format.md) — manifest.json
  fields and how to generate a release directory;
- [Packaging & distribution](docs/packaging.md) — build the standalone
  Windows executable and the release acceptance checklist.

## Supported Targets

ESP32 / ESP32-S2 / S3 / C3 / C6 / H2 / P4 (whatever esptool 5.x can
identify). Firmware sources: release directory, IDF build directory,
merged factory image.

## License & Disclaimer

Copyright (C) 2026 MingChuLab

Released under [GPL-3.0](LICENSE). Third-party component licenses and
source availability are listed in [NOTICE](NOTICE).

Firmware flashing can brick your device — use at your own risk.

<!-- Doc sync: changes here must be mirrored in README.zh-CN.md -->
