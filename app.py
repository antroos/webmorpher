import sys
import os
import json
import asyncio
import socket
import subprocess
import time
from functools import partial

# Add environment variables to prevent OpenBLAS threading issues
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QTextEdit, QLabel, QLineEdit, QMessageBox, QDialog,
                            QListWidget, QTabWidget, QSplitter, QFrame, QFileDialog, QCheckBox,
                            QStyleFactory, QGroupBox, QToolButton)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QObject, QRect, QPoint, QPropertyAnimation
from PyQt5.QtGui import QFont, QPalette, QColor, QFontDatabase, QIcon
from browser_use import Agent, Browser, BrowserConfig
from langchain_openai import ChatOpenAI
from tempfile import gettempdir
import resources_rc  # Импортируем скомпилированный файл ресурсов

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

# Функція для коректного визначення шляху до іконок
def get_icon_path(icon_name):
    """Визначення правильного шляху до іконки в залежності від режиму запуску"""
    # В режимі розробки іконки знаходяться в папці icons/svg
    dev_path = os.path.join(RESOURCES_ROOT, 'icons', 'svg', icon_name)
    
    # В режимі додатка іконки знаходяться в Resources/icons/svg
    app_path = os.path.join(RESOURCES_ROOT, 'icons', 'svg', icon_name)
    
    # Перевіряємо, який шлях існує
    if os.path.exists(dev_path):
        return dev_path
    elif os.path.exists(app_path):
        return app_path
    else:
        print(f"ПОПЕРЕДЖЕННЯ: Іконка не знайдена: {icon_name}")
        # Використовуємо іконки з ресурсів
        return f":/icons/svg/{icon_name}"

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
            error_msg = f"Помилка: {str(e)}"
            
            # Check if it might be an OpenBLAS threading issue
            if "EXC_BAD_ACCESS" in str(e) or "segmentation fault" in str(e).lower():
                error_msg += "\n\nМожливо, це пов'язано з проблемою багатопоточності в NumPy/OpenBLAS."
                error_msg += "\nСпробуйте перезапустити програму та використовувати фоновий режим браузера."
            
            self.error_signal.emit(error_msg)
    
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
        
        # Основні налаштування вікна
        self.setWindowTitle("WebMorpher")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(1000, 700)
        
        # Встановлюємо стиль вікна для macOS
        if sys.platform == 'darwin':
            self.setWindowFlags(Qt.Window | Qt.WindowFullscreenButtonHint | Qt.WindowTitleHint | 
                               Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
            # Активуємо прозорість вікна
            self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Ініціалізація змінних
        self.programs = []
        self.current_program = None
        self.program_running = False
        self.browser_runner = None
        self.is_paused = False
        
        # Визначаємо шлях до профілю Chrome
        self.chrome_profile_path = get_default_chrome_profile()
        
        # Налаштування теми
        self.dark_mode = False  # За замовчуванням світла тема
        self.update_theme()
        
        # Завантаження конфігурації
        self.api_key = ""
        self.load_config()
        
        # Перевірка наявності API ключа
        if not self.check_api_key():
            self.show()  # Показуємо вікно перед діалогом, щоб воно було правильно центровано
        
        # Налаштування інтерфейсу користувача
        self.setup_ui()
        
        # Показуємо вікно
        self.show()
        
    def update_theme(self):
        """Оновлення теми додатку (світла/темна)"""
        if self.dark_mode:
            # Темна тема
            self.setStyleSheet("""
                QMainWindow {
                    background-color: rgba(40, 40, 40, 0.85);
                    border-radius: 10px;
                }
                #mainContainer {
                    background-color: rgba(50, 50, 50, 0.95);
                    border-radius: 15px;
                    border: 1px solid rgba(70, 70, 70, 0.3);
                }
                #topPanel {
                    background-color: rgba(45, 45, 45, 0.95);
                    border-bottom: 1px solid rgba(70, 70, 70, 0.3);
                }
                QToolButton {
                    color: #0A84FF;
                }
                QToolButton:hover {
                    background-color: rgba(10, 132, 255, 0.1);
                }
                QToolButton:pressed {
                    background-color: rgba(10, 132, 255, 0.2);
                }
                QToolButton:disabled {
                    color: rgba(10, 132, 255, 0.5);
                }
                #sidebar {
                    background-color: rgba(45, 45, 45, 0.8);
                    border-right: 1px solid rgba(70, 70, 70, 0.3);
                }
                QLabel {
                    color: #FFFFFF;
                }
                QListWidget {
                    background-color: rgba(60, 60, 60, 0.5);
                    border: 1px solid rgba(80, 80, 80, 0.3);
                    color: #FFFFFF;
                }
                QListWidget::item:hover {
                    background-color: rgba(10, 132, 255, 0.1);
                }
                QListWidget::item:selected {
                    background-color: rgba(10, 132, 255, 0.2);
                    color: #0A84FF;
                }
                QGroupBox {
                    border: 1px solid rgba(80, 80, 80, 0.3);
                    background-color: rgba(60, 60, 60, 0.5);
                    color: #FFFFFF;
                }
                QCheckBox {
                    color: #FFFFFF;
                }
                QTabBar::tab {
                    background-color: rgba(60, 60, 60, 0.7);
                    color: #FFFFFF;
                }
                QTabBar::tab:selected {
                    background-color: rgba(10, 132, 255, 0.8);
                    color: white;
                }
                QTextEdit {
                    background-color: rgba(60, 60, 60, 0.7);
                    color: #FFFFFF;
                    border: 1px solid rgba(80, 80, 80, 0.3);
                }
                QStatusBar {
                    background-color: rgba(45, 45, 45, 0.9);
                    color: #FFFFFF;
                    border-top: 1px solid rgba(70, 70, 70, 0.3);
                }
            """)
        else:
            # Світла тема
            self.setStyleSheet("""
                QMainWindow {
                    background-color: rgba(240, 240, 240, 0.85);
                    border-radius: 10px;
                }
            """)
            # Решта стилів встановлюються в setup_ui
        
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
        
        # Основний макет з верхньою панеллю та головним контентом
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)  # Відступи для тіні та округлення
        main_layout.setSpacing(0)  # Прибираємо відступи між елементами
        
        # Контейнер з тінню та округленими кутами
        main_container = QFrame()
        main_container.setObjectName("mainContainer")
        main_container.setStyleSheet("""
            #mainContainer {
                background-color: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                border: 1px solid rgba(0, 0, 0, 0.1);
            }
        """)
        container_layout = QVBoxLayout(main_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # 1. ВЕРХНЯ ПАНЕЛЬ (Toolbar)
        top_panel = QFrame()
        top_panel.setObjectName("topPanel")
        top_panel.setStyleSheet("""
            #topPanel {
                background-color: rgba(248, 248, 248, 0.95);
                border-top-left-radius: 15px;
                border-top-right-radius: 15px;
                border-bottom: 1px solid rgba(0, 0, 0, 0.1);
                min-height: 70px;
                padding: 10px;
            }
        """)
        top_layout = QHBoxLayout(top_panel)
        top_layout.setContentsMargins(15, 5, 15, 5)
        
        # Кнопки у верхній панелі (тепер з іконками)
        # 1. Кнопка "Нова програма"
        self.new_button = QToolButton()
        self.new_button.setIcon(QIcon(get_icon_path("add.svg")))
        self.new_button.setText("Нова програма")
        self.new_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.new_button.setIconSize(QSize(32, 32))
        self.new_button.setMinimumWidth(80)
        self.new_button.clicked.connect(self.create_program)
        self.new_button.setStyleSheet("""
            QToolButton {
                border: none;
                color: #007AFF;
                padding: 6px;
                border-radius: 6px;
            }
            QToolButton:hover {
                background-color: rgba(0, 122, 255, 0.1);
            }
            QToolButton:pressed {
                background-color: rgba(0, 122, 255, 0.2);
            }
        """)
        
        # 2. Кнопка "Редагувати"
        self.edit_button = QToolButton()
        self.edit_button.setIcon(QIcon(get_icon_path("edit.svg")))
        self.edit_button.setText("Редагувати")
        self.edit_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.edit_button.setIconSize(QSize(32, 32))
        self.edit_button.setMinimumWidth(80)
        self.edit_button.clicked.connect(self.edit_program)
        self.edit_button.setStyleSheet("""
            QToolButton {
                border: none;
                color: #007AFF;
                padding: 6px;
                border-radius: 6px;
            }
            QToolButton:hover {
                background-color: rgba(0, 122, 255, 0.1);
            }
            QToolButton:pressed {
                background-color: rgba(0, 122, 255, 0.2);
            }
        """)
        
        # 3. Кнопка "Видалити"
        self.delete_button = QToolButton()
        self.delete_button.setIcon(QIcon(get_icon_path("delete.svg")))
        self.delete_button.setText("Видалити")
        self.delete_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.delete_button.setIconSize(QSize(32, 32))
        self.delete_button.setMinimumWidth(80)
        self.delete_button.clicked.connect(self.delete_program)
        self.delete_button.setStyleSheet("""
            QToolButton {
                border: none;
                color: #007AFF;
                padding: 6px;
                border-radius: 6px;
            }
            QToolButton:hover {
                background-color: rgba(0, 122, 255, 0.1);
            }
            QToolButton:pressed {
                background-color: rgba(0, 122, 255, 0.2);
            }
        """)
        
        # 4. Кнопка "Запустити"
        self.run_button = QToolButton()
        self.run_button.setIcon(QIcon(get_icon_path("play.svg")))
        self.run_button.setText("Запустити")
        self.run_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.run_button.setIconSize(QSize(32, 32))
        self.run_button.setMinimumWidth(80)
        self.run_button.clicked.connect(self.run_program)
        self.run_button.setStyleSheet("""
            QToolButton {
                border: none;
                color: #007AFF;
                padding: 6px;
                border-radius: 6px;
            }
            QToolButton:hover {
                background-color: rgba(0, 122, 255, 0.1);
            }
            QToolButton:pressed {
                background-color: rgba(0, 122, 255, 0.2);
            }
        """)
        
        # 5. Кнопка "Пауза"
        self.pause_button = QToolButton()
        self.pause_button.setIcon(QIcon(get_icon_path("pause.svg")))
        self.pause_button.setText("Пауза")
        self.pause_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.pause_button.setIconSize(QSize(32, 32))
        self.pause_button.setMinimumWidth(80)
        self.pause_button.clicked.connect(self.pause_program)
        self.pause_button.setEnabled(False)
        self.pause_button.setStyleSheet("""
            QToolButton {
                border: none;
                color: #007AFF;
                padding: 6px;
                border-radius: 6px;
            }
            QToolButton:hover {
                background-color: rgba(0, 122, 255, 0.1);
            }
            QToolButton:pressed {
                background-color: rgba(0, 122, 255, 0.2);
            }
            QToolButton:disabled {
                color: rgba(0, 122, 255, 0.5);
            }
        """)
        
        # 6. Кнопка "Зупинити"
        self.stop_button = QToolButton()
        self.stop_button.setIcon(QIcon(get_icon_path("stop.svg")))
        self.stop_button.setText("Зупинити")
        self.stop_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.stop_button.setIconSize(QSize(32, 32))
        self.stop_button.setMinimumWidth(80)
        self.stop_button.clicked.connect(self.stop_program)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QToolButton {
                border: none;
                color: #007AFF;
                padding: 6px;
                border-radius: 6px;
            }
            QToolButton:hover {
                background-color: rgba(0, 122, 255, 0.1);
            }
            QToolButton:pressed {
                background-color: rgba(0, 122, 255, 0.2);
            }
            QToolButton:disabled {
                color: rgba(0, 122, 255, 0.5);
            }
        """)
        
        # Розділювальна лінія
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: rgba(0, 0, 0, 0.1); margin: 5px 10px;")
        separator.setFixedWidth(1)
        separator.setFixedHeight(50)
        
        # 7. Кнопка "Змінити API ключ"
        self.api_button = QToolButton()
        self.api_button.setIcon(QIcon(get_icon_path("key.svg")))
        self.api_button.setText("API ключ")
        self.api_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.api_button.setIconSize(QSize(32, 32))
        self.api_button.setMinimumWidth(80)
        self.api_button.clicked.connect(self.change_api_key)
        self.api_button.setStyleSheet("""
            QToolButton {
                border: none;
                color: #007AFF;
                padding: 6px;
                border-radius: 6px;
            }
            QToolButton:hover {
                background-color: rgba(0, 122, 255, 0.1);
            }
            QToolButton:pressed {
                background-color: rgba(0, 122, 255, 0.2);
            }
        """)
        
        top_layout.addWidget(self.new_button)
        top_layout.addWidget(self.edit_button)
        top_layout.addWidget(self.delete_button)
        top_layout.addSpacing(10)
        top_layout.addWidget(self.run_button)
        top_layout.addWidget(self.pause_button)
        top_layout.addWidget(self.stop_button)
        top_layout.addWidget(separator)
        top_layout.addWidget(self.api_button)
        top_layout.addStretch()  # Пушуємо кнопки вліво
        
        container_layout.addWidget(top_panel)
        
        # 2. ОСНОВНИЙ КОНТЕНТ (з бічною панеллю та областю контенту)
        content_container = QWidget()
        content_layout = QHBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # 2.1 БІЧНА ПАНЕЛЬ
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setStyleSheet("""
            #sidebar {
                background-color: rgba(245, 245, 247, 0.8);
                border-right: 1px solid rgba(0, 0, 0, 0.1);
                min-width: 250px;
                max-width: 350px;
            }
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(15, 15, 15, 15)
        
        # Заголовок бічної панелі
        sidebar_title = QLabel("Доступні програми")
        sidebar_title.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 15px; color: #333;")
        sidebar_layout.addWidget(sidebar_title)
        
        # Список програм
        self.program_list = QListWidget()
        self.program_list.setStyleSheet("""
            QListWidget {
                background-color: rgba(250, 250, 250, 0.5);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 10px;
                padding: 5px;
                outline: none;
            }
            QListWidget::item {
                border-radius: 6px;
                padding: 10px;
                margin: 2px 0px;
            }
            QListWidget::item:hover {
                background-color: rgba(0, 122, 255, 0.1);
            }
            QListWidget::item:selected {
                background-color: rgba(0, 122, 255, 0.2);
                color: #007AFF;
            }
        """)
        self.program_list.currentRowChanged.connect(self.on_program_selected)
        sidebar_layout.addWidget(self.program_list)
        
        # Опції
        options_group = QGroupBox("Опції запуску")
        options_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: rgba(250, 250, 250, 0.5);
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                color: #333;
            }
        """)
        options_layout = QVBoxLayout(options_group)
        
        # Опція фонового режиму
        self.headless_checkbox = QCheckBox("Запускати браузер у фоновому режимі")
        self.headless_checkbox.setStyleSheet("font-size: 13px;")
        options_layout.addWidget(self.headless_checkbox)
        
        # Опція використання профілю користувача
        self.use_user_profile_checkbox = QCheckBox("Використовувати поточний профіль браузера")
        self.use_user_profile_checkbox.setToolTip("Запускати з профілем, де збережені паролі, історія та налаштування")
        self.use_user_profile_checkbox.setStyleSheet("font-size: 13px;")
        if not self.chrome_profile_path:
            self.use_user_profile_checkbox.setEnabled(False)
            self.use_user_profile_checkbox.setToolTip("Профіль Chrome не знайдено")
        else:
            # Если профиль найден, активируем опцию по умолчанию
            self.use_user_profile_checkbox.setChecked(True)
        
        options_layout.addWidget(self.use_user_profile_checkbox)
        sidebar_layout.addWidget(options_group)
        
        content_layout.addWidget(sidebar)
        
        # 2.2 ОСНОВНА ОБЛАСТЬ КОНТЕНТУ
        main_content = QFrame()
        main_content.setObjectName("mainContent")
        main_content.setStyleSheet("""
            #mainContent {
                background-color: rgba(255, 255, 255, 0.9);
                border-radius: 0px;
            }
        """)
        main_content_layout = QVBoxLayout(main_content)
        main_content_layout.setContentsMargins(20, 20, 20, 20)
        
        # Вкладки з редактором та результатами
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: transparent;
            }
            QTabBar::tab {
                background-color: rgba(240, 240, 240, 0.7);
                padding: 8px 16px;
                margin: 4px 2px 0px 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: rgba(0, 122, 255, 0.8);
                color: white;
            }
        """)
        
        # Вкладка перегляду програми
        self.view_tab = QWidget()
        view_layout = QVBoxLayout(self.view_tab)
        view_layout.setContentsMargins(0, 10, 0, 0)
        
        self.code_view = QTextEdit()
        self.code_view.setReadOnly(True)
        self.code_view.setStyleSheet("""
            QTextEdit {
                background-color: rgba(250, 250, 250, 0.7);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                padding: 10px;
                font-family: "SF Mono", Monaco, monospace;
                font-size: 13px;
            }
        """)
        view_layout.addWidget(self.code_view)
        
        # Вкладка результатів
        self.result_tab = QWidget()
        result_layout = QVBoxLayout(self.result_tab)
        result_layout.setContentsMargins(0, 10, 0, 0)
        
        # Панель статуса
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        status_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(250, 250, 250, 0.7);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                margin-bottom: 10px;
            }
        """)
        status_layout = QVBoxLayout(status_frame)
        
        # Заголовок статуса
        status_header = QLabel("Поточний статус:")
        status_header.setStyleSheet("font-weight: bold; font-size: 14px; color: #333;")
        status_layout.addWidget(status_header)
        
        # Текст статуса
        self.status_label = QLabel("Очікування запуску...")
        self.status_label.setStyleSheet("padding: 10px; font-size: 13px; color: #666;")
        status_layout.addWidget(self.status_label)
        
        result_layout.addWidget(status_frame)
        
        # Лог результатів
        self.result_view = QTextEdit()
        self.result_view.setReadOnly(True)
        self.result_view.setStyleSheet("""
            QTextEdit {
                background-color: rgba(250, 250, 250, 0.7);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                padding: 10px;
                font-family: "SF Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                font-size: 13px;
            }
        """)
        result_layout.addWidget(self.result_view)
        
        self.tabs.addTab(self.view_tab, "Програма")
        self.tabs.addTab(self.result_tab, "Результати")
        
        main_content_layout.addWidget(self.tabs)
        content_layout.addWidget(main_content)
        
        # Встановлюємо розміри бічної панелі та основного контенту
        content_layout.setStretch(0, 1)  # Бічна панель
        content_layout.setStretch(1, 3)  # Основний контент
        
        container_layout.addWidget(content_container)
        
        # Додаємо основний контейнер до макету
        main_layout.addWidget(main_container)
        
        # Статус бар
        self.statusBar().showMessage("Готовий до роботи")
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: rgba(240, 240, 240, 0.9);
                border-top: 1px solid rgba(0, 0, 0, 0.1);
                border-bottom-left-radius: 15px;
                border-bottom-right-radius: 15px;
                padding-left: 10px;
            }
        """)
        
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
            
        if not self.check_api_key():
            return
            
        program_code = self.current_program.get("code", "")
        if not program_code:
            QMessageBox.warning(self, "Помилка", "Програма порожня")
            return
            
        # Перевіряємо, чи не запущена вже програма
        if self.program_running:
            QMessageBox.warning(self, "Помилка", "Програма вже виконується")
            return
            
        # Оновлюємо стан інтерфейсу
        self.program_running = True
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.run_button.setEnabled(False)
        
        # Очищаємо вікно результатів
        self.result_view.clear()
        
        # Визначаємо режим запуску
        headless = self.headless_checkbox.isChecked()
        use_user_profile = self.use_user_profile_checkbox.isChecked()
        user_profile = self.chrome_profile_path if use_user_profile else None
        
        # Створюємо і запускаємо runner
        self.browser_runner = BrowserUseRunner(
            api_key=self.api_key,
            task=program_code,
            headless=headless,
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