# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for ESP32FlashTool.
# Build (Windows):  pyinstaller --noconfirm --clean ESP32FlashTool.spec
# Firmware is NOT bundled: testers load it via the "选择固件..." button.

a = Analysis(
    ['flash_tool.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

# esptool 5.x ships its flasher stub binaries as package data; PyInstaller's
# default hooks may miss them depending on version, so collect explicitly.
# collect_data_files yields (source, dest_dir) pairs; TOC entries need
# (dest_file, source, 'DATA') — dest must include the file name.
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
a.datas += [(os.path.join(dest, os.path.basename(src)), src, 'DATA')
            for src, dest in collect_data_files('esptool')]
a.hiddenimports += collect_submodules('esptool')

# Collect every FILE under espflash/assets, recursively: the folder also
# holds subdirectories (e.g. assets/icons), and blindly registering a
# directory as a DATA entry makes COLLECT fail with "Resource ... is not a
# valid file!" (latent until a subdir was added on 2026-10-14).
assets_src = os.path.join('espflash', 'assets')
if os.path.isdir(assets_src):
    for root, _dirs, files in os.walk(assets_src):
        for f in files:
            src = os.path.join(root, f)
            a.datas += [(src, src, 'DATA')]

pyz = PYZ(a.pure)

icon_file = os.path.join('espflash', 'assets', 'logo_minimal.ico')
if not os.path.exists(icon_file):
    icon_file = 'app.ico'

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ESP32FlashTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=icon_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ESP32FlashTool',
)
