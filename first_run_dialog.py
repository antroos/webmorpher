#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                             QHBoxLayout, QCheckBox, QFrame, QApplication)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QPixmap, QFont

class FirstRunDialog(QDialog):
    """Диалоговое окно для первого запуска приложения"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добро пожаловать в WebMorpher")
        self.setMinimumSize(550, 500)
        self.setup_ui()
        
    def setup_ui(self):
        # Основной макет
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Заголовок
        title_label = QLabel("Добро пожаловать в WebMorpher!")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Линия-разделитель
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        
        # Описание приложения
        desc_label = QLabel(
            "WebMorpher - это приложение для автоматизации работы с веб-страницами "
            "с использованием искусственного интеллекта. Для работы приложения необходим "
            "API-ключ OpenAI и интернет-соединение."
        )
        desc_label.setWordWrap(True)
        main_layout.addWidget(desc_label)
        
        # Инструкции по настройке
        setup_label = QLabel(
            "<b>Для начала работы:</b><br>"
            "1. Получите API-ключ OpenAI на сайте <a href='https://platform.openai.com/api-keys'>platform.openai.com/api-keys</a><br>"
            "2. Нажмите кнопку 'Изменить API-ключ' в основном окне приложения<br>"
            "3. Создайте и запустите свой первый сценарий WebMorpher<br><br>"
            "<b>Примечания:</b><br>"
            "• При первом запуске программа установит необходимый браузер<br>"
            "• Требуется стабильное интернет-соединение<br>"
            "• Ваш API-ключ OpenAI хранится только на вашем компьютере"
        )
        setup_label.setTextFormat(Qt.RichText)
        setup_label.setWordWrap(True)
        setup_label.setOpenExternalLinks(True)
        main_layout.addWidget(setup_label)
        
        # Линия-разделитель
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line2)
        
        # Кнопки и чекбокс
        checkbox_layout = QHBoxLayout()
        self.dont_show_checkbox = QCheckBox("Не показывать это окно при следующем запуске")
        checkbox_layout.addWidget(self.dont_show_checkbox)
        main_layout.addLayout(checkbox_layout)
        
        button_layout = QHBoxLayout()
        close_button = QPushButton("Закрыть")
        close_button.setMinimumWidth(120)
        close_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        main_layout.addLayout(button_layout)
    
    def dont_show_again(self):
        """Возвращает True, если пользователь не хочет видеть это окно снова"""
        return self.dont_show_checkbox.isChecked()


if __name__ == "__main__":
    # Тестовый запуск диалогового окна
    import sys
    app = QApplication(sys.argv)
    dialog = FirstRunDialog()
    result = dialog.exec_()
    print(f"Don't show again: {dialog.dont_show_again()}")
    sys.exit(0) 