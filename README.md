# WebMorpher

WebMorpher — це десктопний додаток для macOS, який дозволяє створювати та керувати автоматизованими сценаріями для веб-браузера за допомогою browser-use та GPT-4.

---

## Швидкий старт для користувача

1. **Завантажте WebMorpher.dmg**
2. Відкрийте файл та перетягніть WebMorpher.app у папку Applications
3. При першому запуску введіть ваш OpenAI API ключ (див. інструкцію нижче)

### Якщо macOS блокує запуск (немає підпису Apple Developer):
- Відкрийте "Системні налаштування" → "Захист і безпека" (Security & Privacy)
- Натисніть "Відкрити все одно" (Open Anyway) біля повідомлення про WebMorpher
- Підтвердіть запуск

### Як отримати OpenAI API ключ
1. Перейдіть на https://platform.openai.com/api-keys
2. Увійдіть у свій акаунт OpenAI
3. Натисніть "Create new secret key"
4. Скопіюйте ключ (починається з sk-...)
5. Вставте у вікно програми при першому запуску

---

## Інструкція для розробника: збірка .app та DMG

### 1. Підготовка середовища
```bash
python3.11 -m venv env311
source env311/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install playwright numpy==1.25.2
playwright install chromium
```

### 2. Збірка .app
- Запустіть скрипт:
```bash
bash create_app_bundle.sh
```
- Скрипт створить WebMorpher.app з усіма ресурсами та готовим python_env

### 3. Копіювання ресурсів
- Переконайтесь, що у WebMorpher.app/Contents/Resources/ є:
  - app.py, resources_rc.py, icons.qrc, first_run_dialog.py, README.md, INSTALL.md, requirements.txt, TROUBLESHOOTING.md, FAQ.md
  - icon.icns
  - system_prompts/ (шаблони)
  - python_env/ (скопійований venv з усіма залежностями)

### 4. Створення DMG
```bash
hdiutil create -volname "WebMorpher" -srcfolder "WebMorpher.app" -ov -format UDZO "WebMorpher.dmg"
```

---

## Основні функції

- 🔑 Безпечне зберігання та управління API ключем OpenAI
- 📝 Створення, редагування та видалення програм автоматизації
- ▶️ Запуск, пауза та зупинка виконання програм
- 🔄 Детальне відображення процесу виконання з кольоровим форматуванням
- 🔍 Режим дебагу з можливістю запуску Chrome DevTools
- 👤 Підтримка користувацьких профілів Chrome
- 🕶️ Можливість запуску браузера у фоновому режимі

## Технічні деталі

- 🐍 Python + PyQt5 для GUI
- 🤖 browser-use для автоматизації браузера
- 🧠 GPT-4 через OpenAI API
- 🎭 Playwright для керування браузером
- 💾 Конфігурація: ~/.webmorpher_config.json

## Системні вимоги
- macOS 10.15 або новіше
- Google Chrome або Chromium
- Інтернет
- OpenAI API ключ

---

## Пошук і усунення несправностей

- Якщо додаток не запускається — перевірте, чи дозволили запуск у Security & Privacy
- Якщо не знаходить бібліотеки — переконайтесь, що python_env скопійований у Resources
- Якщо не працює браузер — перевірте, чи встановлений Chrome/Chromium
- Якщо не приймає API ключ — перевірте, чи він починається з sk-

---

## Приклади програм

### Пошук і збереження інформації
```
Зайди на сайт wikipedia.org, знайди статтю про Python (мову програмування), прочитай перший абзац і збережи його у текстовий файл на робочому столі.
```

### Взаємодія з веб-формами
```
Перейди на сайт openweathermap.org, введи в пошук "Київ", отримай дані про погоду і температуру на наступні 5 днів.
``` 