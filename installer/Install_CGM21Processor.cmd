@echo off
setlocal
set "SOURCE=%~dp0"
set "TARGET=%LOCALAPPDATA%\CGM21Processor"

echo Installing CGM2.1 Processor to "%TARGET%"...
if not exist "%TARGET%" mkdir "%TARGET%"
robocopy "%SOURCE%" "%TARGET%" /MIR /XD .git build dist C3D_Data downloads pycgm2_local __pycache__ /XF *.zip >nul
if errorlevel 8 (
    echo Installation failed while copying files.
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$shell=New-Object -ComObject WScript.Shell; $shortcut=$shell.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\CGM2.1 Processor.lnk'); $shortcut.TargetPath='%TARGET%\CGM21Processor.exe'; $shortcut.WorkingDirectory='%TARGET%'; $shortcut.Save()"

echo Installation complete.
echo Launch from the Desktop shortcut named "CGM2.1 Processor".
pause
