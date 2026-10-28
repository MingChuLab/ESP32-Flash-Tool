"""Asset manager, icon provider, and desktop integration for ESP32Flash UI."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget


_CACHED_APP_ICON: Optional[QIcon] = None


def get_assets_dir() -> Path:
    """Return the assets directory inside esp32flash package."""
    base = Path(__file__).resolve().parent
    assets = base / "assets"
    if assets.is_dir():
        return assets
    if hasattr(sys, "_MEIPASS"):
        meipass_assets = Path(sys._MEIPASS) / "esp32flash" / "assets"
        if meipass_assets.is_dir():
            return meipass_assets
    return assets


def get_arrow_icon_path(dark: bool = False) -> str:
    """Return the absolute posix path to the down arrow SVG icon, creating it if missing."""
    filename = "arrow_down_dark.svg" if dark else "arrow_down_light.svg"
    assets_dir = get_assets_dir()
    asset_path = assets_dir / filename
    if not asset_path.exists():
        try:
            assets_dir.mkdir(parents=True, exist_ok=True)
            color = "#8b949e" if dark else "#57606a"
            svg_content = (
                '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="6" viewBox="0 0 10 6">\n'
                f'  <polygon points="0,0 10,0 5,6" fill="{color}"/>\n'
                '</svg>\n'
            )
            asset_path.write_text(svg_content, encoding="utf-8")
        except Exception:
            pass
    return asset_path.as_posix()


def setup_windows_app_id(app_id: str = "ESP32FlashTool.Flasher.1.0") -> None:
    """Set explicit AppUserModelID on Windows so taskbar groups and icon display correctly.

    Without this, Windows groups Python processes under python.exe and displays the generic
    Python snake icon on the taskbar instead of the application window icon.
    """
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass


def apply_windows_taskbar_icon(window: QWidget) -> None:
    """Explicitly send WM_SETICON to the Win32 window HWND to force taskbar icon refresh."""
    if sys.platform == "win32":
        try:
            import ctypes
            hwnd = int(window.winId())
            WM_SETICON = 0x0080
            LR_LOADFROMFILE = 0x00000010
            IMAGE_ICON = 1
            assets_dir = get_assets_dir()
            root_dir = assets_dir.parent.parent
            for p in (assets_dir / "logo_minimal.ico", root_dir / "app.ico"):
                if p.is_file():
                    ico_path = str(p.resolve())
                    h_big = ctypes.windll.user32.LoadImageW(None, ico_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
                    h_small = ctypes.windll.user32.LoadImageW(None, ico_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                    if h_big:
                        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 1, h_big)
                    if h_small:
                        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 0, h_small)
                    break
        except Exception:
            pass


def get_app_icon() -> QIcon:
    """Return the application QIcon loaded with multi-resolution ICO and high-res PNG."""
    global _CACHED_APP_ICON
    if _CACHED_APP_ICON is not None and not _CACHED_APP_ICON.isNull():
        return _CACHED_APP_ICON

    icon = QIcon()
    assets_dir = get_assets_dir()
    root_dir = assets_dir.parent.parent

    # Candidate paths for logo files (prioritizing minimal logo)
    ico_candidates = [
        assets_dir / "logo_minimal.ico",
        root_dir / "app.ico",
    ]
    png_candidates = [
        assets_dir / "logo_minimal.png",
    ]
    if hasattr(sys, "_MEIPASS"):
        ico_candidates = [
            Path(sys._MEIPASS) / "esp32flash" / "assets" / "logo_minimal.ico",
            Path(sys._MEIPASS) / "app.ico",
        ] + ico_candidates
        png_candidates = [
            Path(sys._MEIPASS) / "esp32flash" / "assets" / "logo_minimal.png",
        ] + png_candidates

    for p in ico_candidates:
        if p.is_file():
            icon.addFile(str(p))
            break

    for p in png_candidates:
        if p.is_file():
            icon.addFile(str(p))
            break

    if not icon.isNull():
        _CACHED_APP_ICON = icon
    return icon


def setup_system_tray(window: QWidget) -> Optional[QSystemTrayIcon]:
    """Setup system tray icon for the main window if system tray is supported.

    When minimized or running, the icon sits in the system status bar / notification area.
    Clicking restores and activates the window.
    """
    if not QSystemTrayIcon.isSystemTrayAvailable():
        return None

    try:
        from esp32flash.i18n import _
        tooltip = _("app_title")
        show_text = _("tray_show")
        exit_text = _("tray_exit")
    except Exception:
        tooltip = "ESP32 Flash Tool"
        show_text = "Show Main Window"
        exit_text = "Exit"

    tray = QSystemTrayIcon(window)
    icon = get_app_icon()
    if not icon.isNull():
        tray.setIcon(icon)

    tray.setToolTip(tooltip)

    menu = QMenu(window)
    restore_action = menu.addAction(show_text)

    def _restore():
        window.showNormal()
        window.raise_()
        window.activateWindow()

    restore_action.triggered.connect(_restore)
    menu.addSeparator()
    exit_action = menu.addAction(exit_text)
    exit_action.triggered.connect(QApplication.instance().quit)

    tray.setContextMenu(menu)

    def _on_activated(reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            if window.isMinimized() or not window.isVisible():
                _restore()
            else:
                window.raise_()
                window.activateWindow()

    tray.activated.connect(_on_activated)
    tray.show()
    return tray
