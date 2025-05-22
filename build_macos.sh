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

# Перевірка наявності Python 3.11
print_status "Перевірка версії Python..."
if ! command -v python3.11 &> /dev/null; then
    print_error "Python 3.11 не знайдено. Встановіть Python 3.11 та спробуйте знову."
    exit 1
fi

# Перевірка наявності pip
print_status "Перевірка наявності pip..."
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 не знайдено. Встановіть pip та спробуйте знову."
    exit 1
fi

# Створення та активація віртуального середовища для збірки
print_status "Створення віртуального середовища для збірки..."
python3.11 -m venv build_env
source build_env/bin/activate

# Оновлення pip
print_status "Оновлення pip..."
pip install --upgrade pip

# Встановлення залежностей для збірки
print_status "Встановлення залежностей для збірки..."
pip install pyinstaller
pip install -r requirements.txt

# Очищення попередніх збірок
print_status "Очищення попередніх збірок..."
rm -rf build dist

# Компіляція ресурсів Qt
print_status "Компіляція ресурсів Qt..."
pyrcc5 icons.qrc -o resources_rc.py
print_success "Ресурси Qt скомпільовано"

# Створення .app бандлу
print_status "Створення .app бандлу..."
pyinstaller WebMorpher.spec

# Перевірка успішності створення .app
if [ ! -d "dist/WebMorpher.app" ]; then
    print_error "Помилка при створенні .app бандлу"
    exit 1
fi

# Створення DMG
print_status "Створення DMG файлу..."
./create_dmg.sh

# Деактивація віртуального середовища
deactivate

# Видалення віртуального середовища для збірки
print_status "Очищення середовища збірки..."
rm -rf build_env

print_success "Збірка завершена успішно!"
print_success "DMG файл створено: dist/WebMorpher_Installer.dmg" 