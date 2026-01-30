# -*- mode: python ; coding: utf-8 -*-
"""
LocalBrisk Backend PyInstaller 打包配置
用于将 Python FastAPI 后端打包为独立可执行文件
"""

import sys
import os
from pathlib import Path

# 获取当前目录
CURRENT_DIR = Path(os.path.dirname(os.path.abspath(SPEC)))

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=[str(CURRENT_DIR)],
    binaries=[],
    datas=[
        # 如果有静态文件或配置文件，在这里添加
    ],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        'fastapi',
        'pydantic',
        'pydantic_settings',
        'starlette',
        'httptools',
        'websockets',
        'watchfiles',
        'polars',
        'duckdb',
        'httpx',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'PIL',
        'cv2',
        'numpy.testing',
        'scipy',
    ],
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
    name='localbrisk-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 保留控制台以便查看日志
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
