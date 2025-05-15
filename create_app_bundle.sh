#!/bin/bash
set -e

# Путь, куда будет установлено приложение
APP_DIR="WebMorpher.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"
PYTHON_ENV_DIR="$RESOURCES_DIR/python_env"

echo "Создание структуры приложения..."
mkdir -p "$MACOS_DIR"
mkdir -p "$RESOURCES_DIR"

# Копирование иконки
echo "Копирование ресурсов..."
cp icon.icns "$RESOURCES_DIR/"

# Создание Info.plist
echo "Создание Info.plist..."
cat > "$CONTENTS_DIR/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>English</string>
    <key>CFBundleDisplayName</key>
    <string>WebMorpher</string>
    <key>CFBundleExecutable</key>
    <string>webmorpher</string>
    <key>CFBundleIconFile</key>
    <string>icon.icns</string>
    <key>CFBundleIdentifier</key>
    <string>com.antroos.webmorpher</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>WebMorpher</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright © 2024 antroos. All Rights Reserved.</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
</dict>
</plist>
EOF

# Создание запускающего скрипта
echo "Создание запускающего скрипта..."
cat > "$MACOS_DIR/webmorpher" << EOF
#!/bin/bash
DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
RESOURCES_DIR="\$DIR/../Resources"
PYTHON_ENV="\$RESOURCES_DIR/python_env"

# Активация виртуального окружения
source "\$PYTHON_ENV/bin/activate"

# Запуск приложения
cd "\$RESOURCES_DIR"
python app.py
EOF

# Делаем скрипт исполняемым
chmod +x "$MACOS_DIR/webmorpher"

# Создание виртуального окружения Python в Resources
echo "Создание виртуального окружения Python 3.11..."
python3.11 -m venv "$PYTHON_ENV_DIR"

# Активация среды и установка зависимостей
echo "Установка зависимостей..."
source "$PYTHON_ENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt
pip install playwright
playwright install chromium

# Копирование исходных файлов приложения
echo "Копирование исходных файлов..."
cp app.py "$RESOURCES_DIR/"
cp README.md "$RESOURCES_DIR/"
cp INSTALL.md "$RESOURCES_DIR/"
cp requirements.txt "$RESOURCES_DIR/"

# Удаляем config-файл с API ключом, если он существует
CONFIG_FILE=~/.webmorpher_config.json
if [ -f "$CONFIG_FILE" ]; then
    echo "Удаление конфигурационного файла с API ключом..."
    # Создаем резервную копию, если пользователь захочет восстановить
    cp "$CONFIG_FILE" "${CONFIG_FILE}.bak"
    
    # Очищаем API ключ в файле
    python -c "
import json
try:
    with open('$CONFIG_FILE', 'r') as f:
        config = json.load(f)
    config['api_key'] = ''
    with open('$CONFIG_FILE', 'w') as f:
        json.dump(config, f)
    print('API ключ удален из конфигурационного файла.')
except Exception as e:
    print(f'Ошибка при обработке файла конфигурации: {e}')
"
fi

# Создание DMG с помощью hdiutil
echo "Создание DMG пакета..."
DMG_NAME="WebMorpher.dmg"
hdiutil create -volname "WebMorpher" -srcfolder "$APP_DIR" -ov -format UDZO "$DMG_NAME"

echo "Готово! Приложение и DMG-пакет успешно созданы."
echo "Приложение: $APP_DIR"
echo "DMG пакет: $DMG_NAME" 