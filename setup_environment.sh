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

# Створення та активація віртуального середовища
print_status "Створення віртуального середовища Python 3.11..."
python3.11 -m venv env311
source env311/bin/activate

# Оновлення pip
print_status "Оновлення pip..."
pip install --upgrade pip

# Встановлення numpy окремо (важливо для уникнення конфліктів)
print_status "Встановлення numpy..."
pip install --no-cache-dir numpy==1.25.2

# Встановлення PyQt5 та залежностей GUI
print_status "Встановлення PyQt5 та GUI залежностей..."
pip install --no-cache-dir PyQt5==5.15.11 PyQt5-sip==12.17.0 PyQt5-Qt5==5.15.16

# Встановлення основних залежностей з requirements.txt
print_status "Встановлення основних залежностей..."
pip install --no-cache-dir -r requirements.txt

# Встановлення Playwright та браузера
print_status "Встановлення Playwright та браузера..."
playwright install chromium

# Налаштування змінних середовища
print_status "Налаштування змінних середовища..."
cat > env311/environment_vars.sh << EOF
#!/bin/bash
# OpenBLAS threading
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export OMP_NUM_THREADS=1
EOF

# Додавання активації змінних середовища до activate скрипта
echo "source \"\$VIRTUAL_ENV/environment_vars.sh\"" >> env311/bin/activate

# Створення конфігураційних директорій
print_status "Створення конфігураційних директорій..."
mkdir -p ~/.webmorpher_browser_profile

# Створення базового конфігураційного файлу
print_status "Створення базового конфігураційного файлу..."
cat > ~/.webmorpher_config.json << EOF
{
    "api_key": "",
    "theme": "auto",
    "show_welcome_dialog": true
}
EOF

print_success "Налаштування середовища завершено!"
print_success "Для активації середовища використовуйте команду: source env311/bin/activate"
print_status "Не забудьте встановити свій API ключ OpenAI в ~/.webmorpher_config.json" 