# -*- mode: python ; coding: utf-8 -*-
# PyInstaller onedir spec. Version + Windows version resource derive from
# pyproject.toml (single source of truth). Build: uv run pyinstaller packaging/dayline.spec --noconfirm

import tomllib
from pathlib import Path

ROOT = Path(SPECPATH).parent
version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
vtuple = tuple(int(x) for x in (version.split(".") + ["0", "0", "0", "0"])[:4])

icon = ROOT / "src" / "dayline" / "ui" / "assets" / "app.ico"
qml_dir = ROOT / "src" / "dayline" / "ui" / "qml"
assets_dir = ROOT / "src" / "dayline" / "ui" / "assets"

# Generate the version resource next to the build dir (kept out of the repo).
vi_path = Path(SPECPATH) / "version_info.txt"
vi_path.write_text(f"""
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={vtuple},
    prodvers={vtuple},
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('0409 04B1', [
      StringStruct('CompanyName', 'Dayline'),
      StringStruct('FileDescription', 'Dayline — daily to-do on your Obsidian vault'),
      StringStruct('FileVersion', '{version}'),
      StringStruct('InternalName', 'Dayline'),
      StringStruct('LegalCopyright', 'Copyright (c) 2026 Sujay Yadav'),
      StringStruct('OriginalFilename', 'Dayline.exe'),
      StringStruct('ProductName', 'Dayline'),
      StringStruct('ProductVersion', '{version}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""", encoding="utf-8")

a = Analysis(
    [str(ROOT / "src" / "dayline" / "__main__.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[
        (str(qml_dir), "dayline/ui/qml"),
        (str(assets_dir / "app.ico"), "dayline/ui/assets"),
        (str(assets_dir / "app.png"), "dayline/ui/assets"),
    ],
    hiddenimports=["PySide6.QtQuickControls2"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
              "PySide6.Qt3DCore", "tkinter"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Dayline",
    debug=False,
    strip=False,
    upx=False,
    console=False,            # windowed app: no console
    disable_windowed_traceback=False,
    icon=str(icon),
    version=str(vi_path),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Dayline",
)
