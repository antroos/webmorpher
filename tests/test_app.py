import os
import sys
import json
import unittest
import tempfile
from unittest.mock import patch, MagicMock, PropertyMock
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt

# Додаємо батьківську директорію до шляху, щоб імпортувати app.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Імпортуємо наш додаток
from app import WebMorpherApp, ApiKeyDialog, ProgramEditorDialog

class TestApiKeyDialog(unittest.TestCase):
    """Тести для діалогу введення API ключа"""
    
    def setUp(self):
        self.app = QApplication.instance() or QApplication([])
        self.dialog = ApiKeyDialog()
    
    def tearDown(self):
        self.dialog.close()
        
    def test_dialog_initial_state(self):
        """Перевірка початкового стану діалогу"""
        self.assertEqual(self.dialog.windowTitle(), "Введіть API ключ")
        self.assertEqual(self.dialog.api_key, "")
        self.assertEqual(self.dialog.key_input.text(), "")
        
    def test_dialog_validation(self):
        """Перевірка валідації API ключа"""
        # Встановлюємо неправильний ключ і викликаємо валідацію
        with patch.object(ApiKeyDialog, 'accept') as accept_mock:
            self.dialog.key_input.setText("wrong-key")
            self.dialog.accept_key()
            # Перевіряємо, що accept не був викликаний
            accept_mock.assert_not_called()
        
        # Встановлюємо правильний ключ і викликаємо валідацію
        with patch.object(ApiKeyDialog, 'accept') as accept_mock:
            self.dialog.key_input.setText("sk-validkey123")
            self.dialog.accept_key()
            # Перевіряємо, що accept був викликаний
            accept_mock.assert_called_once()

class TestProgramEditorDialog(unittest.TestCase):
    """Тести для діалогу редагування програми"""
    
    def setUp(self):
        self.app = QApplication.instance() or QApplication([])
        self.dialog = ProgramEditorDialog()
    
    def tearDown(self):
        self.dialog.close()
        
    def test_dialog_initial_state(self):
        """Перевірка початкового стану діалогу"""
        self.assertEqual(self.dialog.windowTitle(), "Редактор програми")
        self.assertEqual(self.dialog.name_input.text(), "")
        self.assertEqual(self.dialog.code_editor.toPlainText(), "")
        
    def test_dialog_with_data(self):
        """Перевірка стану діалогу з початковими даними"""
        test_name = "Тестова програма"
        test_code = "print('Hello, World!')"
        dialog = ProgramEditorDialog(program_name=test_name, program_code=test_code)
        
        self.assertEqual(dialog.name_input.text(), test_name)
        self.assertEqual(dialog.code_editor.toPlainText(), test_code)
        
    def test_get_program_data(self):
        """Перевірка отримання даних програми"""
        test_name = "Тестова програма"
        test_code = "print('Hello, World!')"
        
        self.dialog.name_input.setText(test_name)
        self.dialog.code_editor.setPlainText(test_code)
        
        data = self.dialog.get_program_data()
        
        self.assertEqual(data["name"], test_name)
        self.assertEqual(data["code"], test_code)

class TestWebMorpherApp(unittest.TestCase):
    """Тести для основного додатку"""
    
    def setUp(self):
        # Створюємо тимчасовий файл конфігурації для тестів
        self.temp_config = tempfile.NamedTemporaryFile(delete=False)
        self.temp_config.close()
        
        # Зберігаємо оригінальний шлях до конфігурації
        self.original_config = os.environ.get('WEBMORPHER_CONFIG')
        
        # Підмінюємо шлях до конфігурації для тестів
        self._patch_config = patch('app.CONFIG_FILE', self.temp_config.name)
        self._patch_config.start()
        
        # Заповнюємо тестовий конфіг даними
        with open(self.temp_config.name, 'w') as f:
            json.dump({
                'api_key': 'sk-testkey123',
                'programs': [
                    {
                        'name': 'Тестова програма 1',
                        'code': 'print("Test 1")'
                    },
                    {
                        'name': 'Тестова програма 2',
                        'code': 'print("Test 2")'
                    }
                ]
            }, f)
        
        # Створюємо екземпляр програми
        self.app = QApplication.instance() or QApplication([])
        
        # Підмінюємо метод перевірки API ключа, щоб уникнути діалогів
        with patch('app.WebMorpherApp.check_api_key', return_value=True):
            self.window = WebMorpherApp()
    
    def tearDown(self):
        self.window.close()
        self._patch_config.stop()
        
        # Видаляємо тимчасовий файл
        os.unlink(self.temp_config.name)
        
        # Відновлюємо оригінальний шлях конфігурації
        if self.original_config:
            os.environ['WEBMORPHER_CONFIG'] = self.original_config
    
    def test_app_initial_state(self):
        """Перевірка початкового стану додатку"""
        self.assertEqual(self.window.windowTitle(), "WebMorpher")
        self.assertEqual(self.window.api_key, "sk-testkey123")
        self.assertEqual(len(self.window.programs), 2)
        self.assertEqual(self.window.program_list.count(), 2)
        
    def test_program_selection(self):
        """Перевірка вибору програми"""
        # Вибираємо першу програму
        self.window.program_list.setCurrentRow(0)
        
        # Перевіряємо, що вибрана програма відображається в редакторі
        self.assertEqual(self.window.current_program["name"], "Тестова програма 1")
        self.assertEqual(self.window.code_view.toPlainText(), 'print("Test 1")')
        
        # Вибираємо другу програму
        self.window.program_list.setCurrentRow(1)
        
        # Перевіряємо, що вибрана програма відображається в редакторі
        self.assertEqual(self.window.current_program["name"], "Тестова програма 2")
        self.assertEqual(self.window.code_view.toPlainText(), 'print("Test 2")')
    
    def test_program_run_ui_state(self):
        """Перевірка стану інтерфейсу при запуску програми"""
        # Вибираємо програму
        self.window.program_list.setCurrentRow(0)
        
        # Перевіряємо початковий стан кнопок
        self.assertTrue(self.window.run_button.isEnabled())
        self.assertFalse(self.window.pause_button.isEnabled())
        self.assertFalse(self.window.stop_button.isEnabled())
        
        # Запускаємо програму
        self.window.run_program()
        
        # Перевіряємо стан кнопок після запуску
        self.assertFalse(self.window.run_button.isEnabled())
        self.assertTrue(self.window.pause_button.isEnabled())
        self.assertTrue(self.window.stop_button.isEnabled())
        
        # Зупиняємо програму
        self.window.stop_program()
        
        # Перевіряємо стан кнопок після зупинки
        self.assertTrue(self.window.run_button.isEnabled())
        self.assertFalse(self.window.pause_button.isEnabled())
        self.assertFalse(self.window.stop_button.isEnabled())

if __name__ == '__main__':
    unittest.main() 