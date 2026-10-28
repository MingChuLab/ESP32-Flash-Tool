# Packaging & Distribution

Tester machines need no Python. The tool is distributed as a standalone
Windows executable built with PyInstaller (**must be built on Windows** —
PyInstaller cannot cross-compile).

## Build

Option 1 (recommended): double-click `build_exe.bat` — installs
dependencies and builds automatically.

Option 2, manually:

```bat
pip install PySide6 pyserial esptool pyinstaller
pyinstaller --noconfirm --clean ESP32FlashTool.spec
```

Output: `dist\ESP32FlashTool\ESP32FlashTool.exe` — distribute the
**whole folder** zipped (onedir mode: fast start, fewer antivirus false
positives). Firmware is NOT bundled; testers load it via the
"Browse..." button.

Notes:

- The spec explicitly collects esptool 5.x flasher stub data files and
  all files under `esp32flash/assets` recursively;
- For debugging, flip `console=False` to `True` in `ESP32FlashTool.spec`
  to see Python tracebacks;
- Frozen builds invoke esptool through `ESP32FlashTool.exe --esptool
  <args>` forwarding (see `flash_tool.py`), so a successful build must
  still be verified on a real device.

## Release Acceptance Checklist

Build OK does NOT mean the exe can flash. On a clean Windows PC
(no Python), with one ESP32 board:

1. Launch `ESP32FlashTool.exe`, pick the firmware + COM port;
2. Chip detect shows the chip ID (the esptool child process runs).
   Failure sign: `unrecognized arguments: -m esptool` means esptool
   forwarding is broken;
3. Full flash: progress bar advances, write-flash completes;
4. Post-flash check: boot log shows the expected version;
5. Re-flash the same image once (idempotent second run).

## Publishing a Release

- Upload `ESP32FlashTool.zip` to GitHub Releases together with its
  SHA256 checksum;
- Mention the common PyInstaller antivirus false positive in the
  release notes; optionally link a VirusTotal scan;
- Point to the source repository in the release notes to satisfy the
  GPL-3.0 corresponding-source requirement.
