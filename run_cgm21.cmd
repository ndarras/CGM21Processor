@echo off
setlocal
set "PYCGM2_PYTHON=C:\Users\darra\miniconda3\envs\pycgm310\python.exe"
if not exist "%~dp0processed" mkdir "%~dp0processed"
if not exist "%~dp0processed\mpl" mkdir "%~dp0processed\mpl"
copy /Y "%~dp0static.c3d" "%~dp0processed\static.c3d" >nul
copy /Y "%~dp0dynamic_*.c3d" "%~dp0processed\" >nul
if not exist "%~dp0processed\cgm21_results.json" echo [] > "%~dp0processed\cgm21_results.json"
"%PYCGM2_PYTHON%" "%~dp0scripts\process_cgm21.py" --config "%~dp0cgm21_config.json" --output "%~dp0processed" %*
endlocal
