"""Firmware manifest loading and artifact verification.

The release directory (e.g. firmware/esp32c6/) ships a manifest.json next to
the merged factory image. The tool refuses to flash anything whose file does
not match the manifest (size / SHA256) or whose embedded application
descriptor version differs from the manifest version.
"""

from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path
import struct

from esp32flash.i18n import _

APP_DESC_MAGIC = 0xABCD5432
DEFAULT_APP_OFFSET = 0x10000
_APP_DESC_VERSION_OFF = 16
_APP_DESC_PROJECT_OFF = 48
_APP_DESC_COMPILE_TIME_OFF = 80   # compile_time[16] + compile_date[16]
_APP_DESC_IDF_VER_OFF = 112       # idf_ver[32]
_IMG_HDR_CHIP_ID_OFF = 12

FLASH_MODES = {0: "qio", 1: "qout", 2: "dio", 3: "dout"}
FLASH_SIZES = {0: "1MB", 1: "2MB", 2: "4MB", 3: "8MB",
               4: "16MB", 5: "32MB", 6: "64MB", 7: "128MB"}
# Flash frequency encoding is chip-specific (mirrors esptool's per-target
# FLASH_FREQUENCY tables); chips not listed use the classic ESP32 map.
_FLASH_FREQS_DEFAULT = {0x0: "40m", 0x1: "26m", 0x2: "20m", 0xF: "80m"}
_FLASH_FREQS_BY_CHIP = {
    # 0x0 doubles as 40m (ROM mspi erratum), esptool displays the first hit
    "esp32c6": {0x0: "80m", 0x2: "20m"},
    "esp32h2": {0x0: "24m", 0x1: "16m", 0x2: "12m", 0xF: "48m"},
    "esp32c2": {0x0: "30m", 0x1: "20m", 0x2: "15m", 0xF: "60m"},
}

# Image header "chip_id" values (esptool ImageChipId) for targets we ship.
_IMAGE_CHIP_NAMES = {
    0x00: "esp32",
    0x02: "esp32s2",
    0x05: "esp32c3",
    0x09: "esp32s3",
    0x0D: "esp32c6",
}
# Flash frequency tables keyed by chip id for the targets above; ESP32-S2/S3/
# C3/P4 inherit the classic ESP32 encoding.
_CHIP_ID_FLASH_FREQS = {chip_id: _FLASH_FREQS_BY_CHIP.get(name, _FLASH_FREQS_DEFAULT)
                        for chip_id, name in _IMAGE_CHIP_NAMES.items()}

IMAGE_MAGIC = 0xE9


class ManifestError(Exception):
    pass


@dataclass
class AppDesc:
    version: str
    project: str
    chip_id: int | None
    compile_time: str = ""
    idf_ver: str = ""


@dataclass
class ImageHeader:
    """ESP image header (v1 extended header when present)."""

    valid: bool = False
    segments: int = 0
    flash_mode: str = ""
    flash_size: str = ""
    flash_freq: str = ""
    entry: int = 0
    chip_id: int | None = None


def _cstr(buf: bytes, off: int, size: int) -> str:
    return buf[off:off + size].split(b"\0")[0].decode("utf-8", "replace")


def read_app_desc(bin_path: Path, app_offset: int = DEFAULT_APP_OFFSET) -> AppDesc | None:
    """Parse esp_app_desc_t from a firmware image.

    Handles both v0 (8-byte) and v1 (24-byte, chips with chip_id) image
    headers by probing both layouts for the app description magic.
    """
    with open(bin_path, "rb") as f:
        for hdr_size in (24, 8):
            f.seek(app_offset + hdr_size + 8)
            head = f.read(_APP_DESC_IDF_VER_OFF + 32)
            if len(head) < 4:
                continue
            (magic,) = struct.unpack_from("<I", head, 0)
            if magic != APP_DESC_MAGIC:
                continue
            chip_id = None
            if hdr_size == 24 and len(head) >= _IMG_HDR_CHIP_ID_OFF + 2:
                f.seek(app_offset + _IMG_HDR_CHIP_ID_OFF)
                raw_chip = f.read(2)
                if len(raw_chip) == 2:
                    chip_id = struct.unpack("<H", raw_chip)[0]
            return AppDesc(
                version=_cstr(head, _APP_DESC_VERSION_OFF, 32),
                project=_cstr(head, _APP_DESC_PROJECT_OFF, 32),
                chip_id=chip_id,
                compile_time=f"{_cstr(head, _APP_DESC_COMPILE_TIME_OFF + 16, 16)} "
                             f"{_cstr(head, _APP_DESC_COMPILE_TIME_OFF, 16)}".strip(),
                idf_ver=_cstr(head, _APP_DESC_IDF_VER_OFF, 32),
            )
    return None


def read_image_header(bin_path: Path, offset: int = 0) -> ImageHeader:
    """Parse the ESP image header at `offset` (0x0 for a merged factory image)."""
    hdr = ImageHeader()
    try:
        with open(bin_path, "rb") as f:
            f.seek(offset)
            head = f.read(24)
    except OSError:
        return hdr
    if len(head) < 24 or head[0] != IMAGE_MAGIC:
        return hdr
    hdr.valid = True
    hdr.segments = head[1]
    hdr.flash_mode = FLASH_MODES.get(head[2], f"?{head[2]}")
    hdr.flash_size = FLASH_SIZES.get(head[3] >> 4, "?")
    # v1 extended header carries the chip id; 0xFFFF means legacy v0 header
    if head[_IMG_HDR_CHIP_ID_OFF:_IMG_HDR_CHIP_ID_OFF + 2] != b"\xff\xff":
        hdr.chip_id = struct.unpack_from("<H", head, _IMG_HDR_CHIP_ID_OFF)[0]
    freq_code = head[3] & 0x0F
    freqs = _CHIP_ID_FLASH_FREQS.get(hdr.chip_id, _FLASH_FREQS_DEFAULT)
    hdr.flash_freq = freqs.get(freq_code, f"?{freq_code:#x}")
    hdr.entry = struct.unpack_from("<I", head, 4)[0]
    return hdr


def describe_image(bin_path: Path) -> tuple[ImageHeader | None, AppDesc | None]:
    """Best-effort firmware info for display: image header at 0x0 plus the
    app descriptor (merged factory image: at 0x10000; bare app image: at 0x0)."""
    bin_path = Path(bin_path)
    header = read_image_header(bin_path)
    desc = None
    for app_offset in (DEFAULT_APP_OFFSET, 0):
        desc = read_app_desc(bin_path, app_offset)
        if desc is not None:
            break
    return (header if header.valid else None), desc


@dataclass
class FirmwareManifest:
    directory: Path
    project: str
    target: str
    version: str
    git_commit: str
    build_time: str
    factory_bin: Path
    factory_sha256: str
    factory_size_bytes: int
    write_flash_args: list = field(default_factory=list)
    chip_auto: bool = False

    @property
    def source_label(self) -> str:
        return _("src_release").format(dir=self.directory)

    @classmethod
    def load(cls, directory: Path) -> "FirmwareManifest":
        directory = Path(directory)
        meta_path = directory / "manifest.json"
        if not meta_path.is_file():
            raise ManifestError(f"manifest.json not found in {directory}")
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ManifestError(f"invalid manifest.json: {e}") from e

        missing = [k for k in ("target", "version", "factory_bin", "factory_sha256") if k not in meta]
        if missing:
            raise ManifestError(f"manifest.json missing keys: {', '.join(missing)}")

        write_flash_args = []
        flasher_args_path = directory / "flasher_args.json"
        if flasher_args_path.is_file():
            try:
                flasher_args = json.loads(flasher_args_path.read_text(encoding="utf-8"))
                write_flash_args = flasher_args.get("write_flash_args", [])
            except json.JSONDecodeError:
                pass

        return cls(
            directory=directory,
            project=meta.get("project", directory.name),
            target=meta["target"],
            version=meta["version"],
            git_commit=meta.get("git_commit", ""),
            build_time=meta.get("build_time", ""),
            factory_bin=directory / meta["factory_bin"],
            factory_sha256=meta["factory_sha256"],
            factory_size_bytes=int(meta.get("factory_size_bytes", 0)),
            write_flash_args=write_flash_args,
        )

    def verify_artifacts(self) -> list[str]:
        """Return a list of problems; empty means the image is safe to flash."""
        problems = []
        if not self.factory_bin.is_file():
            return [f"factory image missing: {self.factory_bin.name}"]

        actual_size = self.factory_bin.stat().st_size
        if self.factory_size_bytes and actual_size != self.factory_size_bytes:
            problems.append(f"size mismatch: manifest {self.factory_size_bytes}, file {actual_size}")

        digest = sha256(self.factory_bin.read_bytes()).hexdigest()
        if digest != self.factory_sha256.lower():
            problems.append("SHA256 mismatch: image does not match manifest")

        desc = read_app_desc(self.factory_bin)
        if desc is None:
            problems.append("cannot parse app descriptor from image")
        else:
            if desc.version != self.version:
                problems.append(f"embedded version {desc.version} != manifest version {self.version}")
            expected_chip = _IMAGE_CHIP_NAMES.get(desc.chip_id) if desc.chip_id is not None else None
            if expected_chip and expected_chip != self.target:
                problems.append(f"image chip {expected_chip} != manifest target {self.target}")
        return problems


@dataclass
class ManualImage:
    """A bare merged .bin selected by hand.

    A merged factory image is self-describing: the v1 image header carries
    the chip id and the app descriptor carries version/project name, so the
    chip dropdown is only needed when the image has no chip id (v0 header,
    e.g. classic ESP32) — see chip_auto.
    """

    factory_bin: Path
    target: str
    directory: Path = field(default_factory=Path)
    project: str = ""
    version: str = ""
    git_commit: str = ""
    build_time: str = ""
    factory_sha256: str = ""
    factory_size_bytes: int = 0
    write_flash_args: list = field(default_factory=list)
    chip_auto: bool = False

    @classmethod
    def from_bin(cls, path: Path, fallback_chip: str = "esp32c6") -> "ManualImage":
        path = Path(path)
        desc = read_app_desc(path) if path.is_file() else None
        chip = _IMAGE_CHIP_NAMES.get(desc.chip_id) if desc and desc.chip_id is not None else None
        return cls(
            factory_bin=path,
            target=chip or fallback_chip,
            project=desc.project if desc and desc.project else _("project_manual_fallback"),
            version=desc.version if desc else "",
            chip_auto=chip is not None,
        )

    def __post_init__(self):
        self.directory = self.factory_bin.parent
        self.factory_size_bytes = self.factory_bin.stat().st_size if self.factory_bin.is_file() else 0

    @property
    def source_label(self) -> str:
        return _("src_manual")

    def verify_artifacts(self) -> list[str]:
        if not self.factory_bin.is_file():
            return [f"firmware file missing: {self.factory_bin.name}"]
        try:
            with open(self.factory_bin, "rb") as f:
                first_byte = f.read(1)
                if not first_byte or first_byte[0] != IMAGE_MAGIC:
                    return [_("err_bad_image")]
        except OSError as e:
            return [str(e)]
        if read_app_desc(self.factory_bin) is None and read_app_desc(self.factory_bin, 0) is not None:
            return [_("err_bare_app")]
        return []


@dataclass
class BuildDirImage:
    """An app image picked inside an ESP-IDF build directory.

    The sibling bootloader / partition-table images and their flash offsets
    are read from flasher_args.json (or the flash_args response file), so
    selecting the bare app .bin just works — no manual merge step.
    """

    app_bin: Path
    directory: Path
    flash_files: list  # [(offset:str, Path)] sorted by offset
    project: str
    target: str
    version: str
    write_flash_args: list = field(default_factory=list)
    chip_auto: bool = True
    git_commit: str = ""
    build_time: str = ""
    factory_sha256: str = ""

    @property
    def factory_bin(self) -> Path:
        """The file the user picked; shown in the firmware path box."""
        return self.app_bin

    @property
    def source_label(self) -> str:
        return _("src_builddir").format(dir=self.directory)

    @property
    def factory_size_bytes(self) -> int:
        return sum(p.stat().st_size for _, p in self.flash_files if p.is_file())

    @classmethod
    def from_app_image(cls, app_path: Path, fallback_chip: str = "esp32c6") -> "BuildDirImage | None":
        """Build a flashable firmware set from a bare app image; None when the
        directory does not contain the boot components it needs."""
        app_path = Path(app_path)
        directory = app_path.parent
        flash_files: list[tuple[str, Path]] = []
        write_flash_args: list[str] = []

        meta = directory / "flasher_args.json"
        if meta.is_file():
            try:
                args = json.loads(meta.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return None
            files = args.get("flash_files")
            if not isinstance(files, dict) or not files:
                return None
            write_flash_args = list(args.get("write_flash_args", []))
            for off, rel in sorted(files.items(), key=lambda kv: int(kv[0], 0)):
                flash_files.append((off, directory / rel))
        else:
            # flash_args response file: "--flash_mode dio" lines plus
            # "<offset> <file>" pairs; params use chip defaults here
            txt = directory / "flash_args"
            if not txt.is_file():
                return None
            for line in txt.read_text(encoding="utf-8", errors="replace").splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[0].lower().startswith("0x"):
                    flash_files.append((parts[0], directory / parts[1]))
            if not flash_files:
                return None

        # Boot components are all required; flashing without one of them
        # leaves a device that cannot start
        if not any(p.name == "bootloader.bin" for _, p in flash_files):
            return None
        if not any("partition" in p.name for _, p in flash_files):
            return None
        if not all(p.is_file() for _, p in flash_files):
            return None

        desc = read_app_desc(app_path, 0)
        if desc is None:
            return None
        chip = _IMAGE_CHIP_NAMES.get(desc.chip_id) if desc.chip_id is not None else None
        return cls(
            app_bin=app_path,
            directory=directory,
            flash_files=flash_files,
            project=desc.project or _("project_builddir_fallback"),
            target=chip or fallback_chip,
            version=desc.version,
            write_flash_args=write_flash_args,
            chip_auto=chip is not None,
        )

    def verify_artifacts(self) -> list[str]:
        missing = [p.name for _, p in self.flash_files if not p.is_file()]
        if missing:
            return [_("err_builddir_missing").format(names=", ".join(missing))]
        return []


def firmware_from_bin(path: Path, fallback_chip: str = "esp32c6") -> ManualImage | BuildDirImage | None:
    """Dispatch a hand-picked .bin.

    Merged factory image -> ManualImage; bare app image inside an IDF build
    directory -> BuildDirImage (bootloader/partition table auto-picked-up);
    bare app image alone -> None (cannot boot, caller should tell the user).
    Anything else falls through to ManualImage which flags invalid images.
    """
    path = Path(path)
    if read_image_header(path).valid and read_app_desc(path) is not None:
        return ManualImage.from_bin(path, fallback_chip)
    if path.is_file() and read_app_desc(path, 0) is not None:
        return BuildDirImage.from_app_image(path, fallback_chip)
    return ManualImage.from_bin(path, fallback_chip)
