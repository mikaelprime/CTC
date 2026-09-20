from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


DESKTOP = Path(SPECPATH)

hiddenimports = [
    "matplotlib.backends.backend_qtagg",
    "matplotlib.backends.backend_agg",
]

datas = collect_data_files("matplotlib")
datas.append((str(DESKTOP / "config.example.json"), "."))

a = Analysis(
    [str(DESKTOP / "main.py")],
    pathex=[str(DESKTOP)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="CTC-Campus",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)