#!/usr/bin/env python3
"""
=============================================================================
 ESP32 Flash Tool
=============================================================================
 Copyright (C) 2026 MingChuLab

 This program is free software: you can redistribute it and/or modify it
 under the terms of the GNU General Public License as published by the
 Free Software Foundation, either version 3 of the License, or (at your
 option) any later version. See LICENSE for the full text and NOTICE for
 third-party component licenses.
=============================================================================
 One-click firmware flashing for testers. No ESP-IDF, no build system:
 pick the firmware (release directory with manifest.json, or a bare merged
 .bin), pick the serial port, press one button. The tool verifies the image
 against the release manifest (size/SHA256/embedded version) when available,
 checks the connected chip matches the firmware target, flashes via esptool,
 then confirms the device boots and reports the expected version.

 Usage:
   python3 flash_tool.py [--manifest-dir /path/to/release/dir]

 Requires: PySide6, pyserial, esptool (pip install).
=============================================================================
"""

import argparse
import sys
from pathlib import Path

# --- PyInstaller frozen-mode esptool forwarding -----------------------------
# esp32flash.esptool_job launches esptool as `[sys.executable, "-m", "esptool"]`,
# which breaks once frozen: sys.executable is THIS exe and the bootloader
# does not interpret "-m" (argparse then dies with "unrecognized arguments").
# Frozen builds instead invoke `ESP32FlashTool.exe --esptool <args>`; the
# esptool package and its flasher stubs are already bundled by the spec
# (collect_submodules + collect_data_files), so forward straight into it.
if getattr(sys, "frozen", False) and len(sys.argv) > 1 and sys.argv[1] == "--esptool":
    from esptool import _main as _esptool_main  # esptool 5.x console entry

    sys.argv = ["esptool"] + sys.argv[2:]
    _esptool_main()
    # esptool.main() swallows SystemExit(0) (re-raises only non-zero codes),
    # so a successful run returns here: stop before the GUI code below —
    # this process IS the esptool child, not the app.
    sys.exit(0)

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox

from esp32flash.assets import get_app_icon, setup_windows_app_id
from esp32flash.gui import ORG_NAME, APP_NAME
from esp32flash.i18n import _, set_language
from esp32flash.manifest import FirmwareManifest, ManifestError

DEFAULT_FIRMWARE_DIR = Path(__file__).resolve().parent / "firmware"
DEFAULT_MANIFEST_DIR = DEFAULT_FIRMWARE_DIR if DEFAULT_FIRMWARE_DIR.is_dir() else None


def main() -> int:
    parser = argparse.ArgumentParser(description="ESP32 firmware flash tool (generic)")
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR,
                        help="directory containing manifest.json + factory image "
                             "(default: auto-detected in repo or picked in GUI)")
    parser.add_argument("--ui", choices=["minimal", "standard"], default="minimal",
                        help="UI layout edition: 'minimal' (modern card-based, default) or 'standard' (classic)")
    args = parser.parse_args()

    # Register explicit AppUserModelID on Windows before QApplication
    setup_windows_app_id()

    app = QApplication(sys.argv)
    app_icon = get_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    # resolve language before any dialog can appear ("system" -> OS locale)
    set_language(QSettings(ORG_NAME, APP_NAME).value("language"))

    manifest = None
    if args.manifest_dir is not None:
        if args.manifest_dir.is_dir():
            try:
                manifest = FirmwareManifest.load(args.manifest_dir)
            except ManifestError as e:
                QMessageBox.warning(None, _("err_manifest_load_title"), str(e))
        else:
            print(_("manifest_dir_missing").format(dir=args.manifest_dir))

    if args.ui == "standard":
        from esp32flash.gui import MainWindow
    else:
        from esp32flash.gui_minimal import MainWindow

    window = MainWindow(manifest)
    window.show()  # MainWindow sizes itself (window height follows log visibility)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
