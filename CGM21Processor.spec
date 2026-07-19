# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
from glob import glob

datas = [('cgm21_config.json', '.')]
binaries = [
    (r'C:\Users\darra\miniconda3\envs\pycgm310\lib\site-packages\_btk.pyd', '.'),
    (r'C:\Users\darra\miniconda3\envs\pycgm310\Library\bin\BTKBasicFilters.dll', '.'),
    (r'C:\Users\darra\miniconda3\envs\pycgm310\Library\bin\BTKCommon.dll', '.'),
    (r'C:\Users\darra\miniconda3\envs\pycgm310\Library\bin\BTKIO.dll', '.'),
]
for dll in glob(r'C:\Users\darra\miniconda3\envs\pycgm310\Library\bin\*.dll'):
    binaries.append((dll, '.'))
hiddenimports = ['process_cgm21', 'btk', '_btk']
tmp_ret = collect_all('pyCGM2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('scipy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('btk')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['scripts\\cgm21_interface.py'],
    pathex=['scripts'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CGM21Processor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CGM21Processor',
)


