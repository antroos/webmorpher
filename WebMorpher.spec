# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app.py'],  # Змінено з main.py на app.py
    pathex=[],
    binaries=[],
    datas=[
        ('icons/*', 'icons/'),  # Іконки
        ('*.md', '.'),  # Документація
        ('resources_rc.py', '.'),  # Qt ресурси
        ('first_run_dialog.py', '.'),  # Діалог першого запуску
    ],
    hiddenimports=[
        # Основні залежності
        'numpy',
        'numpy.core',
        'numpy.core.multiarray',
        'numpy.core.numeric',
        
        # PyQt5
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.sip',
        
        # Browser-use та його компоненти
        'browser_use',
        'playwright',
        'playwright.async_api',
        'langchain',
        'langchain.core',
        'langchain.openai',
        'langchain.anthropic',
        'langchain.aws',
        'langchain.google_genai',
        'langchain.ollama',
        'langchain.deepseek',
        
        # Обробка даних та утиліти
        'faiss',
        'markdownify',
        'pydantic',
        'pydantic.v1',
        'pyperclip',
        'screeninfo',
        'psutil',
        'mem0ai',
        
        # Мережа та API
        'httpx',
        'requests',
        'python-dotenv',
        'google.api.core',
        'asyncio',
        'aiohttp',
        'websockets',
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
    name='WebMorpher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icons/app_icon.icns'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='WebMorpher'
)

app = BUNDLE(
    coll,
    name='WebMorpher.app',
    icon='icons/app_icon.icns',
    bundle_identifier='com.webmorpher.app',
    info_plist={
        'CFBundleName': 'WebMorpher',
        'CFBundleDisplayName': 'WebMorpher',
        'CFBundleGetInfoString': "WebMorpher Application",
        'CFBundleIdentifier': "com.webmorpher.app",
        'CFBundleVersion': "1.0.0",
        'CFBundleShortVersionString': "1.0.0",
        'NSHighResolutionCapable': 'True',
        'LSEnvironment': {
            'OPENBLAS_NUM_THREADS': '1',
            'MKL_NUM_THREADS': '1',
            'VECLIB_MAXIMUM_THREADS': '1',
            'NUMEXPR_NUM_THREADS': '1',
            'OMP_NUM_THREADS': '1',
        }
    }
) 