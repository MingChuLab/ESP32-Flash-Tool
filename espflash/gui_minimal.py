"""PySide6 main window: Minimalist clean edition of ESP32 Flash Tool.

Design highlights:
1. Borderless modern card surfaces (eliminating cluttered nested GroupBox outlines).
2. Hero Status Banner: high-contrast health verdict (Verified · Size · Chip) at a glance.
3. Locked 50:50 symmetric parameter columns with fixed 65px label alignment:
   zero horizontal jumping regardless of firmware filename length.
4. Cohesive execution flow: Step -> Progress -> Result -> Primary Button -> Log Toggle.
5. Automatic dark/light theme switching following the system in real-time.
6. Zero distortion (stretch/squeeze) when toggling the collapsible bottom log drawer.
"""

from pathlib import Path
import sys

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPalette, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from serial.tools import list_ports

from espflash.esptool_job import (
    PROGRESS_LINE_PREFIX,
    BootCheckThread,
    FLASH_BAUD_FALLBACK,
    FLASH_BAUD_PRIMARY,
    ProcThread,
    detect_chip_cmd,
    flash_cmd,
    flash_segments,
    normalize_chip_name,
    parse_detected_chip,
)
from espflash.i18n import _, set_language
from espflash.manifest import (
    BuildDirImage,
    FirmwareManifest,
    ManifestError,
    ManualImage,
    describe_image,
    firmware_from_bin,
)
from espflash.assets import apply_windows_taskbar_icon, get_app_icon, get_arrow_icon_path, setup_system_tray

BOOT_CHECK_TIMEOUT_S = 15.0

CHIP_CHOICES = ["esp32", "esp32s2", "esp32s3", "esp32c3", "esp32c6", "esp32h2", "esp32p4"]
ORG_NAME = "ESP32FlashTool"
APP_NAME = "ESP32FlashTool"
SETTINGS_KEY_LANGUAGE = "language"
LANG_ITEMS = (("system", None), ("zh", "中文"), ("en", "English"))


def is_dark_mode() -> bool:
    """Detect whether the current system environment is in dark mode."""
    hints = QGuiApplication.styleHints()
    if hasattr(hints, "colorScheme"):
        scheme = hints.colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return True
        if scheme == Qt.ColorScheme.Light:
            return False
    app = QApplication.instance()
    if app:
        return app.palette().color(QPalette.ColorRole.Window).lightness() < 128
    return False


THEME_PALETTE = {
    "light": {
        "ok": "#1a7f37",
        "err": "#cf222e",
        "warn": "#bf8700",
        "hint": "#8c959f",
        "step_idle": "#57606a",
        "step_active": "#0969da",
        "hero_idle_bg": "#f3f4f6",
        "hero_idle_text": "#57606a",
        "hero_ok_bg": "#dafbe1",
        "hero_ok_text": "#1a7f37",
        "hero_err_bg": "#ffebe9",
        "hero_err_text": "#cf222e",
        "log_cmd": QColor("#6e7781"),
        "log_chip": QColor("#0969da"),
        "log_retry": QColor("#bf8700"),
        "log_boot": QColor("#57606a"),
    },
    "dark": {
        "ok": "#3fb950",
        "err": "#f85149",
        "warn": "#d29922",
        "hint": "#6e7681",
        "step_idle": "#8b949e",
        "step_active": "#58a6ff",
        "hero_idle_bg": "#161b22",
        "hero_idle_text": "#8b949e",
        "hero_ok_bg": "#122619",
        "hero_ok_text": "#3fb950",
        "hero_err_bg": "#2d1619",
        "hero_err_text": "#f85149",
        "log_cmd": QColor("#8b949e"),
        "log_chip": QColor("#58a6ff"),
        "log_retry": QColor("#d29922"),
        "log_boot": QColor("#8b949e"),
    },
}

_ARROW_LIGHT_URL = get_arrow_icon_path(dark=False)
_ARROW_DARK_URL = get_arrow_icon_path(dark=True)

LIGHT_STYLESHEET = """
QWidget {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    font-size: 13px;
    color: #24292f;
    background-color: #f6f8fa;
}

QLabel#HeaderTitle {
    font-size: 17px;
    font-weight: 700;
    color: #1f2328;
}

QLabel#SubtleLabel {
    color: #57606a;
    font-weight: 500;
}

QLabel#PrefixBadge {
    background-color: transparent;
    border: none;
    color: #57606a;
    font-size: 13px;
    font-weight: 500;
}

QLabel#HintLabel {
    color: #8c959f;
    font-size: 12px;
}

/* Modern Card Surface without harsh GroupBox borders */
QFrame.CardFrame {
    background-color: #ffffff;
    border: 1px solid #e1e4e8;
    border-radius: 10px;
}

QLabel#HeroBanner {
    font-size: 13px;
    font-weight: 600;
    padding: 8px 12px;
    border-radius: 6px;
}

QLineEdit, QComboBox {
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 6px 10px;
    background-color: #ffffff;
    color: #24292f;
    selection-background-color: #0969da;
}

QComboBox {
    padding-right: 24px;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border: none;
    background: transparent;
}

QComboBox::down-arrow {
    image: url(@ARROW_URL@);
    width: 10px;
    height: 6px;
    margin-right: 6px;
}


QLineEdit:focus, QComboBox:focus {
    border: 1px solid #0969da;
}

QLineEdit:read-only {
    background-color: #f6f8fa;
    color: #57606a;
}

QComboBox QAbstractItemView {
    border: 1px solid #d0d7de;
    border-radius: 6px;
    background-color: #ffffff;
    color: #24292f;
    padding: 4px;
    selection-background-color: #0969da;
    selection-color: #ffffff;
}

QPushButton {
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 6px 14px;
    background-color: #ffffff;
    color: #24292f;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #f3f4f6;
    border-color: #1b1f2426;
}

QPushButton:pressed {
    background-color: #ebecf0;
}

QPushButton#PrimaryButton {
    background-color: #0969da;
    color: #ffffff;
    font-size: 16px;
    font-weight: 600;
    border: 1px solid #0969da;
    border-radius: 8px;
    padding: 11px 24px;
}

QPushButton#PrimaryButton:hover {
    background-color: #0860ca;
    border-color: #0860ca;
}

QPushButton#PrimaryButton:pressed {
    background-color: #0757ba;
    border-color: #0757ba;
}

QPushButton#PrimaryButton:disabled {
    background-color: #8c959f;
    border-color: #8c959f;
    color: #ffffff;
}

QPushButton#LogToggleBtn {
    border: none;
    background: transparent;
    font-size: 12px;
    color: #57606a;
    font-weight: 500;
    padding: 4px 8px;
}

QPushButton#LogToggleBtn:hover {
    color: #0969da;
    text-decoration: underline;
}

QProgressBar {
    border: 1px solid #e1e4e8;
    border-radius: 6px;
    text-align: center;
    background-color: #ffffff;
    height: 12px;
    font-size: 11px;
    font-weight: bold;
    color: #24292f;
}

QProgressBar::chunk {
    background-color: #2da44e;
    border-radius: 5px;
}

QPlainTextEdit#LogView {
    border: 1px solid #e1e4e8;
    border-radius: 8px;
    background-color: #ffffff;
    color: #24292f;
    padding: 8px;
}
""".replace("@ARROW_URL@", _ARROW_LIGHT_URL)

DARK_STYLESHEET = """
QWidget {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    font-size: 13px;
    color: #c9d1d9;
    background-color: #0d1117;
}

QLabel#HeaderTitle {
    font-size: 17px;
    font-weight: 700;
    color: #f0f6fc;
}

QLabel#SubtleLabel {
    color: #8b949e;
    font-weight: 500;
}

QLabel#PrefixBadge {
    background-color: transparent;
    border: none;
    color: #8b949e;
    font-size: 13px;
    font-weight: 500;
}

QLabel#HintLabel {
    color: #6e7681;
    font-size: 12px;
}

/* Modern Card Surface without harsh GroupBox borders */
QFrame.CardFrame {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
}

QLabel#HeroBanner {
    font-size: 13px;
    font-weight: 600;
    padding: 8px 12px;
    border-radius: 6px;
}

QLineEdit, QComboBox {
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 10px;
    background-color: #0d1117;
    color: #c9d1d9;
    selection-background-color: #1f6feb;
}

QComboBox {
    padding-right: 24px;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border: none;
    background: transparent;
}

QComboBox::down-arrow {
    image: url(@ARROW_URL@);
    width: 10px;
    height: 6px;
    margin-right: 6px;
}


QLineEdit:focus, QComboBox:focus {
    border: 1px solid #58a6ff;
}

QLineEdit:read-only {
    background-color: #161b22;
    color: #8b949e;
}

QComboBox QAbstractItemView {
    border: 1px solid #30363d;
    border-radius: 6px;
    background-color: #161b22;
    color: #c9d1d9;
    padding: 4px;
    selection-background-color: #1f6feb;
    selection-color: #ffffff;
}

QPushButton {
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 14px;
    background-color: #21262d;
    color: #c9d1d9;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #30363d;
    border-color: #8b949e;
}

QPushButton:pressed {
    background-color: #282e33;
}

QPushButton#PrimaryButton {
    background-color: #1f6feb;
    color: #ffffff;
    font-size: 16px;
    font-weight: 600;
    border: 1px solid #1f6feb;
    border-radius: 8px;
    padding: 11px 24px;
}

QPushButton#PrimaryButton:hover {
    background-color: #388bfd;
    border-color: #388bfd;
}

QPushButton#PrimaryButton:pressed {
    background-color: #1a56db;
    border-color: #1a56db;
}

QPushButton#PrimaryButton:disabled {
    background-color: #30363d;
    border-color: #30363d;
    color: #484f58;
}

QPushButton#LogToggleBtn {
    border: none;
    background: transparent;
    font-size: 12px;
    color: #8b949e;
    font-weight: 500;
    padding: 4px 8px;
}

QPushButton#LogToggleBtn:hover {
    color: #58a6ff;
    text-decoration: underline;
}

QProgressBar {
    border: 1px solid #21262d;
    border-radius: 6px;
    text-align: center;
    background-color: #0d1117;
    height: 12px;
    font-size: 11px;
    font-weight: bold;
    color: #c9d1d9;
}

QProgressBar::chunk {
    background-color: #238636;
    border-radius: 5px;
}

QPlainTextEdit#LogView {
    border: 1px solid #21262d;
    border-radius: 8px;
    background-color: #0d1117;
    color: #c9d1d9;
    padding: 8px;
}
""".replace("@ARROW_URL@", _ARROW_DARK_URL)


class MainWindow(QWidget):
    def __init__(self, manifest: FirmwareManifest | ManualImage | BuildDirImage | None = None):
        super().__init__()
        self.manifest: FirmwareManifest | ManualImage | BuildDirImage | None = None
        self._proc: ProcThread | None = None
        self._boot_thread: BootCheckThread | None = None
        self._flash_baud = FLASH_BAUD_PRIMARY
        self._settings = QSettings(ORG_NAME, APP_NAME)
        self._step_active = False
        self.setWindowTitle(_("app_title"))
        icon = get_app_icon()
        if not icon.isNull():
            self.setWindowIcon(icon)
        apply_windows_taskbar_icon(self)
        self._tray_icon = setup_system_tray(self)

        self.setMinimumWidth(720)
        self._build_ui()
        self._apply_theme()

        # Connect system color scheme listener for live dynamic theme switching
        hints = QGuiApplication.styleHints()
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(self._on_theme_changed)

        self._refresh_ports()
        if manifest is not None:
            self._apply_manifest(manifest)
        else:
            self._show_no_firmware()

    @property
    def _theme(self) -> dict:
        return THEME_PALETTE["dark" if is_dark_mode() else "light"]

    def _apply_theme(self):
        """Apply light or dark theme stylesheet and dynamic semantic colors."""
        dark = is_dark_mode()
        self.setStyleSheet(DARK_STYLESHEET if dark else LIGHT_STYLESHEET)
        pal = self._theme

        if hasattr(self, "step_label"):
            color = pal["step_active"] if self._step_active else pal["step_idle"]
            self.step_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {color};")

        if hasattr(self, "result_label") and self.result_label.text():
            ok = self.result_label.text().startswith("✅")
            color = pal["ok"] if ok else pal["err"]
            self.result_label.setStyleSheet(f"color: {color}; font-size: 15px; font-weight: bold;")

        if hasattr(self, "artifact_label"):
            if self.manifest is not None:
                self._check_artifacts()
            else:
                self.artifact_label.setStyleSheet(
                    f"background-color: {pal['hero_idle_bg']}; color: {pal['hero_idle_text']};"
                )

        if hasattr(self, "info_version"):
            if self.manifest is not None and getattr(self.manifest, "version", None):
                self.info_version.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {pal['step_active']};")
            else:
                self.info_version.setStyleSheet(f"color: {pal['hint']};")
        if hasattr(self, "info_target"):
            if self.manifest is not None:
                self.info_target.setStyleSheet("font-weight: 600; font-family: ui-monospace, SFMono-Regular, monospace;")
            else:
                self.info_target.setStyleSheet(f"color: {pal['hint']};")
        if hasattr(self, "info_project") and self.manifest is None:
            for widget in [self.info_project, self.info_compile, self.info_idf, self.info_flash]:
                widget.setStyleSheet(f"color: {pal['hint']};")

    def _on_theme_changed(self, _=None):
        self._apply_theme()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        # 1. Header Row (Minimalist Title on left, Language Switcher on right)
        header_row = QHBoxLayout()
        header_row.setContentsMargins(2, 0, 8, 0)
        self.header_logo = QLabel()
        self.header_logo.setFixedSize(26, 26)
        app_icon = get_app_icon()
        if not app_icon.isNull():
            self.header_logo.setPixmap(app_icon.pixmap(26, 26))
            self.header_logo.setScaledContents(True)
        header_row.addWidget(self.header_logo)
        header_row.addSpacing(8)
        self.header_title = QLabel(_("app_title"))
        self.header_title.setObjectName("HeaderTitle")
        header_row.addWidget(self.header_title, stretch=1)

        lang_box = QHBoxLayout()
        lang_box.setSpacing(8)
        self.lang_label = QLabel(_("language"))
        self.lang_label.setObjectName("SubtleLabel")
        lang_box.addWidget(self.lang_label)
        self.lang_combo = QComboBox()
        self.lang_combo.setObjectName("LangCombo")
        self.lang_combo.setFixedWidth(100)
        self._reload_lang_combo(self._settings.value(SETTINGS_KEY_LANGUAGE, "system"))
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_box.addWidget(self.lang_combo)
        header_row.addLayout(lang_box)
        header_row.addSpacing(6)
        root.addLayout(header_row)

        # 2. Configuration Card (Clean Flat Card: Firmware + Port Inputs)
        self.fw_card = QFrame()
        self.fw_card.setProperty("class", "CardFrame")
        self.fw_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        fw_col = QVBoxLayout(self.fw_card)
        fw_col.setContentsMargins(14, 12, 14, 12)
        fw_col.setSpacing(10)

        # Row 1: Firmware picker
        fw_row = QHBoxLayout()
        fw_row.setSpacing(8)
        self.fw_label = QLabel(_("tag_fw"))
        self.fw_label.setObjectName("PrefixBadge")
        self.fw_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        fw_row.addWidget(self.fw_label)

        self.fw_path = QLineEdit()
        self.fw_path.setReadOnly(True)
        self.fw_path.setPlaceholderText(_("fw_placeholder"))
        fw_row.addWidget(self.fw_path, stretch=1)
        self.pick_btn = QPushButton(_("browse"))
        self.pick_btn.setFixedWidth(100)
        self.pick_btn.clicked.connect(self._choose_firmware)
        fw_row.addWidget(self.pick_btn)
        fw_col.addLayout(fw_row)

        # Row 2: Port & Chip selector
        port_row = QHBoxLayout()
        port_row.setSpacing(8)
        self.port_label = QLabel(_("tag_port"))
        self.port_label.setObjectName("PrefixBadge")
        self.port_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        port_row.addWidget(self.port_label)
        self._update_label_widths()

        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(240)
        port_row.addWidget(self.port_combo, stretch=1)
        self.refresh_btn = QPushButton(_("refresh"))
        self.refresh_btn.setFixedWidth(100)
        self.refresh_btn.clicked.connect(self._refresh_ports)
        port_row.addWidget(self.refresh_btn)

        self.chip_hint = QLabel()
        self.chip_combo = QComboBox()
        self.chip_combo.addItems(CHIP_CHOICES)
        self.chip_combo.setCurrentText("esp32c6")
        self.chip_combo.currentTextChanged.connect(self._on_chip_picked)
        port_row.addWidget(self.chip_hint)
        port_row.addWidget(self.chip_combo)
        self.chip_hint.setVisible(False)
        self.chip_combo.setVisible(False)

        fw_col.addLayout(port_row)
        root.addWidget(self.fw_card)

        # 3. Firmware Hero Summary Card (Hero Banner + 50:50 Symmetric Meta Grid)
        self.info_card = QFrame()
        self.info_card.setProperty("class", "CardFrame")
        self.info_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        info_col = QVBoxLayout(self.info_card)
        info_col.setContentsMargins(14, 12, 14, 12)
        info_col.setSpacing(10)

        # Hero Status Banner: high-contrast health verdict
        self.artifact_label = QLabel(_("chk_select_first"))
        self.artifact_label.setObjectName("HeroBanner")
        self.artifact_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_col.addWidget(self.artifact_label)

        self.info_source = QLabel("-")
        self.info_project = QLabel("-")
        self.info_version = QLabel("-")
        self.info_target = QLabel("-")
        self.info_compile = QLabel("-")
        self.info_idf = QLabel("-")
        self.info_flash = QLabel("-")

        self.row_labels = {}
        cols_row = QHBoxLayout()
        cols_row.setSpacing(24)

        # Left Column (Project, Version, Target Chip)
        left_w = QWidget()
        left_form = QFormLayout(left_w)
        left_form.setContentsMargins(0, 0, 0, 0)
        left_form.setHorizontalSpacing(10)
        left_form.setVerticalSpacing(6)

        left_items = [
            ("row_project", self.info_project),
            ("row_version", self.info_version),
            ("row_target", self.info_target),
        ]
        self.left_labels = []
        for key, value_widget in left_items:
            value_widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            lbl = QLabel(_(key))
            lbl.setObjectName("SubtleLabel")
            self.row_labels[key] = lbl
            self.left_labels.append(lbl)
            left_form.addRow(lbl, value_widget)

        # Right Column (Flash Params, IDF Version, Compiled At)
        right_w = QWidget()
        right_form = QFormLayout(right_w)
        right_form.setContentsMargins(0, 0, 0, 0)
        right_form.setHorizontalSpacing(10)
        right_form.setVerticalSpacing(6)

        right_items = [
            ("row_flash", self.info_flash),
            ("row_idf", self.info_idf),
            ("row_compile", self.info_compile),
        ]
        self.right_labels = []
        for key, value_widget in right_items:
            value_widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            lbl = QLabel(_(key))
            lbl.setObjectName("SubtleLabel")
            self.row_labels[key] = lbl
            self.right_labels.append(lbl)
            right_form.addRow(lbl, value_widget)

        cols_row.addWidget(left_w, stretch=1)
        cols_row.addWidget(right_w, stretch=1)
        info_col.addLayout(cols_row)
        root.addWidget(self.info_card)

        # 4. Action & Execution Center
        exec_box = QVBoxLayout()
        exec_box.setSpacing(8)

        self.step_label = QLabel(_("ready"))
        exec_box.addWidget(self.step_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        exec_box.addWidget(self.progress)

        self.result_label = QLabel("")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        exec_box.addWidget(self.result_label)

        self.flash_btn = QPushButton(_("flash"))
        self.flash_btn.setObjectName("PrimaryButton")
        self.flash_btn.setMinimumHeight(48)
        self.flash_btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.flash_btn.clicked.connect(self._start_pipeline)
        exec_box.addWidget(self.flash_btn)

        # Footer row: boot tip on the left, log toggle on the right
        footer_row = QHBoxLayout()
        self.hint_label = QLabel(_("boot_hint"))
        self.hint_label.setObjectName("HintLabel")
        footer_row.addWidget(self.hint_label, stretch=1)

        self.log_toggle = QPushButton()
        self.log_toggle.setObjectName("LogToggleBtn")
        self.log_toggle.setCheckable(True)
        self.log_toggle.toggled.connect(self._on_log_toggled)
        footer_row.addWidget(self.log_toggle)
        exec_box.addLayout(footer_row)

        root.addLayout(exec_box)

        # 5. Collapsible Log Drawer (Bottom-most auxiliary console)
        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("LogView")
        self.log_view.setReadOnly(True)
        font = QFont("Monospace")
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        self.log_view.setFont(font)

        self.log_card = QFrame()
        self.log_card.setProperty("class", "CardFrame")
        log_col = QVBoxLayout(self.log_card)
        log_col.setContentsMargins(10, 10, 10, 10)
        log_col.addWidget(self.log_view)
        root.addWidget(self.log_card, stretch=1)

        self._expanded_height: int | None = None
        self.log_toggle.setChecked(self._settings.value("log_visible", False, type=bool))
        self._apply_log_visible(self.log_toggle.isChecked())
        self.resize(740, self.sizeHint().height())

    def _apply_log_visible(self, visible: bool):
        """Show/hide the log area and smoothly resize without distorting other widgets."""
        if not visible and self.isVisible() and self.log_card.isVisible():
            self._expanded_height = self.height()
        self.log_card.setVisible(visible)
        self.log_toggle.setText(_("log_hide") if visible else _("log_show"))
        if visible:
            target_h = self._expanded_height if (self._expanded_height and self._expanded_height > 500) else 720
            self.resize(self.width(), target_h)
        else:
            self.layout().activate()
            target_h = self.layout().sizeHint().height()
            self.resize(self.width(), target_h)

    def _on_log_toggled(self, checked: bool):
        self._apply_log_visible(checked)
        self._settings.setValue("log_visible", checked)

    def _show_log(self):
        """Auto-expand the log (e.g. on failure) without persisting the change."""
        if not self.log_toggle.isChecked():
            self.log_toggle.blockSignals(True)
            self.log_toggle.setChecked(True)
            self._apply_log_visible(True)
            self.log_toggle.blockSignals(False)

    def _reload_lang_combo(self, current: str):
        """(Re)fill the language combo, keeping `current` selected."""
        self.lang_combo.blockSignals(True)
        self.lang_combo.clear()
        for key, fixed_label in LANG_ITEMS:
            self.lang_combo.addItem(fixed_label or _("lang_system"), key)
        index = self.lang_combo.findData(current)
        self.lang_combo.setCurrentIndex(index if index >= 0 else 0)
        self.lang_combo.blockSignals(False)

    def _update_label_widths(self):
        """Fit label widths tightly to current text to eliminate excess gap and prevent clipping."""
        if hasattr(self, "fw_label") and hasattr(self, "port_label"):
            fm = self.fw_label.fontMetrics()
            label_w = max(fm.horizontalAdvance(self.fw_label.text()),
                          fm.horizontalAdvance(self.port_label.text())) + 2
            self.fw_label.setFixedWidth(label_w)
            self.port_label.setFixedWidth(label_w)

        if hasattr(self, "left_labels") and self.left_labels:
            fm_left = self.left_labels[0].fontMetrics()
            left_w = max(fm_left.horizontalAdvance(lbl.text()) for lbl in self.left_labels) + 2
            for lbl in self.left_labels:
                lbl.setFixedWidth(left_w)

        if hasattr(self, "right_labels") and self.right_labels:
            fm_right = self.right_labels[0].fontMetrics()
            right_w = max(fm_right.horizontalAdvance(lbl.text()) for lbl in self.right_labels) + 2
            for lbl in self.right_labels:
                lbl.setFixedWidth(right_w)

    def _retranslate_static(self):
        """Re-apply texts that do not depend on the selected firmware."""
        self.setWindowTitle(_("app_title"))
        self.header_title.setText(_("app_title"))
        self.fw_path.setPlaceholderText(_("fw_placeholder"))
        self.pick_btn.setText(_("browse"))
        self.chip_hint.setText(_("chip_hint"))
        for key, label in self.row_labels.items():
            label.setText(_(key))
        self.fw_label.setText(_("tag_fw"))
        self.port_label.setText(_("tag_port"))
        self._update_label_widths()
        self.refresh_btn.setText(_("refresh"))
        self.lang_label.setText(_("language"))
        self._reload_lang_combo(self.lang_combo.currentData() or "system")
        self.hint_label.setText(_("boot_hint"))
        self.flash_btn.setText(_("flash"))
        self.log_toggle.setText(_("log_hide") if self.log_toggle.isChecked() else _("log_show"))
        if hasattr(self, "_tray_icon") and self._tray_icon:
            self._tray_icon.setToolTip(_("app_title"))

    def closeEvent(self, event):
        if hasattr(self, "_tray_icon") and self._tray_icon:
            self._tray_icon.hide()
        super().closeEvent(event)

    def _on_language_changed(self, index: int):
        key = self.lang_combo.itemData(index)
        self._settings.setValue(SETTINGS_KEY_LANGUAGE, key)
        set_language(None if key == "system" else key)
        self._retranslate_static()
        self._set_step(_("ready"), active=False)
        if self.manifest is not None:
            self._apply_manifest(self.manifest)
        else:
            self._show_no_firmware()

    # ------------------------------------------------------- firmware load
    def _on_chip_picked(self, chip: str):
        if isinstance(self.manifest, ManualImage) and not self.manifest.chip_auto:
            self.manifest.target = chip
            self.info_target.setText(chip + _("anno_manual"))

    def _choose_firmware(self):
        start = str(self.manifest.directory) if self.manifest else str(Path.home())
        chosen = QFileDialog.getOpenFileName(
            self, _("dlg_fw_title"), start, _("dlg_fw_filter"))[0]
        if chosen:
            self._load_firmware_path(Path(chosen))

    def _load_firmware_path(self, path: Path):
        """Single entry: dispatch on file type — manifest.json -> release dir;
        a .bin -> merged image, IDF build-directory app image, or reject."""
        if path.suffix.lower() == ".json":
            try:
                manifest = FirmwareManifest.load(path.parent)
            except ManifestError as e:
                QMessageBox.warning(self, _("err_manifest_title"), str(e))
                return
            self._apply_manifest(manifest)
            return
        fw = firmware_from_bin(path, fallback_chip=self.chip_combo.currentText())
        if fw is None:
            QMessageBox.warning(self, _("err_incomplete_title"), _("err_incomplete"))
            return
        self._apply_manifest(fw)

    def _apply_manifest(self, manifest: FirmwareManifest | ManualImage | BuildDirImage):
        self.manifest = manifest
        is_manual = isinstance(manifest, ManualImage)
        self.fw_path.setText(str(manifest.factory_bin))
        self.info_source.setText(manifest.source_label)
        self.info_source.setToolTip(str(manifest.directory))

        header, desc = describe_image(manifest.factory_bin)
        project = (desc.project if desc and desc.project else "") or manifest.project
        self.info_project.setText(project if project else "-")
        self.info_project.setToolTip(project if project else "")

        version = (desc.version if desc and desc.version else "") or manifest.version
        if version:
            self.info_version.setText(f"v{version}" + (_("anno_embedded")
                                                         if desc and desc.version else ""))
        else:
            self.info_version.setText(_("unknown_version"))

        self.info_target.setText(manifest.target + (_("anno_auto") if manifest.chip_auto
                                                    else _("anno_manual") if is_manual else ""))

        compile_time = desc.compile_time if desc and desc.compile_time else ""
        if isinstance(manifest, FirmwareManifest):
            self.info_compile.setText(compile_time or manifest.build_time or "-")
        else:
            self.info_compile.setText(compile_time or "-")
        self.info_idf.setText(desc.idf_ver if desc and desc.idf_ver else "-")
        if header:
            self.info_flash.setText(f"{header.flash_mode} / {header.flash_size} / {header.flash_freq}")
        else:
            self.info_flash.setText("-")

        title = _("app_title")
        if project and version:
            title = f"{title} — {project} v{version}"
        self.setWindowTitle(title)

        need_chip_picker = is_manual and not manifest.chip_auto
        self.chip_hint.setVisible(need_chip_picker)
        self.chip_combo.setVisible(need_chip_picker)
        if need_chip_picker:
            self.chip_combo.setCurrentText(manifest.target)

        pal = self._theme
        for widget in [self.info_project, self.info_compile, self.info_idf, self.info_flash]:
            widget.setStyleSheet("")
        if version:
            self.info_version.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {pal['step_active']};")
        else:
            self.info_version.setStyleSheet(f"color: {pal['hint']};")
        self.info_target.setStyleSheet("font-weight: 600; font-family: ui-monospace, SFMono-Regular, monospace;")

        self._check_artifacts()
        self._update_flash_enabled()

    def _show_no_firmware(self):
        self.fw_path.setText("")
        self.artifact_label.setText(_("chk_select_first"))
        self.artifact_label.setToolTip("")
        self.info_project.setText("-")
        self.info_version.setText("-")
        self.info_target.setText("-")
        self.info_compile.setText("-")
        self.info_idf.setText("-")
        self.info_flash.setText("-")
        self.info_project.setToolTip("")
        self.info_source.setToolTip("")
        pal = self._theme
        for widget in [self.info_project, self.info_version, self.info_target,
                       self.info_compile, self.info_idf, self.info_flash]:
            widget.setStyleSheet(f"color: {pal['hint']};")
        self.artifact_label.setStyleSheet(
            f"background-color: {pal['hero_idle_bg']}; color: {pal['hero_idle_text']};"
        )
        self.flash_btn.setEnabled(False)

    def _refresh_ports(self):
        current = self.port_combo.currentText()
        self.port_combo.clear()
        ports = [p.device for p in list_ports.comports()]
        self.port_combo.addItems(ports)
        if current in ports:
            self.port_combo.setCurrentText(current)
        self._update_flash_enabled()

    def _update_flash_enabled(self):
        self.flash_btn.setEnabled(bool(self.port_combo.currentText()) and self.manifest is not None)

    def _check_artifacts(self):
        assert self.manifest is not None
        problems = self.manifest.verify_artifacts()
        pal = self._theme
        if problems:
            self.artifact_label.setText("❌ " + "; ".join(problems))
            self.artifact_label.setStyleSheet(
                f"background-color: {pal['hero_err_bg']}; color: {pal['hero_err_text']};"
            )
        else:
            detail = f" ({self.manifest.factory_size_bytes / 1024:.0f} KB)" if self.manifest.factory_size_bytes else ""
            summary_chip = f" · {self.manifest.target.upper()}" if self.manifest.target else ""
            self.artifact_label.setText(f"✅ {_('chk_ok')}{detail}{summary_chip}")
            self.artifact_label.setToolTip(self.manifest.factory_bin.name)
            self.artifact_label.setStyleSheet(
                f"background-color: {pal['hero_ok_bg']}; color: {pal['hero_ok_text']};"
            )

    # ------------------------------------------------------------- logging
    def _log(self, text: str, color: QColor | None = None):
        cursor = self.log_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if color is not None:
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            cursor.mergeCharFormat(fmt)
        cursor.insertText(text + "\n")
        self.log_view.ensureCursorVisible()
        if color is not None:
            cursor.setCharFormat(QTextCharFormat())
            self.log_view.setTextCursor(cursor)

    def _set_step(self, text: str, active: bool = True):
        self._step_active = active
        self.step_label.setText(text)
        pal = self._theme
        color = pal["step_active"] if active else pal["step_idle"]
        self.step_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {color};")

    def _set_result(self, ok: bool, text: str):
        color = self._theme["ok"] if ok else self._theme["err"]
        self.result_label.setText(("✅ " if ok else "❌ ") + text)
        self.result_label.setStyleSheet(f"color: {color}; font-size: 15px; font-weight: bold;")

    # ------------------------------------------------------------ pipeline
    def _start_pipeline(self):
        port = self.port_combo.currentText()
        if not port:
            self._set_result(False, _("err_no_port"))
            return
        if self.manifest is None:
            self._set_result(False, _("err_no_fw"))
            return
        self.flash_btn.setEnabled(False)
        self.result_label.clear()
        self.log_view.clear()
        self.progress.setValue(0)
        self._flash_baud = FLASH_BAUD_PRIMARY
        self._run_chip_detect(port)

    def _run_chip_detect(self, port: str):
        self._set_step(_("step_detect"))
        self.progress.setValue(2)
        self._log(f"$ {' '.join(detect_chip_cmd(port))}", self._theme["log_cmd"])
        self._proc = ProcThread(detect_chip_cmd(port), self)
        self._proc.line.connect(lambda s: self._log(s, self._theme["log_cmd"]))
        self._proc.done.connect(lambda ok: self._on_chip_detected(port, ok))
        self._proc.start()

    def _on_chip_detected(self, port: str, ok: bool):
        chip = parse_detected_chip(self._proc.output) if ok else None
        if chip is None:
            self._fail(_("err_no_chip"))
            return
        self.progress.setValue(5)
        self._log(_("detected_chip").format(chip=chip), self._theme["log_chip"])
        if normalize_chip_name(chip) != normalize_chip_name(self.manifest.target):
            self._fail(_("err_chip_mismatch").format(chip=chip, target=self.manifest.target))
            return
        self._run_flash(port)

    def _run_flash(self, port: str):
        self._set_step(_("step_flash").format(baud=self._flash_baud))
        flash_files = getattr(self.manifest, "flash_files", None) \
            or [("0x0", self.manifest.factory_bin)]
        cmd = flash_cmd(port, self.manifest.target, self._flash_baud, flash_files,
                        write_flash_args=self.manifest.write_flash_args)
        self._log(f"$ {' '.join(cmd)}")
        self._proc = ProcThread(cmd, self, segments=flash_segments(flash_files))
        self._proc.line.connect(self._log_flash_line)
        self._proc.progress.connect(self._on_flash_progress)
        self._proc.done.connect(lambda ok: self._on_flashed(port, ok))
        self._proc.start()

    def _on_flash_progress(self, val: int):
        # Map esptool 0..100% to weighted 5..85% (80% of total pipeline)
        self.progress.setValue(5 + int(val * 0.8))

    def _log_flash_line(self, text: str):
        if PROGRESS_LINE_PREFIX in text:
            return
        self._log(text)

    def _on_flashed(self, port: str, ok: bool):
        if not ok:
            if self._flash_baud != FLASH_BAUD_FALLBACK:
                self._flash_baud = FLASH_BAUD_FALLBACK
                self._log(_("retry_baud"), self._theme["log_retry"])
                self.progress.setValue(5)
                self._run_flash(port)
                return
            self._fail(_("err_flash"))
            return
        self.progress.setValue(85)
        self._set_step(_("step_boot"))
        if hasattr(self, "_boot_timer") and self._boot_timer.isActive():
            self._boot_timer.stop()
        self._boot_timer = QTimer(self)
        self._boot_timer.setInterval(1000)
        self._boot_timer.timeout.connect(self._on_boot_tick)
        self._boot_timer.start()
        self._boot_thread = BootCheckThread(port, BOOT_CHECK_TIMEOUT_S,
                                            self.manifest.version, self)
        self._boot_thread.done.connect(self._on_boot_checked)
        self._boot_thread.start()

    def _on_boot_tick(self):
        if self.progress.value() < 95:
            self.progress.setValue(self.progress.value() + 1)

    def _on_boot_checked(self, result):
        if hasattr(self, "_boot_timer") and self._boot_timer.isActive():
            self._boot_timer.stop()
        self._log(_("boot_log_header"))
        for line in result.log.splitlines():
            self._log(line, self._theme["log_boot"])
        if not result.booted:
            self._fail(_("err_no_boot"))
            return
        expected = self.manifest.version
        if expected and result.version_matches(expected):
            self.progress.setValue(100)
            self._set_result(True, _("ok_verified").format(version=expected))
        elif expected and result.version is not None:
            self._fail(_("err_ver_mismatch").format(version=result.version, expected=expected))
        else:
            self.progress.setValue(100)
            self._set_result(True, _("ok_no_ver"))
        self._set_step(_("step_done"), active=False)
        self.flash_btn.setEnabled(True)

    def _fail(self, reason: str):
        if hasattr(self, "_boot_timer") and self._boot_timer.isActive():
            self._boot_timer.stop()
        self._show_log()
        self._set_result(False, reason)
        self._set_step(_("step_failed"), active=False)
        self.flash_btn.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    set_language(QSettings(ORG_NAME, APP_NAME).value(SETTINGS_KEY_LANGUAGE))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

