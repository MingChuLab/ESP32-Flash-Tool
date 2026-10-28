"""esptool subprocess wrappers and Qt worker threads.

esptool v5 verifies written data automatically, so write_flash needs no
--verify flag. Commands are built as lists and streamed line by line so the
GUI can show live progress ("Writing at 0x... (NN %)").
"""

from pathlib import Path
import re
import subprocess
import sys
import threading

from PySide6.QtCore import QThread, Signal

# Frozen (PyInstaller): sys.executable is the app exe itself and the
# bootloader ignores "-m", so the entry point above forwards "--esptool <args>"
# into the bundled esptool package instead. Source runs keep plain python -m.
ESPTOOL_CMD = ([sys.executable, "--esptool"] if getattr(sys, "frozen", False)
               else [sys.executable, "-m", "esptool"])

CHIP_DETECT_RES = (
    re.compile(r"Chip type:\s+(\S+)"),   # esptool v5
    re.compile(r"Chip is (\S+)"),        # esptool <= v4
)
PROGRESS_LINE_PREFIX = "Writing at"
PROGRESS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")  # esptool v5: "100.0% 1.38MB/..."
# esptool v4 and v5 both embed the ABSOLUTE flash address in the description:
# "Writing at 0x00010000 ... 42.0% 1.38MB/5.00MB [0:05]"
WRITE_ADDR_RE = re.compile(r"Writing at (0x[0-9a-fA-F]+)")

FLASH_BAUD_PRIMARY = 921600
FLASH_BAUD_FALLBACK = 115200


def detect_chip_cmd(port: str) -> list[str]:
    return ESPTOOL_CMD + ["--port", port, "--after", "no-reset", "chip-id"]


def flash_cmd(port: str, chip: str, baud: int,
              flash_files: list[tuple[str, Path]],
              before: str = "default-reset", after: str = "hard-reset",
              write_flash_args: list[str] | None = None) -> list[str]:
    """Build the write-flash command. `flash_files` is a list of
    (offset, image) pairs — a single ("0x0", factory.bin) for merged
    images, or per-partition offsets for build-directory mode."""
    cmd = ESPTOOL_CMD + [
        "--chip", chip,
        "--port", port,
        "--baud", str(baud),
        "--before", before,
        "--after", after,
        "write-flash",  # v5 canonical spelling ('write_flash' is deprecated)
    ]
    cmd += list(write_flash_args or [])
    for offset, image in flash_files:
        cmd += [offset, str(image)]
    return cmd


def flash_segments(flash_files: list[tuple[str, Path]]) -> list[tuple[int, int]]:
    """(flash_base, image_size) pairs for progress normalization."""
    return [(int(offset, 16), Path(image).stat().st_size) for offset, image in flash_files]


def parse_write_progress(line: str,
                         segments: list[tuple[int, int]] | None = None) -> int | None:
    """Extract write progress 0..100 from one esptool output line.

    esptool reports progress PER FILE SEGMENT (each segment restarts at 0%),
    which made the GUI bar sawtooth at every file boundary. When `segments`
    (the (flash_base, image_size) table from flash_segments) is given, the
    segment is identified by the absolute address in the progress line and
    the percentage is re-based across the whole job. An address exactly on a
    boundary belongs to the earlier segment — that is a segment's final
    100% update. Without an address (or without segments) the raw
    segment-local percentage is returned.
    """
    if PROGRESS_LINE_PREFIX not in line:
        return None
    match = PROGRESS_RE.search(line)
    if not match:
        return None
    pct = float(match.group(1))
    if not segments:
        return int(pct)
    addr_match = WRITE_ADDR_RE.search(line)
    if not addr_match:
        return int(pct)
    addr = int(addr_match.group(1), 16)
    ordered = sorted(segments)
    total = sum(size for _, size in ordered)
    if total <= 0:
        return int(pct)
    done_before = 0
    for base, size in ordered:
        # First match wins: on a shared boundary this is the earlier
        # segment's final update (pct 100), not the next segment's start.
        if base <= addr <= base + size:
            return int((done_before + pct / 100.0 * size) / total * 100)
        done_before += size
    return int(pct)


def normalize_chip_name(name: str) -> str:
    """esptool reports 'ESP32-C6' but --chip/manifest use 'esp32c6'."""
    return name.lower().replace("-", "").replace("_", "").strip()


def parse_detected_chip(output: str) -> str | None:
    for pattern in CHIP_DETECT_RES:
        match = pattern.search(output)
        if match:
            return match.group(1)
    return None


class ProcThread(QThread):
    """Run one esptool command, streaming stdout lines and progress."""

    line = Signal(str)
    progress = Signal(int)
    done = Signal(bool)

    def __init__(self, cmd: list[str], parent=None,
                 segments: list[tuple[int, int]] | None = None):
        super().__init__(parent)
        self.cmd = cmd
        self.output = ""
        self.segments = segments
        self._proc: subprocess.Popen | None = None

    def run(self):
        try:
            self._proc = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
            )
        except OSError as e:
            self.output = f"failed to start esptool: {e}"
            self.line.emit(self.output)
            self.done.emit(False)
            return

        assert self._proc.stdout is not None
        for raw in self._proc.stdout:
            text = raw.rstrip("\n")
            self.output += raw
            self.line.emit(text)
            pct = parse_write_progress(text, self.segments)
            if pct is not None:
                self.progress.emit(pct)
        rc = self._proc.wait()
        self.done.emit(rc == 0)

    def stop(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()


class BootCheckThread(QThread):
    """Reset-grace + serial boot capture, runs after flashing."""

    done = Signal(object)

    def __init__(self, port: str, timeout_s: float, expected_version: str = "",
                 parent=None):
        super().__init__(parent)
        self.port = port
        self.timeout_s = timeout_s
        self.expected_version = expected_version
        self._stop = threading.Event()

    def run(self):
        import time
        from esp32flash.serialboot import BootResult, capture_boot_log

        time.sleep(0.5)  # let esptool release the port and the chip reset
        try:
            result = capture_boot_log(self.port, timeout_s=self.timeout_s,
                                      stop_event=self._stop,
                                      expected_version=self.expected_version or None)
        except Exception as e:
            result = BootResult(log=f"serial open failed: {e}", booted=False, version=None)
        self.done.emit(result)

    def stop(self):
        self._stop.set()
