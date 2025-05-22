#!/usr/bin/env python3
import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtCore import Qt, QSettings
from browser_use import BrowserAgent
import resources_rc
from first_run_dialog import FirstRunDialog

class WebMorpherApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WebMorpher")
        self.settings = QSettings('WebMorpher', 'WebMorpher')
        
        # Перевірка першого запуску
        if self.settings.value('first_run', True, type=bool):
            self.show_welcome_dialog()
            
        self.setup_ui()
        self.setup_browser_agent()
        
    def setup_ui(self):
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(800, 600)
        # Тут буде додатковий UI код
        
    def setup_browser_agent(self):
        try:
            self.browser_agent = BrowserAgent()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to initialize browser: {str(e)}")
            
    def show_welcome_dialog(self):
        dialog = FirstRunDialog(self)
        if dialog.exec_() == FirstRunDialog.Accepted:
            self.settings.setValue('first_run', False)
            self.settings.sync()

def main():
    # Налаштування змінних середовища для OpenBLAS
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    os.environ['MKL_NUM_THREADS'] = '1'
    os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
    os.environ['NUMEXPR_NUM_THREADS'] = '1'
    os.environ['OMP_NUM_THREADS'] = '1'
    
    app = QApplication(sys.argv)
    window = WebMorpherApp()
    window.show()
    sys.exit(app.exec_()) 