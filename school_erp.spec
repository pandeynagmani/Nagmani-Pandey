# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for SANT Digital Solution School ERP

import os

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app/templates', 'app/templates'),
        ('app/static', 'app/static'),
        ('config', 'config'),
    ],
    hiddenimports=[
        'flask',
        'flask_login',
        'flask_wtf',
        'werkzeug',
        'werkzeug.security',
        'jinja2',
        'sqlite3',
        'cryptography',
        'cryptography.fernet',
        'qrcode',
        'PIL',
        'reportlab',
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
    name='SchoolERP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SchoolERP',
)
