"""Generate high-resolution interface screenshots for README documentation."""
import os
from pathlib import Path
import struct
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from espflash.gui_minimal import MainWindow
from espflash.i18n import set_language
from espflash.manifest import FirmwareManifest, ManualImage


def create_mock_firmware(target_dir: Path) -> Path:
    bin_path = target_dir / "smart_gadget_esp32c6_v1.0.0_factory.bin"
    total_size = 2402304
    data = bytearray(total_size)

    # 1. Image Header at 0x0 (DIO mode, 4MB flash, 80MHz, ESP32-C6)
    data[0] = 0xE9
    data[1] = 4
    data[2] = 2     # DIO
    data[3] = 0x20  # 4MB, 80MHz on C6
    struct.pack_into("<I", data, 4, 0x40080000)
    struct.pack_into("<H", data, 12, 0x0D)  # 0x0D = esp32c6

    # 2. App Image Header at 0x10000
    data[0x10000] = 0xE9
    data[0x10000 + 1] = 4
    data[0x10000 + 2] = 2
    data[0x10000 + 3] = 0x20
    struct.pack_into("<H", data, 0x10000 + 12, 0x0D)  # chip_id in app image header

    # 3. App Descriptor at 0x10000 + 24 + 8 = 0x10020
    desc_off = 0x10000 + 24 + 8
    struct.pack_into("<I", data, desc_off, 0xABCD5432)  # APP_DESC_MAGIC
    ver = b"1.0.0\0"
    data[desc_off + 16:desc_off + 16 + len(ver)] = ver
    proj = b"smart_gadget\0"
    data[desc_off + 48:desc_off + 48 + len(proj)] = proj
    ctime = b"14:20:08\0"
    data[desc_off + 80:desc_off + 80 + len(ctime)] = ctime
    cdate = b"Oct 20 2026\0"
    data[desc_off + 96:desc_off + 96 + len(cdate)] = cdate
    idf = b"v5.3.1\0"
    data[desc_off + 112:desc_off + 112 + len(idf)] = idf

    bin_path.write_bytes(data)
    return bin_path


def render_screenshot(lang: str, output_path: Path):
    set_language(lang)
    with tempfile.TemporaryDirectory() as tmp_dir:
        bin_path = create_mock_firmware(Path(tmp_dir))
        image = ManualImage.from_bin(bin_path, fallback_chip="esp32c6")

        win = MainWindow(manifest=image)
        # Select explicit language in the UI combo
        idx = win.lang_combo.findData(lang)
        if idx >= 0:
            win.lang_combo.setCurrentIndex(idx)
            win._on_language_changed(idx)

        # Prettify path display to simulate a real user workspace
        clean_path = r"D:\firmware\esp32c6\smart_gadget_esp32c6_v1.0.0_factory.bin"
        win.fw_path.setText(clean_path)

        # Populate simulated COM port
        port_name = "COM5 - Silicon Labs CP210x (COM5)" if lang == "en" else "COM5 - USB-Serial CP210x (COM5)"
        win.port_combo.clear()
        win.port_combo.addItem(port_name, "COM5")
        win.port_combo.setCurrentIndex(0)
        win._update_flash_enabled()

        # Adjust dimensions to standard crisp layout
        win.resize(740, 520)
        win.show()

        # Process any pending events for layout stability
        app.processEvents()

        pixmap = win.grab()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pixmap.save(str(output_path), "PNG")
        print(f"[{lang}] Screenshot saved to {output_path} ({pixmap.width()}x{pixmap.height()})")
        win.close()


if __name__ == "__main__":
    app = QApplication([])
    docs_img_dir = Path(__file__).resolve().parent.parent / "docs" / "images"

    render_screenshot("en", docs_img_dir / "screenshot.png")
    render_screenshot("zh", docs_img_dir / "screenshot_zh.png")
