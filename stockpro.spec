# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

# Collect all data files
datas = [
    ('templates', 'templates'),
    ('static', 'static'),
    ('screener.py', '.'),
    ('screener_scraper.py', '.'),
    ('stock_analyzer_v34.py', '.'),
]

# Add data files if they exist
optional_files = [
    'users.json',
    'screener_results.json',
    'upstox_instruments.json',
]
for f in optional_files:
    if os.path.exists(f):
        datas.append((f, '.'))

a = Analysis(
    ['launcher.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'flask', 'flask_login', 'werkzeug', 'werkzeug.security',
        'requests', 'bs4', 'beautifulsoup4',
        'yfinance', 'numpy', 'pandas',
        'engineio', 'socketio',
        'pkg_resources',
        'charset_normalizer',
        'certifi', 'urllib3', 'idna',
        'lxml', 'html5lib',
        'multitasking', 'peewee',
        'appdirs', 'frozendict',
        'curl_cffi',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'PIL', 'cv2', 'torch'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='StockPro',
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
    icon=None,
)
