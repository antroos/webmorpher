#!/bin/bash
set -e

echo "=== Создание автономного пакета WebMorpher для macOS ==="

# Основные пути для приложения
APP_DIR="WebMorpher.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"
FRAMEWORKS_DIR="$CONTENTS_DIR/Frameworks"
PYTHON_ENV_DIR="$RESOURCES_DIR/python_env"

# Очистка предыдущей сборки
echo "Очистка предыдущих сборок..."
rm -rf "$APP_DIR"
rm -f "WebMorpher-Standalone.dmg"

# Создание структуры каталогов
echo "Создание структуры приложения..."
mkdir -p "$MACOS_DIR"
mkdir -p "$RESOURCES_DIR"
mkdir -p "$RESOURCES_DIR/icons/svg"
mkdir -p "$FRAMEWORKS_DIR"

# Копирование иконки и SVG-иконок
echo "Копирование ресурсов..."
cp icon.icns "$RESOURCES_DIR/"
cp -r icons/svg/* "$RESOURCES_DIR/icons/svg/"

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
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
</dict>
</plist>
EOF

# Создание запускающего скрипта
echo "Создание запускающего скрипта..."
cat > "$MACOS_DIR/webmorpher" << 'EOF'
#!/bin/bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESOURCES_DIR="$DIR/../Resources"
PYTHON_ENV="$RESOURCES_DIR/python_env"
BROWSER_INSTALLED_FLAG="$RESOURCES_DIR/.browser_installed"

# Предотвращение проблем с многопоточностью OpenBLAS в NumPy
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export OMP_NUM_THREADS=1

# Активация виртуального окружения
source "$PYTHON_ENV/bin/activate"

# Проверка необходимости установки браузера
if [ ! -f "$BROWSER_INSTALLED_FLAG" ] || [ "$1" == "--install-browser" ]; then
    echo "Установка/обновление Chromium для WebMorpher..."
    # Устанавливаем браузер
    cd "$RESOURCES_DIR"
    python -m playwright install chromium
    
    # Создаем флаг, что браузер установлен
    touch "$BROWSER_INSTALLED_FLAG"
    
    echo "Chromium успешно установлен!"
fi

# Проверка наличия аргумента для установки браузера и выход, если это единственный аргумент
if [ "$1" == "--install-browser" ] && [ "$#" -eq 1 ]; then
    echo "Установка браузера завершена. Теперь вы можете запустить приложение обычным способом."
    exit 0
fi

# Запуск приложения
cd "$RESOURCES_DIR"
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
pip install --no-cache-dir -r requirements.txt

# Устанавливаем browser-use и playwright явно, чтобы убедиться, что они точно установлены
echo "Установка browser-use и playwright..."
pip install --no-cache-dir browser-use>=0.1.46
pip install --no-cache-dir playwright>=1.52.0
pip install --no-cache-dir numpy==1.25.2
pip install --no-cache-dir PyQt5>=5.15.0

# Копирование исходных файлов приложения
echo "Копирование исходных файлов..."
cp app.py "$RESOURCES_DIR/"
cp resources_rc.py "$RESOURCES_DIR/"
cp icons.qrc "$RESOURCES_DIR/"
cp first_run_dialog.py "$RESOURCES_DIR/"
cp app_welcome_dialog_patch.py "$RESOURCES_DIR/"
cp README.md "$RESOURCES_DIR/"
cp INSTALL.md "$RESOURCES_DIR/"
cp requirements.txt "$RESOURCES_DIR/"
cp TROUBLESHOOTING.md "$RESOURCES_DIR/"
cp FAQ.md "$RESOURCES_DIR/"

# Применение патча для окна приветствия
echo "Применение патча для окна приветствия с помощью Python..."
cat > "$RESOURCES_DIR/apply_welcome_patch.py" << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

def apply_patch(filename):
    """Применяет патч для добавления диалога приветствия"""
    with open(filename, 'r') as f:
        content = f.read()
    
    # Добавление импорта
    content = content.replace(
        'import resources_rc', 
        'import resources_rc\nfrom first_run_dialog import FirstRunDialog'
    )
    
    # Добавление флага в метод load_config
    content = content.replace(
        'self.theme = config.get("theme", "auto")',
        'self.theme = config.get("theme", "auto")\n        # Флаг для отслеживания первого запуска\n        self.show_welcome_dialog = config.get("show_welcome_dialog", True)'
    )
    
    # Добавление сохранения флага в метод save_config
    content = content.replace(
        'config["theme"] = self.theme',
        'config["theme"] = self.theme\n        # Сохраняем флаг первого запуска\n        config["show_welcome_dialog"] = self.show_welcome_dialog'
    )
    
    # Добавление вызова диалога в конец метода setup_ui
    content = content.replace(
        'self.setWindowTitle("WebMorpher")',
        'self.setWindowTitle("WebMorpher")\n        \n        # Показываем диалог первого запуска, если это необходимо\n        if self.show_welcome_dialog:\n            self.show_welcome_screen()'
    )
    
    # Добавление нового метода show_welcome_screen
    welcome_method = """    def show_welcome_screen(self):
        # Показывает экран приветствия при первом запуске
        welcome_dialog = FirstRunDialog(self)
        welcome_dialog.exec_()
        
        # Если пользователь выбрал "Не показывать снова", сохраняем эту настройку
        if welcome_dialog.dont_show_again():
            self.show_welcome_dialog = False
            self.save_config()

"""
    
    # Находим место перед методом closeEvent для вставки нового метода
    pattern = r'def\s+closeEvent'
    content = re.sub(pattern, welcome_method + r'def closeEvent', content)
    
    # Записываем обновленное содержимое
    with open(filename, 'w') as f:
        f.write(content)
    
    print(f"Патч успешно применен к {filename}")

if __name__ == "__main__":
    apply_patch("app.py")
EOF

# Делаем скрипт исполняемым и запускаем его
chmod +x "$RESOURCES_DIR/apply_welcome_patch.py"
cd "$RESOURCES_DIR"
python apply_welcome_patch.py

# Установка браузера Chromium через playwright
echo "Установка Chromium через playwright..."
# Сначала устанавливаем нужные переменные окружения, чтобы избежать ошибок
export PLAYWRIGHT_BROWSERS_PATH="$RESOURCES_DIR/pw-browsers"
python -m playwright install chromium --force
# Создаем флаг установки браузера
touch "$RESOURCES_DIR/.browser_installed"

# Удаляем config-файл с API ключом, если он существует
# Возвращаемся в корневую директорию
cd "$(dirname "$0")"
CONFIG_FILE=~/.webmorpher_config.json
if [ -f "$CONFIG_FILE" ]; then
    echo "Создание пустого конфигурационного файла..."
    # Создаем резервную копию, если пользователь захочет восстановить
    cp "$CONFIG_FILE" "${CONFIG_FILE}.bak"
    
    # Создаем пустой файл конфигурации
    python -c "
import json
try:
    with open('$CONFIG_FILE', 'r') as f:
        config = json.load(f)
    config['api_key'] = ''
    with open('$RESOURCES_DIR/default_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    print('Создан пустой файл конфигурации.')
except Exception as e:
    print(f'Ошибка при обработке файла конфигурации: {e}')
    with open('$RESOURCES_DIR/default_config.json', 'w') as f:
        json.dump({'api_key': '', 'theme': 'auto', 'show_welcome_dialog': True}, f, indent=2)
"
else
    # Если файла нет, создаем пустой шаблон
    echo "Создание пустого шаблона конфигурации..."
    echo '{"api_key": "", "theme": "auto", "show_welcome_dialog": true}' > "$RESOURCES_DIR/default_config.json"
fi

# Создание скрипта для установки/обновления браузера
echo "Создание утилиты обновления браузера..."
cat > "$RESOURCES_DIR/update_browser.command" << 'EOF'
#!/bin/bash
# Скрипт для обновления/переустановки браузера Chromium для WebMorpher

# Находим путь к приложению WebMorpher
APP_PATH=""

# Сначала проверяем, запущен ли скрипт из самого приложения
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$SCRIPT_DIR" == *"/WebMorpher.app/Contents/Resources" ]]; then
    APP_PATH="${SCRIPT_DIR}/../.."
else
    # Ищем приложение в стандартных местах
    for dir in "/Applications" "$HOME/Applications"; do
        if [ -d "$dir/WebMorpher.app" ]; then
            APP_PATH="$dir/WebMorpher.app"
            break
        fi
    done
fi

if [ -z "$APP_PATH" ]; then
    echo "Ошибка: Не удалось найти приложение WebMorpher.app"
    echo "Пожалуйста, убедитесь, что приложение установлено в папку Applications."
    exit 1
fi

echo "Найдено приложение WebMorpher: $APP_PATH"
echo "Запуск установки/обновления браузера Chromium..."

# Запускаем приложение с аргументом для установки браузера
"$APP_PATH/Contents/MacOS/webmorpher" --install-browser

echo "Завершено! Теперь вы можете запустить WebMorpher обычным способом."
EOF

# Делаем скрипт исполняемым
chmod +x "$RESOURCES_DIR/update_browser.command"

# Возврат в корневую директорию
cd "$(dirname "$0")"

# Создание DMG с помощью hdiutil
echo "Создание DMG пакета..."
DMG_NAME="WebMorpher-Standalone.dmg"
hdiutil create -volname "WebMorpher" -srcfolder "$APP_DIR" -ov -format UDZO "$DMG_NAME"

echo "===== Готово! ====="
echo "Приложение создано: $APP_DIR"
echo "DMG пакет создан: $DMG_NAME" 
echo "Теперь пользователи могут просто перетащить приложение в папку Applications и запустить его." 