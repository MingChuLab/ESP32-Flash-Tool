# ESP32 Flash Tool（ESP32 固件烧录工具）

**[English](README.md) | 简体中文**

面向测试/产线人员的通用 ESP32 一键烧录工具。**无需安装 ESP-IDF、无需 Python 开发环境**，
插上设备、选择固件和串口、点击一个按钮即可完成烧录，并自动确认烧录结果。

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
![Platform: Windows / Linux / macOS](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)

<p align="center">
  <img src="docs/images/screenshot_zh.png" alt="ESP32 固件烧录工具" width="720">
</p>

## 下载

Windows 测试机请直接到 [Releases](../../releases) 下载打包好的 `ESP32FlashTool.zip`
（解压整个文件夹运行，无需安装任何东西）。源码运行见下文。

## 功能特性

- **通用工具**：不绑定具体产品，标题与固件信息随所选固件变化；
- **单一固件入口**：一个"选择固件..."按钮，按所选内容自动分流——
  - 选中发布目录的 `manifest.json` → 完整防呆（文件存在性、尺寸、SHA256、内嵌版本号）；
  - 选中 IDF 构建目录里的裸 app `.bin`（如 `build/xxx.bin`）→ 自动从同目录
    `flasher_args.json`/`flash_args` 补齐 bootloader 与分区表，按各自偏移一次写入，
    无需手工合并；
  - 选中合并后的 `.bin` → 自动从镜像头识别芯片/版本/工程名（v0 头无芯片信息时
    才需手动选芯片），并校验镜像头合法性；
  - 选中孤立的裸 app 镜像（缺引导程序，烧后无法启动）→ 用人话提示拒绝；
- **固件信息面板**：工程名、版本、编译时间、IDF 版本、Flash 模式/容量/频率
  （频率编码按芯片查表，与 esptool 一致），全部直接解析自固件文件；
- **中英双语界面**：默认跟随系统语言，界面内可随时切换（Language），选择持久化；
- **一键烧录**：自动检测芯片型号 → 烧录 → 复位校验，全程图形界面；
- **芯片防呆**：烧录前识别实际芯片，与固件目标芯片不符时拒绝烧录；
- **结果确认**：烧录后自动复位设备并抓取启动日志，固件版本号与清单一致
  才显示"成功"；
- **单一进度显示**：写入进度只显示在窗口进度条上，日志区保持干净；
- **波特率自适应**：默认 921600，失败自动降级 115200 重试；
- **日志留档**：完整烧录过程与设备启动日志显示在窗口中，可复制保存。
  日志区默认折叠保持界面干净，失败时自动展开以便留证，手动开关会被记住；

## 界面流程

```
选择固件(目录或bin) ──► 选择串口 ──► [开始烧录]
   第 1 步: 检测芯片型号
   第 2 步: 烧录固件（窗口进度条）
   第 3 步: 复位并校验启动
✅ 烧录成功, 设备已启动, 版本 vX.Y.Z 校验通过
```

## 环境要求（源码运行）

| 项目 | 说明 |
| :--- | :--- |
| 操作系统 | Windows 10/11（推荐）、Linux、macOS |
| Python | 3.10+（仅源码运行时；正式分发为独立 exe，测试人员无需安装） |
| 依赖 | `PySide6`、`pyserial`、`esptool` |

```bash
pip install PySide6 pyserial esptool
```

> 驱动说明：带原生 USB-Serial/JTAG 的芯片（如 ESP32-C6/S3）Windows 10+ 免装驱动；
> 使用外接 USB 转串口芯片（CH340/CP210x 等）的板子，需先安装对应驱动。

## 使用方法

```bash
git clone https://github.com/yakemozu/esp32-flash-tool.git
cd esp32-flash-tool
python3 flash_tool.py                    # 启动空界面, 手动选择固件
python3 flash_tool.py --manifest-dir /path/to/release/dir   # 可选: 启动即载入发布目录
```

1. **选择固件**：点击"选择固件..."——
   - 选中发布目录里的 `manifest.json`（推荐，防呆最全，含发布追溯信息）；
   - 或选中 IDF 构建目录中的 app `.bin`（如 `build/xxx.bin`），工具自动补齐
     同目录的 bootloader 与分区表一起烧录；
   - 或直接选中 `merge_bin` 合并后的单文件 `.bin`，工具自动识别芯片和版本；
2. 将设备通过 USB 连接到电脑；
3. 点击"刷新"选择对应串口（多个设备时按串口号区分）；
4. 点击"**开始烧录**"，等待三步流程完成；
5. 窗口顶部显示 ✅ 即为成功；显示 ❌ 时把日志区内容保存并反馈给开发人员。

> 若板子**没有自动复位电路**：按住板上的 BOOT 键，再插入 USB，
> 看到工具开始烧录后再松开 BOOT 键。

## 发布目录格式（可选，用于完整防呆）

发布目录需包含以下文件：

| 文件 | 作用 |
| :--- | :--- |
| `manifest.json` | 版本、目标芯片、工厂镜像文件名、SHA256（必需） |
| `<name>_factory.bin` | `esptool merge_bin` 合并后的单文件镜像（必需） |
| `flasher_args.json` | flash 模式/容量/频率参数（可选，缺失时使用芯片默认值） |

`manifest.json` 示例：

```json
{
  "project": "myapp",
  "target": "esp32c6",
  "version": "1.2.3",
  "factory_bin": "myapp_esp32c6_v1.2.3_factory.bin",
  "factory_sha256": "<sha256 of the factory image>",
  "factory_size_bytes": 2402304
}
```

构建发布固件时生成上述文件的示例：

```bash
# 在 IDF 构建目录中，将分散的 bin 合并为单文件工厂镜像
esptool.py --chip esp32c6 merge_bin -o myapp_esp32c6_vX.Y.Z_factory.bin \
    --flash-mode dio --flash-size 4MB --flash-freq 80m @flash_args
# 同时生成 manifest.json（含 sha256、版本、构建时间）
```

> **单 bin 手动模式**：请确保 bin 是 `merge_bin` 合并后的完整镜像
> （从 0x0 偏移烧录）；若选的是 IDF 构建目录里的裸 app `.bin`，工具会
> 自动补齐同目录的 bootloader/分区表，无需手工合并。

## 常见问题

| 现象 | 原因与处理 |
| :--- | :--- |
| 串口列表为空 | 驱动未装 / 线材无数据功能；换线或装驱动后点"刷新" |
| 第 1 步提示"未检测到芯片" | 未进入下载模式：有自动复位电路的板子直接重试；无电路的板子按住 BOOT 插入 USB |
| 第 2 步失败且自动重试后仍失败 | 换 USB 口（避免无源 Hub/扩展坞）、换线；仍失败则记录日志反馈 |
| 第 3 步"设备未启动" | 多为串口刚释放时序问题，重跑一次即可；反复出现需检查固件本身 |
| "芯片型号不符，已拒绝烧录" | 固件与板子不匹配（手动模式检查"目标芯片"选择是否正确） |
| 杀毒软件拦截 exe | PyInstaller 打包程序常见误报，加白名单即可 |

## 打包为独立可执行文件（给测试人员分发）

测试人员机器无需 Python。**exe 必须在 Windows 上构建**（PyInstaller 不能交叉编译）：

方式一（推荐）：双击运行 `build_exe.bat`，自动装依赖并构建；
方式二手动执行：

```bat
pip install PySide6 pyserial esptool pyinstaller
pyinstaller --noconfirm --clean ESP32FlashTool.spec
```

- 产物：`dist\ESP32FlashTool\ESP32FlashTool.exe`，**整个文件夹**压缩分发
  （onedir 模式：启动快、杀毒误报少；固件不内置，由界面手动选择）；
- spec 已显式收集 esptool 5.x 的 flasher stub 数据文件，
  首次构建后请在无 Python 的干净 Windows 上完整验证一遍烧录流程；
- 调试期可把 spec 中 `console=False` 改为 `True`，能看到 Python 报错信息。

## 目录结构

```
esp32-flash-tool/
├── flash_tool.py        # 程序入口
├── gdflash/
│   ├── assets/          # 图标与 UI 矢量图形资源
│   ├── assets.py        # 图标加载器与系统托盘/任务栏集成
│   ├── esptool_job.py   # esptool 命令构造、执行线程、芯片识别、进度解析
│   ├── gui.py           # PySide6 经典标准主界面
│   ├── gui_minimal.py   # PySide6 极简卡片式主界面（默认）
│   ├── i18n.py          # 中英双语运行时字符串表
│   ├── manifest.py      # 发布清单加载、固件文件防呆校验、手动/构建目录模式对象
│   └── serialboot.py    # 烧录后串口启动日志抓取与版本比对
├── ESP32FlashTool.spec  # PyInstaller 打包配置
├── build_exe.bat        # Windows 一键打包脚本
├── requirements.txt     # Python 源码运行依赖
├── README.md            # English README
└── README.zh-CN.md      # 本文件
```

## 实现说明

- 烧录基于 `esptool`（v5.x）：`python -m esptool --chip <chip> write-flash <offset> <file> ...`，
  写入数据由 esptool 自动 SHA 校验；构建目录模式生成与 `idf.py flash` 等价的多偏移命令；
- 芯片名归一化后比较：esptool 报告 `ESP32-C6`，manifest 用 `esp32c6`，
  统一小写并去除 `-`/`_` 再比对；
- 固件信息解析不依赖清单：直接读取镜像头（magic/flash 参数/chip_id）和
  `0x10000` 偏移处的 `esp_app_desc_t`（自动适配 24 字节 v1 / 8 字节 v0 镜像头），
  与 `manifest.json` 比对；频率编码按芯片查表（如 ESP32-C6 的 0x0 按 80m 显示）；
- 启动日志版本提取按优先级匹配：`App version:` 横幅 → 通用版本号，
  避免误匹配 `ESP-IDF vX.Y.Z` 之类的横幅版本；
- 手动 bin 模式：跳过清单的 SHA256 比对，芯片/版本从镜像头自动识别
  （v0 镜像头无芯片信息时需手动选择），并校验 0x0 处存在合法镜像头；
- 构建目录模式：裸 app 镜像 + 同目录 `flasher_args.json`（或 `flash_args`）
  即构成完整可烧固件；bootloader 或分区表缺失时降级为拒绝提示；
- 拒绝孤立的裸 app 镜像：该文件缺少设备启动必需的引导程序，单独烧录
  无法启动，必须改用合并固件或完整构建目录。

## 支持范围

- 芯片：ESP32 / ESP32-S2 / S3 / C3 / C6 / H2 / P4（由 esptool 芯片识别决定）；
- esptool v5.x，Python 3.10+；
- 固件来源：发布目录（manifest.json）、IDF 构建目录（app .bin）、合并工厂镜像。

## 许可证与免责

- **个人项目声明**：本项目为作者独立利用业余时间开发并维护的个人开源项目，与作者当前及过往任职的任何公司、雇主或商业实体均无关联，不代表任何机构的立场，亦不包含任何雇主的商业机密或专有资产；
- 本项目以 [GPL-3.0](LICENSE) 发布。程序界面采用 [PySide6](https://wiki.qt.io/Qt_for_Python)（LGPLv3），底层包含 [esptool](https://github.com/espressif/esptool)（GPLv2+）组件；
- 固件烧录存在使设备变砖的风险，使用本工具须自行承担风险；
- 本工具与乐鑫（Espressif）无隶属关系，esptool 归其原作者所有。

<!-- 文档同步: 修改本文档时请同步更新 README.md -->
