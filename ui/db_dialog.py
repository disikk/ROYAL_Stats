#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Диалог выбора и создания баз данных для покерного трекера ROYAL_Stats.
"""

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QLabel, QLineEdit, QMessageBox, QFileDialog, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal


class DatabaseDialog(QDialog):
    """
    Диалог для выбора существующей или создания новой базы данных.
    """
    
    db_selected = pyqtSignal(str)  # Сигнал, содержащий путь к выбранной БД
    
    def __init__(self, db_manager, parent=None):
        """
        Инициализирует диалог выбора БД.
        
        Args:
            db_manager: Экземпляр DatabaseManager
            parent: Родительский виджет
        """
        super().__init__(parent)
        
        self.db_manager = db_manager
        
        self.setWindowTitle("Выбор базы данных")
        self.setMinimumSize(500, 400)
        
        self._init_ui()
        self._load_databases()
        
    def _init_ui(self):
        """
        Инициализирует элементы интерфейса.
        """
        # Основной layout
        main_layout = QVBoxLayout(self)
        
        # Заголовок
        title_label = QLabel("Выберите базу данных или создайте новую")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        main_layout.addWidget(title_label)
        
        # Список доступных БД
        self.db_list = QListWidget()
        self.db_list.setAlternatingRowColors(True)
        self.db_list.itemDoubleClicked.connect(self._on_db_double_clicked)
        main_layout.addWidget(self.db_list)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        self.create_button = QPushButton("Создать")
        self.create_button.clicked.connect(self._on_create_button_clicked)
        buttons_layout.addWidget(self.create_button)
        
        self.import_button = QPushButton("Импортировать")
        self.import_button.clicked.connect(self._on_import_button_clicked)
        buttons_layout.addWidget(self.import_button)
        
        self.delete_button = QPushButton("Удалить")
        self.delete_button.clicked.connect(self._on_delete_button_clicked)
        buttons_layout.addWidget(self.delete_button)
        
        self.select_button = QPushButton("Выбрать")
        self.select_button.clicked.connect(self._on_select_button_clicked)
        self.select_button.setDefault(True)
        buttons_layout.addWidget(self.select_button)
        
        main_layout.addLayout(buttons_layout)
        
    def _load_databases(self):
        """
        Загружает список доступных баз данных.
        """
        self.db_list.clear()
        
        databases = self.db_manager.get_available_databases()
        for db_name in databases:
            self.db_list.addItem(db_name)
            
    def _on_create_button_clicked(self):
        """
        Обработчик нажатия на кнопку "Создать".
        """
        db_name, ok = QInputDialog.getText(
            self, "Новая база данных", 
            "Введите имя для новой базы данных:"
        )
        
        if ok and db_name:
            # Проверяем, что имя базы данных уникально
            if not db_name.endswith('.db'):
                db_name += '.db'
                
            db_path = os.path.join(self.db_manager.db_folder, db_name)
            if os.path.exists(db_path):
                QMessageBox.warning(
                    self, 
                    "Ошибка", 
                    f"База данных с именем {db_name} уже существует!"
                )
                return
                
            # Создаем новую базу данных
            try:
                db_path = self.db_manager.create_database(db_name)
                self._load_databases()
                
                # Выбираем созданную БД в списке
                for i in range(self.db_list.count()):
                    if self.db_list.item(i).text() == db_name:
                        self.db_list.setCurrentRow(i)
                        break
                        
                QMessageBox.information(
                    self,
                    "Успех",
                    f"База данных {db_name} успешно создана!"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось создать базу данных: {str(e)}"
                )
                
    def _on_import_button_clicked(self):
        """
        Обработчик нажатия на кнопку "Импортировать".
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл базы данных",
            "",
            "SQLite Database (*.db);;All Files (*)"
        )
        
        if file_path:
            # Получаем имя файла
            db_name = os.path.basename(file_path)
            
            # Проверяем, что файл с таким именем не существует
            target_path = os.path.join(self.db_manager.db_folder, db_name)
            if os.path.exists(target_path):
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    f"База данных с именем {db_name} уже существует!"
                )
                return
                
            # Копируем файл в папку баз данных
            try:
                import shutil
                shutil.copy2(file_path, target_path)
                
                # Проверяем, что это действительно база данных SQLite
                try:
                    import sqlite3
                    conn = sqlite3.connect(target_path)
                    # Проверяем наличие необходимых таблиц
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()
                    required_tables = ['tournaments', 'knockouts', 'statistics']
                    
                    missing_tables = []
                    for table in required_tables:
                        if (table,) not in tables:
                            missing_tables.append(table)
                            
                    conn.close()
                    
                    if missing_tables:
                        # Не все требуемые таблицы найдены
                        QMessageBox.warning(
                            self,
                            "Предупреждение",
                            f"Файл не является базой данных ROYAL_Stats или имеет неверную структуру. "
                            f"Отсутствуют таблицы: {', '.join(missing_tables)}. "
                            f"База данных будет инициализирована заново."
                        )
                        # Инициализируем базу данных
                        self.db_manager.connect(target_path)
                        self.db_manager._create_tables()
                except:
                    # Если возникла ошибка при проверке базы, инициализируем её
                    QMessageBox.warning(
                        self,
                        "Предупреждение",
                        "Файл не является базой данных SQLite или поврежден. "
                        "База данных будет инициализирована заново."
                    )
                    # Инициализируем базу данных
                    self.db_manager.connect(target_path)
                    self.db_manager._create_tables()
                    
                # Обновляем список баз данных
                self._load_databases()
                
                # Выбираем импортированную БД в списке
                for i in range(self.db_list.count()):
                    if self.db_list.item(i).text() == db_name:
                        self.db_list.setCurrentRow(i)
                        break
                        
                QMessageBox.information(
                    self,
                    "Успех",
                    f"База данных {db_name} успешно импортирована!"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось импортировать базу данных: {str(e)}"
                )
                
    def _on_delete_button_clicked(self):
        """
        Обработчик нажатия на кнопку "Удалить".
        """
        # Получаем выбранную БД
        current_item = self.db_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Выберите базу данных для удаления!"
            )
            return
            
        db_name = current_item.text()
        
        # Запрашиваем подтверждение
        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить базу данных {db_name}?\n"
            f"Это действие невозможно отменить!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Удаляем файл базы данных
            try:
                db_path = os.path.join(self.db_manager.db_folder, db_name)
                
                # Если это текущая база данных, закрываем соединение
                if self.db_manager.current_db_path == db_path:
                    self.db_manager.close()
                    
                # Удаляем файл
                os.remove(db_path)
                
                # Обновляем список
                self._load_databases()
                
                QMessageBox.information(
                    self,
                    "Успех",
                    f"База данных {db_name} успешно удалена!"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось удалить базу данных: {str(e)}"
                )
                
    def _on_select_button_clicked(self):
        """
        Обработчик нажатия на кнопку "Выбрать".
        """
        # Получаем выбранную БД
        current_item = self.db_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Выберите базу данных!"
            )
            return
            
        db_name = current_item.text()
        db_path = os.path.join(self.db_manager.db_folder, db_name)
        
        # Подключаемся к базе данных
        try:
            self.db_manager.connect(db_path)
            
            # Отправляем сигнал с путем к БД
            self.db_selected.emit(db_path)
            
            # Закрываем диалог
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось подключиться к базе данных: {str(e)}"
            )
            
    def _on_db_double_clicked(self, item):
        """
        Обработчик двойного клика на элементе списка.
        """
        # Эмулируем нажатие на кнопку "Выбрать"
        self._on_select_button_clicked()