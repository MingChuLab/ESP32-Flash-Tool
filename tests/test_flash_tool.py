"""Unit tests for ESP32 Flash Tool core components."""
from pathlib import Path
import struct
import tempfile
import unittest

from espflash.esptool_job import parse_write_progress
from espflash.i18n import STRINGS, _
from espflash.manifest import (
    IMAGE_MAGIC,
    ManualImage,
    read_image_header,
)
from espflash.serialboot import extract_version


class TestManifest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_verify_empty_file(self):
        """A 0-byte file should be caught gracefully without IndexError."""
        empty_bin = self.dir_path / "empty.bin"
        empty_bin.write_bytes(b"")

        img = ManualImage.from_bin(empty_bin)
        problems = img.verify_artifacts()
        self.assertTrue(len(problems) > 0)
        self.assertIn(_("err_bad_image"), problems)

    def test_verify_invalid_header(self):
        """Random binary data without ESP image magic (0xE9) should be rejected."""
        corrupt_bin = self.dir_path / "corrupt.bin"
        corrupt_bin.write_bytes(b"\x00\x01\x02\x03\x04\x05")

        img = ManualImage.from_bin(corrupt_bin)
        problems = img.verify_artifacts()
        self.assertTrue(len(problems) > 0)
        self.assertIn(_("err_bad_image"), problems)

    def test_read_image_header(self):
        """Test header parsing on constructed header."""
        valid_bin = self.dir_path / "valid.bin"
        # magic: 0xE9, segments: 3, flash_mode: 0, flash_size_freq: 0x2F (4MB, 80m), entry: 0x40080000
        hdr_bytes = bytearray(24)
        hdr_bytes[0] = IMAGE_MAGIC
        hdr_bytes[1] = 3
        hdr_bytes[2] = 0
        hdr_bytes[3] = 0x2F
        struct.pack_into("<I", hdr_bytes, 4, 0x40080000)
        valid_bin.write_bytes(bytes(hdr_bytes))

        header = read_image_header(valid_bin)
        self.assertTrue(header.valid)
        self.assertEqual(header.segments, 3)
        self.assertEqual(header.entry, 0x40080000)


class TestSerialBoot(unittest.TestCase):
    def test_bootloader_only_does_not_extract_idf_version(self):
        """ESP-IDF bootloader line must not be mistakenly identified as app version."""
        boot_log = (
            "ESP-ROM:esp32c6-20220919\n"
            "Build:Sep 19 2022\n"
            "rst:0x1 (POWERON),boot:0xc (SPI_FAST_FLASH_BOOT)\n"
            "I (31) boot: ESP-IDF v5.1.2 2nd stage bootloader\n"
            "I (31) boot: compile time 12:34:56\n"
            "I (35) boot: chip revision: v0.0\n"
        )
        self.assertIsNone(extract_version(boot_log))

    def test_app_version_banner(self):
        """App version banner should be extracted with highest priority."""
        boot_log = (
            "I (31) boot: ESP-IDF v5.1.2 2nd stage bootloader\n"
            "I (100) app_init: App version: 1.2.3\n"
        )
        self.assertEqual(extract_version(boot_log), "1.2.3")

    def test_app_custom_version_line(self):
        """Non-framework version lines should be parsed by fallback."""
        boot_log = (
            "I (31) boot: ESP-IDF v5.1.2 2nd stage bootloader\n"
            "I (120) main: Firmware v2.0.4 initialized\n"
        )
        self.assertEqual(extract_version(boot_log), "2.0.4")


class TestEsptoolJob(unittest.TestCase):
    def test_parse_write_progress(self):
        line = "Writing at 0x00010000... (50 %)"
        self.assertEqual(parse_write_progress(line), 50)

    def test_parse_write_progress_with_segments(self):
        # 2 segments: (0x0, 1000 bytes) and (0x10000, 1000 bytes)
        segments = [(0x0, 1000), (0x10000, 1000)]
        line = "Writing at 0x00010000... (50 %)"
        # done_before = 1000, current = 50% * 1000 = 500 => 1500 / 2000 = 75%
        self.assertEqual(parse_write_progress(line, segments), 75)

    def test_parse_write_progress_zero_total(self):
        segments = [(0x0, 0)]
        line = "Writing at 0x00000000... (50 %)"
        # Should not raise ZeroDivisionError
        self.assertEqual(parse_write_progress(line, segments), 50)


class TestI18n(unittest.TestCase):
    def test_key_parity(self):
        en_keys = set(STRINGS["en"].keys())
        zh_keys = set(STRINGS["zh"].keys())
        self.assertEqual(en_keys, zh_keys)


if __name__ == "__main__":
    unittest.main()
