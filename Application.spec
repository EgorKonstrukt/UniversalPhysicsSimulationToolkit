# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs

# Явно перечисляем всё, что pygame может использовать
pygame_hidden = [
    'pygame',
    'pygame._sdl2',
    'pygame._sdl2.audio',
    'pygame._sdl2.controller',
    'pygame._sdl2.touch',
    'pygame._sdl2.video',
    'pygame.gfxdraw',
    'pygame.scrap',
    'pygame.mixer',
    'pygame.mixer_music',
    'pygame.font',
    'pygame.image',
    'pygame.imageext',
    'pygame.color',
    'pygame.pixelcopy',
    'pygame.surfarray',
    'pygame.fastevent',
]

hiddenimports = pygame_hidden + [
    'taichi', 'taichi._lib', 'taichi.lang',
    'pygame_gui',
    'pymunk', 'pymunk._lib',
    'colorama',
    'psutil',
    'numba', 'numba.core', 'numba.experimental', 'llvmlite',
    'numpy',
]

# Собираем данные и бинарники
datas = []
datas += collect_data_files('pygame')
datas += collect_data_files('pygame_gui')
datas += collect_data_files('taichi')

binaries = []
binaries += collect_dynamic_libs('pygame')
binaries += collect_dynamic_libs('pymunk')

a = Analysis(
    ['Application.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Application',
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
    icon='logo.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Application',
)