import sys
import os
import json
import asyncio
import socket
import subprocess
import time
from functools import partial
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QTextEdit, QLabel, QLineEdit, QMessageBox, QDialog,
                            QListWidget, QTabWidget, QSplitter, QFrame, QFileDialog, QCheckBox,
                            QStyleFactory)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QObject, QRect, QPoint
from PyQt5.QtGui import QFont, QPalette, QColor, QFontDatabase
from browser_use import Agent, Browser, BrowserConfig
from langchain_openai import ChatOpenAI
from tempfile import gettempdir

# Определяем корневую директорию приложения
if getattr(sys, 'frozen', False):
    # Если приложение запущено из .app бандла
    APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(sys.executable)))
    RESOURCES_ROOT = os.path.join(APP_ROOT, 'Resources')
else:
    # Если приложение запущено из исходного кода
    APP_ROOT = os.path.dirname(os.path.abspath(__file__))
    RESOURCES_ROOT = APP_ROOT

# Шлях до файлу з налаштуваннями
CONFIG_FILE = os.path.expanduser("~/.webmorpher_config.json")
# Шлях до директорії профілю браузера
BROWSER_PROFILE_DIR = os.path.expanduser("~/.webmorpher_browser_profile")

def get_default_chrome_profile():
    """Визначення шляху до стандартного профілю користувача Chrome/Chromium"""
    user_profile_dir = None
    
    if sys.platform == 'darwin':  # macOS
        # Шлях до стандартного профілю Chrome на macOS
        chrome_profile_alt = os.path.expanduser("~/Library/Application Support/Google/Chrome")
        
        # Перевіряємо наявність каталогу
        if os.path.exists(chrome_profile_alt) and os.path.isdir(chrome_profile_alt):
            user_profile_dir = chrome_profile_alt
    elif sys.platform.startswith('win'):  # Windows
        # Шлях до стандартного профілю Chrome на Windows
        chrome_profile = os.path.join(os.environ.get('LOCALAPPDATA', ''), 
                                     "Google", "Chrome", "User Data")
        if os.path.exists(chrome_profile) and os.path.isdir(chrome_profile):
            user_profile_dir = chrome_profile
    elif sys.platform.startswith('linux'):  # Linux
        # Шлях до стандартного профілю Chrome на Linux
        chrome_profile = os.path.expanduser("~/.config/google-chrome")
        if os.path.exists(chrome_profile) and os.path.isdir(chrome_profile):
            user_profile_dir = chrome_profile
    
    return user_profile_dir

class BrowserUseRunner(QThread):
    """Клас для запуску browser-use у окремому потоці"""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)
    
    def __init__(self, api_key, task, headless=False, debug_port=None, user_profile_dir=None):
        super().__init__()
        self.api_key = api_key
        self.task = task
        self.headless = headless
        self.debug_port = debug_port
        self.user_profile_dir = user_profile_dir
        self._is_paused = False
        self._is_stopped = False
        self.agent = None
    
    def run(self):
        """Запуск browser-use агента"""
        try:
            os.environ["OPENAI_API_KEY"] = self.api_key
            
            # Ініціалізація ChatOpenAI моделі
            llm = ChatOpenAI(model="gpt-4o")
            
            # Створення браузера з відповідними параметрами
            if self.debug_port:
                # Для режиму дебагу використовуємо cdp_url
                browser_config = BrowserConfig(cdp_url=f"http://localhost:{self.debug_port}")
            else:
                # Шлях до Google Chrome на macOS
                chrome_paths = [
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # Стандартный путь
                    os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),  # Пользовательские приложения
                    "/Applications/Chromium.app/Contents/MacOS/Chromium",  # Chromium как запасной вариант
                ]
                
                # Находим первый существующий браузер
                chrome_path = None
                for path in chrome_paths:
                    if os.path.exists(path):
                        chrome_path = path
                        break
                
                if not chrome_path:
                    raise Exception("Не знайдено Google Chrome або Chromium. Будь ласка, встановіть один з браузерів.")
                
                # Параметры конфигурации браузера
                browser_config_params = {
                    'headless': self.headless,
                    'browser_binary_path': chrome_path,
                }
                
                # Если задан каталог профиля пользователя, используем его
                if self.user_profile_dir:
                    browser_config_params['user_data_dir'] = self.user_profile_dir
                
                # Для звичайного режиму використовуємо browser_binary_path и user_data_dir
                browser_config = BrowserConfig(**browser_config_params)
                
            browser = Browser(config=browser_config)
            
            # Створення агента з callback для логування
            self.agent = Agent(
                task=self.task,
                llm=llm,
                browser=browser,
                register_new_step_callback=self._on_new_step
            )
            
            # Запускаємо агента в асинхронному режимі
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            if not self._is_stopped:
                self.log_signal.emit("Запуск браузера та ініціалізація агента...")
                result = loop.run_until_complete(self._run_with_pause_check())
                self.log_signal.emit("Виконання завершено!")
                self.finished_signal.emit()
        
        except Exception as e:
            self.error_signal.emit(f"Помилка: {str(e)}")
    
    async def _run_with_pause_check(self):
        """Запуск агента з можливістю паузи"""
        try:
            # Запускаємо агента
            result = await self.agent.run()
            return result
        except Exception as e:
            self.error_signal.emit(f"Помилка під час виконання: {str(e)}")
            return None
    
    async def _on_new_step(self, state, output, step_index):
        """Колбек для логування кроків агента"""
        # Додаємо інформацію з AgentBrain
        if hasattr(output, 'current_state'):
            brain = output.current_state
            if brain.next_goal:
                self.log_signal.emit(f"🎯 Наступна ціль: {brain.next_goal}")
            if brain.evaluation_previous_goal:
                self.log_signal.emit(f"✓ Результат: {brain.evaluation_previous_goal}")
        
        # Стандартні статуси
        action_type = getattr(output, 'action_type', None)
        content = getattr(output, 'content', None)
        
        if action_type == "thinking":
            self.log_signal.emit(f"🤔 Модель думає: {content}")
        elif action_type == "browser_action":
            self.log_signal.emit(f"🌐 Браузер: {content}")
        elif action_type == "agent_action":
            self.log_signal.emit(f"🤖 Агент: {content}")
        elif action_type == "error":
            self.log_signal.emit(f"❌ Помилка: {content}")
        elif content:
            self.log_signal.emit(f"{action_type}: {content}")
        
        # Перевіряємо чи є пауза
        while self._is_paused and not self._is_stopped:
            await asyncio.sleep(0.1)  # Маленька затримка, щоб не навантажувати процесор
        
        # Якщо зупинено, піднімаємо виключення для зупинки агента
        if self._is_stopped:
            raise Exception("Виконання зупинено користувачем")
    
    def pause(self):
        """Призупинення виконання"""
        self._is_paused = True
        self.log_signal.emit("⏸️ Виконання призупинено...")
    
    def resume(self):
        """Відновлення виконання"""
        self._is_paused = False
        self.log_signal.emit("▶️ Виконання відновлено...")
    
    def stop(self):
        """Зупинка виконання"""
        self._is_stopped = True
        self._is_paused = False
        self.log_signal.emit("⏹️ Виконання зупинено!")

def find_free_port():
    """Знайти вільний порт для запуску дебаг-сервера"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def launch_debug_browser(port=9222, use_user_profile=True, user_profile_dir=None):
    """Запустити браузер у режимі дебагу на вказаному порті"""
    # Шлях до Chrome на macOS
    if sys.platform == 'darwin':  # macOS
        chrome_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # Стандартный путь
            os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),  # Пользовательские приложения
            "/Applications/Chromium.app/Contents/MacOS/Chromium",  # Chromium как запасной вариант
        ]
        
        # Находим первый существующий браузер
        chrome_path = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_path = path
                break
                
        if not chrome_path:
            raise Exception("Не знайдено Google Chrome або Chromium. Будь ласка, встановіть один з браузерів.")
            
        print(f"Використовуємо браузер за шляхом: {chrome_path}")
    else:
        # Для Linux та інших платформ
        chrome_path = "google-chrome"
    
    # Визначаємо директорію для профілю Chrome
    if use_user_profile and user_profile_dir:
        # Використовуємо профіль користувача
        debug_profile_dir = user_profile_dir
        print(f"Використовуємо профіль користувача для дебагу: {debug_profile_dir}")
    else:
        # Використовуємо тимчасову директорію для профілю Chrome
        debug_profile_dir = os.path.join(gettempdir(), f"chrome-debug-{port}")
        os.makedirs(debug_profile_dir, exist_ok=True)
    
    cmd = [
        chrome_path,
        f"--remote-debugging-port={port}",
        "--no-first-run",
        "--no-default-browser-check",
        f"--user-data-dir={debug_profile_dir}",
        "--disable-application-cache",  # Відключаємо кеш для зменшення конфліктів
        "about:blank"
    ]
    
    print(f"Запускаємо команду: {' '.join(cmd)}")
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Браузер запущено з PID: {process.pid}")
        
        # Перевіряємо, що браузер справді працює
        time.sleep(2)  # Чекаємо, щоб браузер встиг запуститися
        
        # Перевіряємо, що процес досі активний
        if process.poll() is not None:
            error = process.stderr.read().decode('utf-8', errors='ignore')
            raise Exception(f"Браузер завершився з кодом {process.returncode}. Помилка: {error}")
            
        return process, port
    except Exception as e:
        raise Exception(f"Не вдалося запустити браузер: {str(e)}")

class ApiKeyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Введіть API ключ")
        self.setFixedSize(400, 150)
        self.api_key = ""
        
        layout = QVBoxLayout()
        
        # Інформаційне повідомлення
        info_label = QLabel("Для роботи програми потрібен API ключ OpenAI.\nВведіть ваш ключ для продовження:")
        layout.addWidget(info_label)
        
        # Поле для вводу ключа
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("sk-...")
        layout.addWidget(self.key_input)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        self.save_button = QPushButton("Зберегти")
        self.save_button.clicked.connect(self.accept_key)
        
        self.cancel_button = QPushButton("Скасувати")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def accept_key(self):
        api_key = self.key_input.text().strip()
        if not api_key or not api_key.startswith("sk-"):
            QMessageBox.warning(self, "Помилка", "Введіть коректний API ключ, що починається з 'sk-'")
            return
        
        self.api_key = api_key
        self.accept()

class ProgramEditorDialog(QDialog):
    def __init__(self, program_name="", program_code="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактор програми")
        self.setMinimumSize(600, 400)
        
        self.layout = QVBoxLayout()
        
        # Назва програми
        name_layout = QHBoxLayout()
        name_label = QLabel("Назва програми:")
        self.name_input = QLineEdit(program_name)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        self.layout.addLayout(name_layout)
        
        # Редактор коду
        code_label = QLabel("Код програми:")
        self.code_editor = QTextEdit()
        self.code_editor.setPlainText(program_code)
        self.layout.addWidget(code_label)
        self.layout.addWidget(self.code_editor)
        
        # Кнопки
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Зберегти")
        self.save_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("Скасувати")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        self.layout.addLayout(button_layout)
        self.setLayout(self.layout)
    
    def get_program_data(self):
        return {
            "name": self.name_input.text().strip(),
            "code": self.code_editor.toPlainText().strip()
        }

class WebMorpherApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # Встановлюємо нативний стиль macOS
        QApplication.setStyle(QStyleFactory.create("macintosh"))
        
        # Завантажуємо системний шрифт SF Pro
        font_id = QFontDatabase.addApplicationFont(":/System/Library/Fonts/SFPro.ttf")
        if font_id != -1:
            self.default_font = QFont("SF Pro", 13)
            QApplication.setFont(self.default_font)
        
        self.api_key = ""
        self.programs = []
        self.current_program = None
        self.program_running = False
        self.browser_runner = None
        self.debug_browser_process = None
        self.debug_port = None
        self.chrome_profile_path = get_default_chrome_profile()
        self.current_status = None
        
        # Налаштування вікна
        self.setWindowTitle("WebMorpher")
        self.setGeometry(100, 100, 1200, 800)  # Збільшуємо розмір для кращого UX
        
        # Налаштування прозорості та матеріалів
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QMainWindow {
                background-color: rgba(255, 255, 255, 0.95);
            }
            QWidget {
                font-family: "SF Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }
            /* Стилі для світлої теми */
            QMainWindow[lightTheme="true"] {
                background-color: rgba(255, 255, 255, 0.95);
                color: #000000;
            }
            /* Стилі для темної теми */
            QMainWindow[lightTheme="false"] {
                background-color: rgba(28, 28, 28, 0.95);
                color: #FFFFFF;
            }
            /* Базові відступи */
            QWidget {
                margin: 0;
                padding: 0;
            }
            /* Стиль для кнопок */
            QPushButton {
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                background-color: #007AFF;
                color: white;
                margin: 4px;
            }
            QPushButton:hover {
                background-color: #0063CC;
            }
            QPushButton:pressed {
                background-color: #004999;
            }
            QPushButton:disabled {
                background-color: #E5E5E5;
                color: #999999;
            }
            /* Стиль для полів вводу */
            QLineEdit, QTextEdit {
                border: 1px solid #E5E5E5;
                border-radius: 6px;
                padding: 8px;
                background-color: rgba(255, 255, 255, 0.8);
            }
            /* Стиль для списків */
            QListWidget {
                border: 1px solid #E5E5E5;
                border-radius: 6px;
                background-color: rgba(255, 255, 255, 0.8);
            }
            /* Стиль для вкладок */
            QTabWidget::pane {
                border: 1px solid #E5E5E5;
                border-radius: 6px;
                background-color: rgba(255, 255, 255, 0.8);
            }
            QTabBar::tab {
                padding: 8px 16px;
                margin: 4px 2px;
                border-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #007AFF;
                color: white;
            }
        """)
        
        # Визначаємо тему системи
        self.update_theme()
        
        # Спочатку перевіряємо наявність API ключа
        self.load_config()
        if not self.check_api_key():
            sys.exit()
            
        self.setup_ui()
        
    def update_theme(self):
        """Оновлення теми відповідно до системних налаштувань"""
        # В майбутньому тут буде перевірка системної теми
        # Наразі просто встановлюємо світлу тему
        self.setProperty("lightTheme", True)
        self.style().unpolish(self)
        self.style().polish(self)
    
    def load_config(self):
        """Завантаження конфігурації з файлу"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.api_key = config.get('api_key', '')
                    self.programs = config.get('programs', [])
            except Exception as e:
                print(f"Помилка завантаження конфігурації: {e}")
    
    def save_config(self):
        """Збереження конфігурації у файл"""
        config = {
            'api_key': self.api_key,
            'programs': self.programs
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Помилка збереження конфігурації: {e}")
    
    def check_api_key(self):
        """Перевірка наявності API ключа"""
        if not self.api_key:
            dialog = ApiKeyDialog(self)
            # Убедиться, что поле ввода пустое
            dialog.key_input.setText("")  
            if dialog.exec_():
                self.api_key = dialog.api_key
                self.save_config()
                return True
            else:
                return False
        return True
            
    def setup_ui(self):
        """Налаштування інтерфейсу користувача"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)  # Відступи згідно гайдлайнів
        main_layout.setSpacing(16)  # Відступ між елементами
        
        # Верхня панель з кнопками керування
        control_layout = QHBoxLayout()
        
        self.new_button = QPushButton("Нова програма")
        self.new_button.clicked.connect(self.create_program)
        
        self.edit_button = QPushButton("Редагувати")
        self.edit_button.clicked.connect(self.edit_program)
        
        self.delete_button = QPushButton("Видалити")
        self.delete_button.clicked.connect(self.delete_program)
        
        self.run_button = QPushButton("Запустити")
        self.run_button.clicked.connect(self.run_program)
        
        self.pause_button = QPushButton("Пауза")
        self.pause_button.clicked.connect(self.pause_program)
        self.pause_button.setEnabled(False)
        
        self.stop_button = QPushButton("Зупинити")
        self.stop_button.clicked.connect(self.stop_program)
        self.stop_button.setEnabled(False)
        
        self.debug_button = QPushButton("Режим дебагу")
        self.debug_button.clicked.connect(self.launch_debug_browser)
        
        self.api_button = QPushButton("Змінити API ключ")
        self.api_button.clicked.connect(self.change_api_key)
        
        control_layout.addWidget(self.new_button)
        control_layout.addWidget(self.edit_button)
        control_layout.addWidget(self.delete_button)
        control_layout.addWidget(self.run_button)
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.debug_button)
        control_layout.addWidget(self.api_button)
        
        main_layout.addLayout(control_layout)
        
        # Опція фонового режиму
        headless_layout = QHBoxLayout()
        self.headless_checkbox = QCheckBox("Запускати браузер у фоновому режимі")
        headless_layout.addWidget(self.headless_checkbox)
        
        # Опція використання профілю користувача
        self.use_user_profile_checkbox = QCheckBox("Використовувати поточний профіль браузера")
        self.use_user_profile_checkbox.setToolTip("Запускати з профілем, де збережені паролі, історія та налаштування")
        if not self.chrome_profile_path:
            self.use_user_profile_checkbox.setEnabled(False)
            self.use_user_profile_checkbox.setToolTip("Профіль Chrome не знайдено")
        else:
            # Если профиль найден, активируем опцию по умолчанию
            self.use_user_profile_checkbox.setChecked(True)
        
        headless_layout.addWidget(self.use_user_profile_checkbox)
        headless_layout.addStretch()
        main_layout.addLayout(headless_layout)
        
        # Розділювач для списку програм та вкладок з результатами
        splitter = QSplitter(Qt.Horizontal)
        
        # Список програм
        program_frame = QFrame()
        program_layout = QVBoxLayout(program_frame)
        
        program_label = QLabel("Доступні програми:")
        self.program_list = QListWidget()
        self.program_list.currentRowChanged.connect(self.on_program_selected)
        
        program_layout.addWidget(program_label)
        program_layout.addWidget(self.program_list)
        
        splitter.addWidget(program_frame)
        
        # Вкладки з редактором та результатами
        tab_frame = QFrame()
        tab_layout = QVBoxLayout(tab_frame)
        
        self.tabs = QTabWidget()
        
        # Вкладка перегляду програми
        self.view_tab = QWidget()
        view_layout = QVBoxLayout(self.view_tab)
        
        self.code_view = QTextEdit()
        self.code_view.setReadOnly(True)
        view_layout.addWidget(self.code_view)
        
        # Вкладка результатів
        self.result_tab = QWidget()
        result_layout = QVBoxLayout(self.result_tab)
        
        # Панель статуса
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        status_layout = QVBoxLayout(status_frame)
        
        # Заголовок статуса
        status_header = QLabel("Поточний статус:")
        status_header.setFont(QFont("", 12, QFont.Bold))
        status_layout.addWidget(status_header)
        
        # Текст статуса
        self.status_label = QLabel("Очікування запуску...")
        self.status_label.setFont(QFont("", 11))
        self.status_label.setStyleSheet("padding: 10px;")
        status_layout.addWidget(self.status_label)
        
        result_layout.addWidget(status_frame)
        
        # Лог результатів
        self.result_view = QTextEdit()
        self.result_view.setReadOnly(True)
        result_layout.addWidget(self.result_view)
        
        self.tabs.addTab(self.view_tab, "Програма")
        self.tabs.addTab(self.result_tab, "Результати")
        
        tab_layout.addWidget(self.tabs)
        
        splitter.addWidget(tab_frame)
        
        # Встановлюємо пропорції розділювача
        splitter.setSizes([200, 800])
        
        main_layout.addWidget(splitter)
        
        # Статус бар
        self.statusBar().showMessage("Готовий до роботи")
        
        # Завантаження списку програм
        self.load_program_list()
    
    def load_program_list(self):
        """Завантаження списку програм"""
        self.program_list.clear()
        for program in self.programs:
            self.program_list.addItem(program.get("name", "Без назви"))
    
    def on_program_selected(self, index):
        """Обробка вибору програми в списку"""
        if index >= 0 and index < len(self.programs):
            program = self.programs[index]
            self.current_program = program
            self.code_view.setPlainText(program.get("code", ""))
            self.result_view.clear()
            self.status_label.setText("Обрано програму...")
            self.status_label.setStyleSheet("padding: 10px; color: black;")
        else:
            self.current_program = None
            self.code_view.clear()
            self.result_view.clear()
    
    def create_program(self):
        """Створення нової програми"""
        dialog = ProgramEditorDialog(parent=self)
        if dialog.exec_():
            program_data = dialog.get_program_data()
            if not program_data["name"]:
                QMessageBox.warning(self, "Помилка", "Назва програми не може бути порожньою")
                return
            
            self.programs.append(program_data)
            self.save_config()
            self.load_program_list()
            self.status_label.setText("Створено нову програму...")
            self.status_label.setStyleSheet("padding: 10px; color: black;")
    
    def edit_program(self):
        """Редагування обраної програми"""
        if not self.current_program:
            QMessageBox.warning(self, "Помилка", "Спочатку оберіть програму для редагування")
            return
        
        index = self.program_list.currentRow()
        dialog = ProgramEditorDialog(
            program_name=self.current_program.get("name", ""),
            program_code=self.current_program.get("code", ""),
            parent=self
        )
        
        if dialog.exec_():
            program_data = dialog.get_program_data()
            if not program_data["name"]:
                QMessageBox.warning(self, "Помилка", "Назва програми не може бути порожньою")
                return
            
            self.programs[index] = program_data
            self.save_config()
            self.load_program_list()
            self.program_list.setCurrentRow(index)
            self.status_label.setText("Програму оновлено...")
            self.status_label.setStyleSheet("padding: 10px; color: black;")
    
    def delete_program(self):
        """Видалення обраної програми"""
        if not self.current_program:
            QMessageBox.warning(self, "Помилка", "Спочатку оберіть програму для видалення")
            return
        
        index = self.program_list.currentRow()
        program_name = self.current_program.get("name", "Без назви")
        
        reply = QMessageBox.question(
            self, "Підтвердження", 
            f"Ви впевнені, що хочете видалити програму '{program_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.programs.pop(index)
            self.save_config()
            self.load_program_list()
            self.status_label.setText("Програму видалено...")
            self.status_label.setStyleSheet("padding: 10px; color: black;")
    
    def run_program(self):
        """Запуск обраної програми"""
        if not self.current_program:
            QMessageBox.warning(self, "Помилка", "Спочатку оберіть програму для запуску")
            return
        
        program_name = self.current_program.get("name", "Без назви")
        program_code = self.current_program.get("code", "")
        
        if not program_code.strip():
            QMessageBox.warning(self, "Помилка", "Програма не містить коду для виконання")
            return
            
        self.program_running = True
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.run_button.setEnabled(False)
        
        # Перемикаємося на вкладку результатів
        self.tabs.setCurrentIndex(1)
        
        # Очищаємо вікно результатів і статус
        self.result_view.clear()
        self.status_label.setText("Запуск програми...")
        self.status_label.setStyleSheet("padding: 10px; color: black;")
        self.result_view.append(f"Запуск програми: {program_name}")
        
        # Визначаємо, який профіль використовувати
        use_user_profile = self.use_user_profile_checkbox.isChecked() and self.chrome_profile_path
        user_profile = self.chrome_profile_path if use_user_profile else None
        
        # Повідомлення про профіль
        if use_user_profile:
            self.result_view.append(f"Використовуємо профіль користувача: {self.chrome_profile_path}")
        
        # Створюємо та запускаємо потік для browser-use
        headless = self.headless_checkbox.isChecked()
        self.browser_runner = BrowserUseRunner(
            api_key=self.api_key,
            task=program_code,
            headless=headless,
            debug_port=self.debug_port,
            user_profile_dir=user_profile
        )
        
        # Підключаємо сигнали
        self.browser_runner.log_signal.connect(self.on_browser_log)
        self.browser_runner.error_signal.connect(self.on_browser_error)
        self.browser_runner.finished_signal.connect(self.on_browser_finished)
        
        # Запускаємо виконання
        self.browser_runner.start()
        
        self.status_label.setText("Запущено програму...")
        self.status_label.setStyleSheet("padding: 10px; color: black;")
    
    def on_browser_log(self, message):
        """Обробник логів від browser-use"""
        # Додаємо повідомлення в лог з відповідним форматуванням
        if "🎯 Наступна ціль:" in message:
            self.result_view.append(f"<span style='color: #2196F3;'>{message}</span>")
        elif "✓ Результат:" in message:
            self.result_view.append(f"<span style='color: #4CAF50;'>{message}</span>")
        elif "🤔 Модель думає:" in message:
            self.result_view.append(f"<span style='color: #FF9800;'>{message}</span>")
        elif "🌐 Браузер:" in message:
            self.result_view.append(f"<span style='color: #9C27B0;'>{message}</span>")
        elif "❌ Помилка:" in message:
            self.result_view.append(f"<span style='color: #F44336;'>{message}</span>")
        else:
            self.result_view.append(message)
        
        # Оновлюємо статус у верхньому полі
        self.status_label.setText(message)
        if "🎯 Наступна ціль:" in message:
            self.status_label.setStyleSheet("padding: 10px; color: #2196F3;")
        elif "✓ Результат:" in message:
            self.status_label.setStyleSheet("padding: 10px; color: #4CAF50;")
        elif "🤔 Модель думає:" in message:
            self.status_label.setStyleSheet("padding: 10px; color: #FF9800;")
        elif "🌐 Браузер:" in message:
            self.status_label.setStyleSheet("padding: 10px; color: #9C27B0;")
        elif "❌ Помилка:" in message:
            self.status_label.setStyleSheet("padding: 10px; color: #F44336;")
        else:
            self.status_label.setStyleSheet("padding: 10px; color: black;")
        
        # Прокрутка до нижнього краю
        self.result_view.verticalScrollBar().setValue(
            self.result_view.verticalScrollBar().maximum()
        )
    
    def on_browser_error(self, error_message):
        """Обробник помилок від browser-use"""
        self.result_view.append(f"<span style='color: red;'>{error_message}</span>")
        # Оновлюємо стан інтерфейсу
        self.program_running = False
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.run_button.setEnabled(True)
    
    def on_browser_finished(self):
        """Обробник завершення виконання browser-use"""
        self.result_view.append("Виконання програми завершено.")
        # Оновлюємо стан інтерфейсу
        self.program_running = False
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.run_button.setEnabled(True)
    
    def pause_program(self):
        """Призупинення виконання програми"""
        if not self.program_running or not self.browser_runner:
            return
            
        if self.browser_runner._is_paused:
            # Відновлення виконання
            self.browser_runner.resume()
            self.pause_button.setText("Пауза")
        else:
            # Призупинення виконання
            self.browser_runner.pause()
            self.pause_button.setText("Продовжити")
        
        self.status_label.setText("Програму призупинено/відновлено...")
        self.status_label.setStyleSheet("padding: 10px; color: black;")
    
    def stop_program(self):
        """Зупинка виконання програми"""
        if not self.program_running or not self.browser_runner:
            return
            
        # Зупиняємо виконання
        self.browser_runner.stop()
        
        # Оновлюємо стан інтерфейсу
        self.program_running = False
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.run_button.setEnabled(True)
        self.pause_button.setText("Пауза")
        
        self.status_label.setText("Програму зупинено...")
        self.status_label.setStyleSheet("padding: 10px; color: black;")
    
    def launch_debug_browser(self):
        """Запуск браузера в режимі дебагу"""
        try:
            # Якщо браузер вже запущено, просто показуємо інформацію
            if self.debug_browser_process and self.debug_port:
                QMessageBox.information(
                    self, 
                    "Браузер у режимі дебагу", 
                    f"Браузер вже запущено на порту {self.debug_port}"
                )
                return
                
            # Використовуємо фіксований порт 9222
            port = 9222
            
            # Перевіряємо, чи не зайнятий порт
            try:
                socket.create_connection(("localhost", port), timeout=1).close()
                reply = QMessageBox.question(
                    self, "Увага", 
                    f"Порт {port} вже використовується. Можливо, Chrome вже запущено. Спробувати все одно?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
            except (socket.timeout, socket.error):
                # Порт вільний, продовжуємо
                pass
                
            # Зберігаємо логи у тимчасовий файл
            log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_debug.log")
            with open(log_file, "w") as f:
                f.write(f"Запуск Chrome на порту {port} в {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                
            # Визначаємо, який профіль використовувати
            use_user_profile = self.use_user_profile_checkbox.isChecked() and self.chrome_profile_path
            user_profile = self.chrome_profile_path if use_user_profile else None
            
            # Запускаємо браузер
            process, port = launch_debug_browser(port, use_user_profile=use_user_profile, user_profile_dir=user_profile)
            
            # Зберігаємо процес і порт
            self.debug_browser_process = process
            self.debug_port = port
            
            # Перевіряємо, що запустився саме Chrome
            try:
                import requests
                import json
                response = requests.get(f"http://localhost:{port}/json/version")
                browser_info = json.loads(response.text)
                browser_name = browser_info.get("Browser", "")
                
                with open(log_file, "a") as f:
                    f.write(f"Підключено до браузера: {browser_name}\n")
                    
                if "Chrome" in browser_name:
                    QMessageBox.information(
                        self, 
                        "Браузер у режимі дебагу", 
                        f"Google Chrome запущено на порту {port}\nІнформація про браузер: {browser_name}"
                    )
                else:
                    QMessageBox.warning(
                        self, 
                        "Увага", 
                        f"Запущено браузер, але це не Chrome: {browser_name}. Можливі проблеми з сумісністю."
                    )
            except Exception as e:
                with open(log_file, "a") as f:
                    f.write(f"Помилка перевірки браузера: {str(e)}\n")
                QMessageBox.information(
                    self, 
                    "Браузер у режимі дебагу", 
                    f"Браузер запущено на порту {port}, але не вдалося перевірити тип браузера."
                )
            
            self.status_label.setText(f"Google Chrome у режимі дебагу запущено на порту {port}")
        
        except Exception as e:
            QMessageBox.warning(
                self, 
                "Помилка", 
                f"Не вдалося запустити браузер у режимі дебагу: {str(e)}"
            )
    
    def change_api_key(self):
        """Зміна API ключа"""
        dialog = ApiKeyDialog(self)
        dialog.key_input.setText("")  # Поле ввода всегда пустое, независимо от текущего значения ключа
        
        if dialog.exec_():
            self.api_key = dialog.api_key
            self.save_config()
            self.status_label.setText("API ключ оновлено")

    def closeEvent(self, event):
        """Обробка закриття додатку"""
        # Перевіряємо, чи виконується програма
        if self.program_running:
            reply = QMessageBox.question(
                self, "Підтвердження", 
                "Програма все ще виконується. Ви впевнені, що хочете вийти?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.stop_program()
                event.accept()
            else:
                event.ignore()
                return
        
        # Закриваємо дебаг-браузер, якщо він запущений
        if self.debug_browser_process:
            try:
                self.debug_browser_process.terminate()
            except:
                pass
                
        # Зберігаємо конфігурацію перед виходом
        self.save_config()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Проверяем на наличие аргумента для сброса API ключа
    if len(sys.argv) > 1 and sys.argv[1] == "--reset-api-key":
        # Если конфигурационный файл существует, удаляем API ключ
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    # Удаляем ключ API, сохраняя программы
                    config['api_key'] = ""
                with open(CONFIG_FILE, 'w') as f:
                    json.dump(config, f)
                print("API ключ сброшен!")
            except Exception as e:
                print(f"Ошибка при сбросе API ключа: {e}")
    
    window = WebMorpherApp()
    window.show()
    sys.exit(app.exec_()) 