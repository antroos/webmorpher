#!/bin/bash

# Кольори для виводу
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функція для виводу статусу
print_status() {
    echo -e "${YELLOW}[*] $1${NC}"
}

print_success() {
    echo -e "${GREEN}[+] $1${NC}"
}

print_error() {
    echo -e "${RED}[-] $1${NC}"
}

# Перевірка наявності create-dmg
if ! command -v create-dmg &> /dev/null; then
    print_status "Встановлення create-dmg..."
    brew install create-dmg
fi

# Створення тимчасової директорії для збірки
BUILD_DIR="build/dmg_build"
APP_NAME="WebMorpher"
DMG_NAME="${APP_NAME}_Installer"

# Очищення попередньої збірки
print_status "Очищення попередньої збірки..."
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}"

# Копіювання .app в тимчасову директорію
print_status "Копіювання .app..."
cp -R "dist/${APP_NAME}.app" "${BUILD_DIR}/"

# Створення символічного посилання на Applications
print_status "Створення символічного посилання на Applications..."
ln -s /Applications "${BUILD_DIR}/Applications"

# Створення DMG
print_status "Створення DMG файлу..."
create-dmg \
    --volname "${DMG_NAME}" \
    --volicon "icons/app_icon.icns" \
    --window-pos 200 120 \
    --window-size 800 400 \
    --icon-size 100 \
    --icon "${APP_NAME}.app" 200 190 \
    --hide-extension "${APP_NAME}.app" \
    --app-drop-link 600 185 \
    --no-internet-enable \
    "dist/${DMG_NAME}.dmg" \
    "${BUILD_DIR}"

# Перевірка результату
if [ $? -eq 0 ]; then
    print_success "DMG файл успішно створено: dist/${DMG_NAME}.dmg"
    # Очищення тимчасових файлів
    rm -rf "${BUILD_DIR}"
else
    print_error "Помилка при створенні DMG файлу"
    exit 1
fi 