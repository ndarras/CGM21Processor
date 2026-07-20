# CGM2.1 Processor

Windows interface for processing CGM2.1 C3D folders with pyCGM2.

## What it does

- Select a folder containing C3D files.
- Treats files containing `static` in the filename as static trials.
- Treats all other `.c3d` files as dynamic trials.
- Lets the user review and update CGM2.1 anthropometric/configuration values.
- Processes dynamic trials into a `processed` folder.
- Shows processing progress and log output in the interface.

## Installation manual

For detailed Windows 11 download, installation, setup, and troubleshooting instructions, see [INSTALLATION_MANUAL.md](INSTALLATION_MANUAL.md).

## Windows installation

Download the release zip from GitHub, unzip it, then either:

1. Run `CGM21Processor.exe` directly, or
2. Run `Install_CGM21Processor.cmd` to copy the app to `%LOCALAPPDATA%\CGM21Processor` and create a Desktop shortcut.

The packaged application is self-contained and does not require users to install Python, conda, pyCGM2, or BTK separately.

## Development build

The distributable is built with PyInstaller from the `pycgm310` environment:

```powershell
C:\Users\darra\miniconda3\envs\pycgm310\python.exe -m PyInstaller --noconfirm --clean CGM21Processor.spec
```

The generated Windows package is created from `dist\CGM21Processor`.

