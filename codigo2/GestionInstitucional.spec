# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all


ROOT = Path(SPECPATH)
datas = [
    (str(ROOT / "icon.png"), "."),
    (str(ROOT / "image.png"), "."),
    (str(ROOT / "views" / "assets" / "cvdr.jpg"), "views/assets"),
    (str(ROOT / "database" / "crear_tabla_documentos.sql"), "database"),
]
binaries = []
hiddenimports = [
    "PIL._tkinter_finder",
    "views.ui_helpers",
    "views.applogin",
    "views.home",
    "views.update",
    "views.folio_reservado",
    "views.crear_documento",
    "views.enviados",
]

for package in ("customtkinter", "PIL", "msal", "requests",
                "decouple", "docx", "reportlab", "psycopg", "paramiko"):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

analysis = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
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
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="GestionInstitucional",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)
collection = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="GestionInstitucional",
)
