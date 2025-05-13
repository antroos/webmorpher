import sys
import os
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QTextEdit, QLabel, QLineEdit, QMessageBox, QDialog,
                            QListWidget, QTabWidget, QSplitter, QFrame, QFileDialog)
from PyQt5.QtCore import Qt, QSize

# Шлях до файлу з налаштуваннями
CONFIG_FILE = os.path.expanduser("~/.webmorpher_config.json")

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
        self.api_key = ""
        self.programs = []
        self.current_program = None
        self.program_running = False
        
        self.setWindowTitle("WebMorpher")
        self.setGeometry(100, 100, 1000, 700)
        
        # Спочатку перевіряємо наявність API ключа
        self.load_config()
        if not self.check_api_key():
            sys.exit()
            
        self.setup_ui()
        
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
        
        self.api_button = QPushButton("Змінити API ключ")
        self.api_button.clicked.connect(self.change_api_key)
        
        control_layout.addWidget(self.new_button)
        control_layout.addWidget(self.edit_button)
        control_layout.addWidget(self.delete_button)
        control_layout.addWidget(self.run_button)
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.api_button)
        
        main_layout.addLayout(control_layout)
        
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
            self.statusBar().showMessage(f"Обрано програму: {program.get('name', 'Без назви')}")
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
            self.statusBar().showMessage(f"Створено нову програму: {program_data['name']}")
    
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
            self.statusBar().showMessage(f"Програму оновлено: {program_data['name']}")
    
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
            self.statusBar().showMessage(f"Програму видалено: {program_name}")
    
    def run_program(self):
        """Запуск обраної програми"""
        if not self.current_program:
            QMessageBox.warning(self, "Помилка", "Спочатку оберіть програму для запуску")
            return
        
        program_name = self.current_program.get("name", "Без назви")
        self.program_running = True
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.run_button.setEnabled(False)
        
        # Перемикаємося на вкладку результатів
        self.tabs.setCurrentIndex(1)
        
        # Заглушка - пізніше тут буде реальний запуск програми
        self.result_view.append(f"Запуск програми: {program_name}")
        self.result_view.append("Ця версія програми містить тільки інтерфейс без реальної функціональності.")
        self.result_view.append("Тут буде відображатися вивід роботи програми...")
        
        self.statusBar().showMessage(f"Запущено програму: {program_name}")
    
    def pause_program(self):
        """Призупинення виконання програми"""
        if not self.program_running:
            return
            
        # Заглушка
        self.result_view.append("Програму призупинено")
        self.statusBar().showMessage("Програму призупинено")
    
    def stop_program(self):
        """Зупинка виконання програми"""
        if not self.program_running:
            return
            
        self.program_running = False
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.run_button.setEnabled(True)
        
        # Заглушка
        self.result_view.append("Програму зупинено")
        self.statusBar().showMessage("Програму зупинено")
    
    def change_api_key(self):
        """Зміна API ключа"""
        dialog = ApiKeyDialog(self)
        dialog.key_input.setText(self.api_key)
        
        if dialog.exec_():
            self.api_key = dialog.api_key
            self.save_config()
            self.statusBar().showMessage("API ключ оновлено")

    def closeEvent(self, event):
        """Обробка закриття додатку"""
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
    window = WebMorpherApp()
    window.show()
    sys.exit(app.exec_()) 