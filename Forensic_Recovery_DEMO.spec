# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\Drhapso\\Documents\\PROYECTOS IA INDEPENDIENTES\\RECUPERADOR DE DATOS\\main_demo.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\Drhapso\\Documents\\PROYECTOS IA INDEPENDIENTES\\RECUPERADOR DE DATOS\\core', 'core'), ('C:\\Users\\Drhapso\\Documents\\PROYECTOS IA INDEPENDIENTES\\RECUPERADOR DE DATOS\\ui', 'ui'), ('C:\\Users\\Drhapso\\Documents\\PROYECTOS IA INDEPENDIENTES\\RECUPERADOR DE DATOS\\data', 'data'), ('C:\\Users\\Drhapso\\Documents\\PROYECTOS IA INDEPENDIENTES\\RECUPERADOR DE DATOS\\sessions', 'sessions'), ('C:\\Users\\Drhapso\\Documents\\PROYECTOS IA INDEPENDIENTES\\RECUPERADOR DE DATOS\\docs', 'docs')],
    hiddenimports=['PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'PyQt5.QtMultimedia', 'PyQt5.QtMultimediaWidgets', 'PIL', 'PIL.Image', 'PIL.ExifTags', 'sqlite3', 'winreg', 'ctypes', 'hashlib', 'hmac', 'zipfile', 'xml.etree.ElementTree'],
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
    a.binaries,
    a.datas,
    [],
    name='Forensic_Recovery_DEMO',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
