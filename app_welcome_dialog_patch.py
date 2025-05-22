#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Патч для добавления окна приветствия при первом запуске WebMorpher.
Этот файл нужно применить к файлу app.py для добавления новой функциональности.

Инструкция по применению:
1. Импортировать класс FirstRunDialog в app.py
2. Добавить проверку и показ диалога первого запуска в метод __init__ класса WebMorpherApp
3. Добавить настройку для хранения флага первого запуска
"""

# Добавить после импорта resources_rc:
# from first_run_dialog import FirstRunDialog

# Добавить в метод load_config класса WebMorpherApp:
"""
        # Флаг для отслеживания первого запуска
        self.show_welcome_dialog = config.get('show_welcome_dialog', True)
"""

# Добавить в метод save_config класса WebMorpherApp:
"""
        # Сохраняем флаг первого запуска
        config['show_welcome_dialog'] = self.show_welcome_dialog
"""

# Добавить в конец метода setup_ui класса WebMorpherApp:
"""
        # Показываем диалог первого запуска, если это необходимо
        if self.show_welcome_dialog:
            self.show_welcome_screen()
"""

# Добавить новый метод в класс WebMorpherApp:
"""
    def show_welcome_screen(self):
        """Показывает экран приветствия при первом запуске"""
        welcome_dialog = FirstRunDialog(self)
        welcome_dialog.exec_()
        
        # Если пользователь выбрал "Не показывать снова", сохраняем эту настройку
        if welcome_dialog.dont_show_again():
            self.show_welcome_dialog = False
            self.save_config()
""" 