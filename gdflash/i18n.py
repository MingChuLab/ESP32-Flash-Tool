"""Minimal runtime i18n: plain string tables, no Qt Linguist toolchain.

The Qt .ts/.qm workflow (pylupdate6/lrelease, .qm packaging) is
disproportionate for a tool this size, so translations live in a dict and
UI texts are looked up at runtime via _(). Language resolution: a manual
override ("en"/"zh", persisted by the GUI via QSettings) falls back to the
system locale, then English. Add new user-visible strings to BOTH tables,
and prefer adding new keys over reusing ambiguous ones.
"""

STRINGS = {
    "en": {
        "app_title": "ESP32 Firmware Flash Tool",
        "fw_group": "Firmware",
        "fw_placeholder": "No firmware selected (release manifest.json or merged .bin)",
        "browse": "Browse...",
        "chip_hint": "Target chip (choose manually when the image header has no chip id):",
        "info_group": "Firmware Info",
        "row_source": "Source",
        "row_project": "Project",
        "row_version": "Version",
        "row_target": "Target chip",
        "row_compile": "Compiled at",
        "row_idf": "IDF version",
        "row_flash": "Flash params",
        "row_check": "File check",
        "tag_fw": "Firmware",
        "tag_port": "Port",
        "port": "Port:",
        "refresh": "Refresh",
        "language": "Language:",
        "lang_system": "System",
        "boot_hint": ("Tip: if the board has no auto-reset circuit, hold BOOT "
                      "while plugging in USB and release after flashing starts."),
        "ready": "Ready.",
        "flash": "Start Flashing",
        "dlg_fw_title": "Select firmware (release manifest.json or merged .bin)",
        "dlg_fw_filter": "Firmware (manifest.json *.bin);;All files (*)",
        "err_manifest_load_title": "Firmware manifest error",
        "err_manifest_title": "Release manifest invalid",
        "err_incomplete_title": "Firmware incomplete",
        "err_incomplete": (
            "The selected file is only part of the firmware; the device cannot "
            "start if it is flashed alone.\n\n"
            "Please use instead:\n"
            "  - the merged factory image (*_factory.bin) from a release directory\n"
            "  - or a firmware file from a complete build output directory\n\n"
            "Contact the developer if unsure."
        ),
        "step_detect": "Step 1/3: detecting chip ...",
        "step_flash": "Step 2/3: flashing firmware ({baud} bps) ...",
        "step_boot": "Step 3/3: resetting and verifying boot ...",
        "step_done": "Done.",
        "step_failed": "Failed.",
        "detected_chip": "Detected chip: {chip}",
        "retry_baud": "Flash failed, retrying at 115200 ...",
        "err_no_port": "No serial port selected",
        "err_no_fw": "Please select firmware first",
        "err_no_chip": "No chip detected; check cable/driver, or hold BOOT and retry",
        "err_chip_mismatch": ("Chip mismatch: device is {chip}, firmware targets "
                              "{target}; flashing aborted"),
        "err_flash": "Flashing failed at both baud rates; see log",
        "err_no_boot": "Device did not boot, no serial output",
        "ok_verified": "Flashed successfully, device booted, version v{version} verified",
        "err_ver_mismatch": ("Device booted but reports version v{version}, "
                             "expected v{expected}"),
        "ok_no_ver": "Flashed successfully, device booted (no version info to compare)",
        "boot_log_header": "----- boot log -----",
        "log_group": "Log",
        "log_show": "Show Log \u25bc",
        "log_hide": "Hide Log \u25b2",
        "anno_embedded": "(from image)",
        "anno_auto": "(auto-detected)",
        "anno_manual": "(manual)",
        "unknown_version": "unknown (no manifest)",
        "chk_select_first": "Please select firmware first",
        "chk_ok": "Verified",
        # manifest.py
        "src_release": "Release directory {dir}",
        "src_manual": "Manual pick (no manifest)",
        "src_builddir": ("Build directory {dir} "
                         "(bootloader/partition table included automatically)"),
        "err_bad_image": "the selected file is not a valid firmware image (no image header)",
        "err_bare_app": ("this file is only the application part (the bootloader "
                         "needed to start the device is missing) and cannot be flashed alone"),
        "err_builddir_missing": "files missing from the build directory: {names}",
        "project_manual_fallback": "Manually picked firmware",
        "project_builddir_fallback": "Build-directory firmware",
        # flash_tool.py
        "manifest_dir_missing": "--manifest-dir not found: {dir}; pick firmware in the GUI.",
        # system tray
        "tray_show": "Show Main Window",
        "tray_exit": "Exit",
    },
    "zh": {
        "app_title": "ESP32 固件烧录工具",
        "fw_group": "固件",
        "fw_placeholder": "尚未选择固件 (manifest.json 或合并后的 .bin)",
        "browse": "选择固件...",
        "chip_hint": "目标芯片(镜像头无芯片信息时请手动选择):",
        "info_group": "固件信息",
        "row_source": "来源",
        "row_project": "工程",
        "row_version": "版本",
        "row_target": "目标芯片",
        "row_compile": "编译时间",
        "row_idf": "IDF 版本",
        "row_flash": "Flash 参数",
        "row_check": "文件校验",
        "tag_fw": "固件",
        "tag_port": "串口",
        "port": "串口:",
        "refresh": "刷新",
        "language": "语言:",
        "lang_system": "跟随系统",
        "boot_hint": "提示: 若板子无自动复位电路, 请按住 BOOT 键再插入 USB, 烧录完成后再松开。",
        "ready": "就绪。",
        "flash": "开始烧录",
        "dlg_fw_title": "选择固件 (发布目录的 manifest.json, 或合并后的 .bin)",
        "dlg_fw_filter": "固件 (manifest.json *.bin);;所有文件 (*)",
        "err_manifest_load_title": "固件清单错误",
        "err_manifest_title": "发布清单无效",
        "err_incomplete_title": "固件不完整",
        "err_incomplete": (
            "所选文件只是应用固件的一部分, 单独烧录后设备无法启动。\n\n"
            "请改用:\n"
            "· 发布目录中的合并固件 (*_factory.bin)\n"
            "· 或包含 bootloader 的完整编译输出目录中的固件\n\n"
            "如有疑问请联系开发人员。"
        ),
        "step_detect": "第 1/3 步: 检测芯片型号 ...",
        "step_flash": "第 2/3 步: 烧录固件 ({baud} bps) ...",
        "step_boot": "第 3/3 步: 复位并校验启动 ...",
        "step_done": "完成。",
        "step_failed": "失败。",
        "detected_chip": "检测到芯片: {chip}",
        "retry_baud": "烧录失败, 降级到 115200 重试 ...",
        "err_no_port": "未选择串口",
        "err_no_fw": "请先选择固件",
        "err_no_chip": "未检测到芯片, 请检查连线/驱动, 或按住 BOOT 后重试",
        "err_chip_mismatch": "芯片型号不符: 设备是 {chip}, 固件目标是 {target}, 已拒绝烧录",
        "err_flash": "烧录失败 (两种波特率均失败), 详见日志",
        "err_no_boot": "设备未启动, 串口无输出",
        "ok_verified": "烧录成功, 设备已启动, 版本 v{version} 校验通过",
        "err_ver_mismatch": "设备启动了, 但报告版本 v{version}, 期望 v{expected}",
        "ok_no_ver": "烧录成功, 设备已启动 (无版本信息可比对)",
        "boot_log_header": "----- 启动日志 -----",
        "log_group": "日志",
        "log_show": "显示日志 \u25bc",
        "log_hide": "隐藏日志 \u25b2",
        "anno_embedded": "(镜像内嵌)",
        "anno_auto": "(自动识别)",
        "anno_manual": "(手动指定)",
        "unknown_version": "未知(无清单)",
        "chk_select_first": "请先选择固件",
        "chk_ok": "校验通过",
        # manifest.py
        "src_release": "发布目录 {dir}",
        "src_manual": "手动选择(无清单)",
        "src_builddir": "构建目录 {dir}(已自动补齐 bootloader/分区表)",
        "err_bad_image": "所选文件不是有效的固件镜像 (缺少镜像头)",
        "err_bare_app": "该文件只是应用固件(缺少设备启动必需的引导程序), 无法单独烧录",
        "err_builddir_missing": "构建目录文件缺失: {names}",
        "project_manual_fallback": "手动选择的固件",
        "project_builddir_fallback": "构建目录固件",
        # flash_tool.py
        "manifest_dir_missing": "--manifest-dir 不存在: {dir}, 请通过界面手动选择固件。",
        # system tray
        "tray_show": "显示主窗口",
        "tray_exit": "退出",
    },
}

_language = "en"


def set_language(lang: str | None) -> None:
    """Activate a language: "en"/"zh", or None to follow the system locale."""
    global _language
    _language = lang if lang in STRINGS else detect_language()


def detect_language() -> str:
    try:
        from PySide6.QtCore import QLocale
        name = QLocale.system().name().lower()  # e.g. "zh_cn", "en_us"
    except Exception:
        name = ""
    return "zh" if name.startswith("zh") else "en"


def get_language() -> str:
    return _language


def _(key: str) -> str:
    """Look up a UI string; falls back to English, then to the key itself."""
    text = STRINGS[_language].get(key)
    if text is None:
        text = STRINGS["en"].get(key, key)
    return text
