"""Capture the device boot log over serial after flashing.

Used as the post-flash sanity check: the device must come up far enough to
print ROM/app output, and if the firmware prints its version (added in
app_main), it must match the manifest version.

Once success is positively confirmed (expected version seen, or the app-level
boot banner when no version is expected), the port is released after a short
grace window instead of idling until the full timeout — a confirmed-success
log has no more diagnostic value, and holding the port blocks serial monitors
and slows down batch flashing. Failure/suspicious paths always run the full
timeout: the complete log is the evidence needed for debugging.
"""

from dataclasses import dataclass
import re
import time

BOOT_MARKERS = ("ESP-ROM", "App version:")
DEFAULT_BAUD = 115200
DEFAULT_TIMEOUT_S = 15.0
# After a positive confirmation, keep reading this long to capture the log
# tail before releasing the port early.
SUCCESS_SETTLE_S = 1.0


@dataclass
class BootResult:
    log: str
    booted: bool
    version: str | None

    def version_matches(self, expected: str) -> bool:
        return self.version is not None and self.version == expected


def extract_version(log: str) -> str | None:
    # 1. Primary: explicitly marked app version banner (IDF app_init or custom)
    match = re.search(r"App version:\s*v?(\d+\.\d+\.\d+)", log)
    if match:
        return match.group(1)

    # 2. Fallback: search for any semantic version in lines that are NOT
    # framework/bootloader output (e.g. "ESP-IDF v5.1.2 2nd stage bootloader", "ESP-ROM")
    for line in log.splitlines():
        lower_line = line.lower()
        if "esp-idf" in lower_line or "bootloader" in lower_line or "esp-rom" in lower_line:
            continue
        match = re.search(r"\bv?(\d+\.\d+\.\d+)\b", line)
        if match:
            return match.group(1)
    return None


def _read_until(ser, deadline: float, stop_event, chunks: list) -> None:
    """Read into `chunks` until the deadline (or until stopped)."""
    while time.monotonic() < deadline:
        if stop_event is not None and stop_event.is_set():
            break
        data = ser.read(4096)
        if data:
            chunks.append(data.decode("utf-8", "replace"))


def capture_boot_log(port: str, baud: int = DEFAULT_BAUD,
                     timeout_s: float = DEFAULT_TIMEOUT_S,
                     stop_event=None, expected_version: str | None = None) -> BootResult:
    """Capture the boot log; `expected_version` (from the firmware manifest)
    enables early release: once the log confirms success the port is freed
    after SUCCESS_SETTLE_S instead of waiting out the full `timeout_s`."""
    import serial

    chunks: list[str] = []
    ser = serial.Serial(port, baud, timeout=0.2)
    try:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if stop_event is not None and stop_event.is_set():
                break
            data = ser.read(4096)
            if not data:
                continue
            chunks.append(data.decode("utf-8", "replace"))
            log = "".join(chunks)
            confirmed = (bool(expected_version)
                         and extract_version(log) == expected_version) \
                or (not expected_version and "App version:" in log)
            if confirmed:
                _read_until(ser, time.monotonic() + SUCCESS_SETTLE_S,
                            stop_event, chunks)
                break
    finally:
        ser.close()

    log = "".join(chunks)
    booted = any(marker in log for marker in BOOT_MARKERS)
    return BootResult(log=log, booted=booted, version=extract_version(log))
