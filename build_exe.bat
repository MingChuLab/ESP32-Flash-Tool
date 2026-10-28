@echo off
REM ============================================================
REM  ESP32FlashTool one-click build script (Windows)
REM  Prereq: Python 3.10+ installed, "Add to PATH" checked.
REM  Output: dist\ESP32FlashTool\ESP32FlashTool.exe (whole folder = release)
REM  NOTE: keep this file ASCII-only + CRLF; cmd.exe parses batch
REM  files in the system codepage (GBK on Chinese Windows) and UTF-8
REM  Chinese comments corrupt the commands.
REM ============================================================
setlocal EnableExtensions

set "SRC=%~dp0"
set "SRC=%SRC:~0,-1%"

if /i "%SRC:~0,2%"=="\\" goto :from_unc
pushd "%SRC%"
if errorlevel 1 goto :bad_dir
goto :build

:from_unc
echo [INFO] UNC path detected (%SRC%).
echo [INFO] Copying sources to a local temp dir before building ...
set "BUILDROOT=%TEMP%\ESP32FlashTool_build"
if exist "%BUILDROOT%" rmdir /s /q "%BUILDROOT%"
mkdir "%BUILDROOT%"
xcopy "%SRC%\*" "%BUILDROOT%\" /e /i /q /y >nul
if errorlevel 1 goto :copy_fail
pushd "%BUILDROOT%"
if errorlevel 1 goto :bad_dir
echo [INFO] Build dir: %CD%
goto :build

:copy_fail
echo [ERROR] Failed to copy sources to %BUILDROOT%.
echo [ERROR] Please copy the flash_tool folder to a local disk and retry.
pause
exit /b 1

:bad_dir
echo [ERROR] Cannot enter build directory.
pause
exit /b 1

:build
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ and check "Add to PATH".
    pause
    exit /b 1
)

echo [1/3] Installing dependencies (PySide6, pyserial, esptool, pyinstaller) ...
if exist "requirements.txt" (
    python -m pip install -r requirements.txt "pyinstaller>=6.0.0" || goto :dep_fail
) else (
    python -m pip install "PySide6>=6.5.0" "pyserial>=3.5" "esptool>=5.0.0" "pyinstaller>=6.0.0" || goto :dep_fail
)
goto :step2

:dep_fail
echo [ERROR] pip install failed (network or permission?).
echo [TIP] Try running as Administrator, or use a domestic PyPI mirror:
echo [TIP]   python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple PySide6 pyserial esptool pyinstaller
pause
exit /b 1

:step2
echo [2/3] Building ESP32FlashTool.exe ...
python -m PyInstaller --noconfirm --clean ESP32FlashTool.spec || goto :build_fail

echo.
echo [3/3] Copying result back to the source dir ...
xcopy "%CD%\dist\*" "%SRC%\dist\" /e /i /q /y >nul
if errorlevel 1 (
    echo [WARN] Copy-back failed. Result remains at:
    echo [WARN]   %CD%\dist\ESP32FlashTool
) else (
    echo Result copied to: %SRC%\dist\ESP32FlashTool
)
goto :done

:build_fail
echo [ERROR] PyInstaller build failed. Set console=True in ESP32FlashTool.spec
echo [ERROR] and rebuild to see the traceback.
pause
exit /b 1

:done
echo.
echo Build OK. Zip the whole ESP32FlashTool folder for distribution.
echo.
echo ============================================================
echo  ACCEPTANCE CHECK (frozen builds only - build OK does NOT
echo  mean the exe can flash: sys.executable/-m behavior changes
echo  under PyInstaller, so every rebuild must pass a real cycle)
echo ============================================================
echo  On a clean Windows PC (no Python), with one ESP32 board:
echo   1. Launch ESP32FlashTool.exe, pick the firmware + COM port.
echo   2. Chip detect: shows the chip ID (espptool child runs).
echo      FAIL sign: "unrecognized arguments: -m esptool" - the
echo      exe is calling itself, esptool forwarding is broken.
echo   3. Full flash: progress bar advances, write_flash completes.
echo   4. Post-flash check: boot log shows the expected version.
echo   5. Re-flash the same image once (idempotent second run).
echo ============================================================
pause
