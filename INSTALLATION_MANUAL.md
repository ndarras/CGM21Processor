# CGM2.1 Processor Installation Manual for Windows 11

This guide explains how to download, install, and run the CGM2.1 Processor on a Windows 11 PC.

## 1. What You Need

Before starting, you need:

- A Windows 11 computer.
- Internet access to download the application from GitHub.
- A folder containing your `.c3d` files.
- At least one static trial file with `static` in the filename, for example `Subject01_Static.c3d`.
- One or more dynamic trial files without `static` in the filename, for example `Subject01_Walk01.c3d`.

You do not need to install Python, conda, pyCGM2, or BTK. They are included in the downloaded package.

## 2. Download the Application

1. Open this release page in your browser:

   https://github.com/ndarras/CGM21Processor/releases/tag/v0.1.0

2. Under **Assets**, download:

   `CGM21Processor_Windows11_v0.1.0.zip`

3. Save the zip file somewhere easy to find, such as your `Downloads` folder.

## 3. Unzip the Download

1. Right-click `CGM21Processor_Windows11_v0.1.0.zip`.
2. Choose **Extract All...**.
3. Select a destination folder, for example:

   `C:\Users\YourName\Documents\CGM21Processor`

4. Click **Extract**.

After extraction, open the extracted folder. You should see files including:

- `CGM21Processor.exe`
- `Install_CGM21Processor.cmd`
- `README.md`

## 4. Install the Application

You have two options.

### Option A: Run Without Installing

1. Open the extracted folder.
2. Double-click `CGM21Processor.exe`.

This starts the application directly from the extracted folder.

### Option B: Install With a Desktop Shortcut

1. Open the extracted folder.
2. Double-click `Install_CGM21Processor.cmd`.
3. If Windows asks for confirmation, choose **More info**, then **Run anyway**.
4. Wait until the installer says installation is complete.
5. Use the new Desktop shortcut named **CGM2.1 Processor**.

The installer copies the application to:

`%LOCALAPPDATA%\CGM21Processor`

This usually means:

`C:\Users\YourName\AppData\Local\CGM21Processor`

## 5. Prepare Your C3D Folder

Put all files for one processing session in the same folder.

The folder must contain:

- Static trials: filenames must include `static` anywhere in the name.
- Dynamic trials: filenames must not include `static`.

Examples:

```text
T001_Static.c3d
T001_Walk01.c3d
T001_Walk02.c3d
T001_Run01.c3d
```

The application uses this naming rule automatically:

- `static` in filename = static trial
- no `static` in filename = dynamic trial

The match is not case-sensitive, so `Static`, `STATIC`, and `static` all work.

## 6. Run CGM2.1 Processing

1. Open **CGM2.1 Processor**.
2. Click **Browse**.
3. Select the folder containing your `.c3d` files.
4. Review the configuration fields in the application.
5. Update anthropometric values if needed, such as body mass, leg length, knee width, and ankle width.
6. Click **Run CGM2.1**.
7. Watch the processing log and progress panel.
8. When processing finishes, click **Open Processed Folder**.

Processed files are written to a new folder named:

`processed`

inside the selected C3D folder.

## 7. Configuration Notes

The application reads and updates a file named:

`cgm21_config.json`

This file stores CGM2.1 processing settings and anthropometric measurements.

Important values include:

- `Bodymass` in kilograms.
- Leg lengths in millimetres.
- Knee and ankle widths in millimetres.
- Marker diameter in millimetres.
- Force plate assignment mode.
- Filter settings.

By default, pyCGM2 marker and force filtering is disabled to preserve the corrected kinetics behavior in this release.

## 8. Common Problems

### Windows Blocks the Application

Because this is an unsigned application, Windows may show a warning.

Choose:

1. **More info**
2. **Run anyway**

### No Static Trial Found

If you see an error saying no static C3D was found, rename the static trial so the filename contains `static`.

Example:

```text
Subject01_Static.c3d
```

### No Dynamic Trial Found

If every `.c3d` filename contains `static`, the application will not find any dynamic trials.

Dynamic files should not contain `static` in the filename.

### Processed Folder Is Empty or Processing Fails

Check that:

- The selected folder contains `.c3d` files.
- At least one file contains `static` in the filename.
- Dynamic trials do not contain `static` in the filename.
- Required anthropometric values are present and realistic.
- The files are not open in another program.

### Antivirus Warning

Some antivirus tools warn about newly built unsigned `.exe` files. If this happens, allow the application only if it was downloaded from the official GitHub release page:

https://github.com/ndarras/CGM21Processor/releases/tag/v0.1.0

## 9. Updating to a New Version

1. Download the newest release zip from GitHub.
2. Extract it.
3. Run `Install_CGM21Processor.cmd` again.
4. The installer will replace the previous local application files.

Your original C3D data folders are not modified except for the creation or update of the `processed` folder inside the selected session folder.

## 10. Support Information

When reporting a problem, include:

- The application version, for example `v0.1.0`.
- A screenshot of the error message.
- The processing log shown in the application.
- Whether the filenames include the correct `static` naming rule.
- Whether the issue happens with one file or all files.
