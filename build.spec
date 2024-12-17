# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_dynamic_libs

binaries = []
binaries += collect_dynamic_libs('tables')


a = Analysis(
    [ 'src/run.py' ],
    pathex                  = [ '.' ],
    binaries                = binaries,
    datas                   = [],
    hiddenimports           = [],
    hookspath               = [],
    hooksconfig             = {},
    runtime_hooks           = [],
    excludes                = [],
    win_no_prefer_redirects = False,
    win_private_assemblies  = False,
    cipher                  = None,
    noarchive               = False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher = None
)

exe = EXE(
    pyz,
    a.scripts, a.binaries, a.zipfiles, a.datas,
    [],
    name                       = 'osu-performance-analyzer',
    exclude_binaries           = False,
    debug                      = False,
    bootloader_ignore_signals  = False,
    strip                      = False,
    upx                        = False,
    upx_exclude                = [],
    runtime_tmpdir             = None,
    console                    = True,
    disable_windowed_traceback = False,
    argv_emulation             = False,
    target_arch                = None,
    codesign_identity          = None,
    entitlements_file          = None,
)
