# adviser.spec
import os
block_cipher = None

a = Analysis(
    ['adviser_main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Archivos que deben incluirse en el .exe
        ('ui.html',      '.'),
        ('overlay.html',        '.'),
        ('rutina_overlay.html', '.'),
        ('style.css',    '.'),
        ('script.js',    '.'),
        ('icon.png',     '.'),
        ('rutina.json',  '.'),
        ('config.json',  '.'),
    ],
    hiddenimports=[
        'webview',
        'webview.platforms.winforms',
        'winotify',
        'clr',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Adviser',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # Sin ventana de consola negra
    icon='icon.png',        # Ícono del .exe
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Adviser',
)
