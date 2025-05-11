#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Главное окно покерного трекера ROYAL_Stats.
"""

import os
import uuid
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTabWidget, QFileDialog, QMessageBox, QProgressBar,
    QStatusBar, QSplitter, QTreeWidget, QTreeWidgetItem, QMenu,
    QDialog, QInputDialog, QHeaderView, QTableWidget, QTableWidgetItem,
    QGroupBox, QScrollArea
)
from PyQt6.QtCore import Qt, QThreadPool, QRunnable, pyqtSignal, pyqtSlot, QObject, QSize
from PyQt6.QtGui import QAction, QIcon, QFont

from db.database import DatabaseManager, StatsDatabase
from ui.db_dialog import DatabaseDialog
from ui.visualizations import PlaceDistributionChart, StatsGrid
from parsers.hand_history import HandHistoryParser
from parsers.tournament_summary import TournamentSummaryParser

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.MainWindow')

# Сигналы для выполнения задач в отдельном потоке
class WorkerSignals(QObject):
    """
    Сигналы для WorkerThread.
    """
    started = pyqtSignal()
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    error = pyqtSignal(str)
    result = pyqtSignal(object)


class Worker(QRunnable):
    """
    Класс для выполнения задач в отдельном потоке.
    """
    
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        
        # Логирование для отладки
        self.logger = logging.getLogger('ROYAL_Stats.Worker')
        
    @pyqtSlot()
    def run(self):
        """
        Выполняет функцию в отдельном потоке.
        """
        try:
            # Сообщаем о начале работы
            self.signals.started.emit()
            self.logger.debug(f"Worker начал выполнение функции {self.fn.__name__}")
            
            # Выполняем функцию
            result = self.fn(*self.args, **self.kwargs)
            
            # Отправляем результат
            self.signals.result.emit(result)
            self.logger.debug(f"Worker успешно выполнил функцию {self.fn.__name__}")
            
        except Exception as e:
            # Логируем ошибку
            self.logger.error(f"Ошибка в Worker при выполнении {self.fn.__name__}: {str(e)}", 
                            exc_info=True)
            
            # Отправляем сигнал об ошибке
            self.signals.error.emit(str(e))
            
        finally:
            # В любом случае сообщаем о завершении работы
            self.signals.finished.emit()
            self.logger.debug(f"Worker завершил выполнение функции {self.fn.__name__}")


class MainWindow(QMainWindow):
    """
    Главное окно приложения ROYAL_Stats.
    """
    
    def __init__(self):
        super().__init__()
        
        # Инициализируем менеджер БД и стат. БД
        self.db_manager = DatabaseManager(db_folder='databases')
        self.stats_db = None
        
        # Парсеры
        self.hand_history_parser = HandHistoryParser()
        self.tournament_summary_parser = TournamentSummaryParser()
        
        # Пул потоков для выполнения задач
        self.threadpool = QThreadPool()
        
        # Текущая сессия
        self.current_session_id = None
        
        # Настраиваем интерфейс
        self._init_ui()
        
        # Показываем диалог выбора БД при запуске
        self.show_database_dialog()
        
    def _init_ui(self):
        """
        Инициализирует элементы интерфейса.
        """
        self.setWindowTitle("Royal Stats by disikk")
        self.setMinimumSize(1200, 800)
        
        # Создаем центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        main_layout = QVBoxLayout(central_widget)
        
        # Верхняя панель с кнопками
        toolbar_layout = QHBoxLayout()
        
        # Кнопка выбора БД
        self.db_button = QPushButton("Выбрать БД")
        self.db_button.clicked.connect(self.show_database_dialog)
        toolbar_layout.addWidget(self.db_button)
        
        # Кнопка загрузки файлов
        self.load_files_button = QPushButton("Загрузить файлы")
        self.load_files_button.clicked.connect(self.load_files)
        self.load_files_button.setEnabled(False)  # Активируем только после выбора БД
        toolbar_layout.addWidget(self.load_files_button)
        
        # Название текущей БД
        self.db_name_label = QLabel("База данных не выбрана")
        self.db_name_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        font = QFont()
        font.setBold(True)
        self.db_name_label.setFont(font)
        toolbar_layout.addWidget(self.db_name_label)
        
        # Добавляем toolbar на основной layout
        main_layout.addLayout(toolbar_layout)
        
        # Сплиттер для разделения списка сессий и основного контента
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Список сессий
        self.sessions_tree = QTreeWidget()
        self.sessions_tree.setHeaderLabels(["Сессии"])
        self.sessions_tree.setMinimumWidth(250)
        self.sessions_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sessions_tree.customContextMenuRequested.connect(self.show_session_context_menu)
        self.sessions_tree.itemClicked.connect(self.on_session_selected)
        
        # Табы с основным контентом
        self.tabs = QTabWidget()
        
        # Вкладка "Статистика"
        self.stats_tab = QWidget()
        stats_layout = QVBoxLayout(self.stats_tab)
        
        # Сетка с основными показателями
        self.stats_grid = StatsGrid()
        stats_layout.addWidget(self.stats_grid)
        
        # Гистограмма распределения мест
        self.place_chart = PlaceDistributionChart()
        stats_layout.addWidget(self.place_chart)
        
        # Вкладка "Турниры"
        self.tournaments_tab = QWidget()
        tournaments_layout = QVBoxLayout(self.tournaments_tab)
        
        # Таблица с турнирами
        self.tournaments_table = QTableWidget()
        self.tournaments_table.setColumnCount(7)
        self.tournaments_table.setHorizontalHeaderLabels([
            "ID турнира", "Buy-in", "Место", "Выигрыш", "Нокаутов", "x10 Нокауты", "Дата"
        ])
        self.tournaments_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tournaments_layout.addWidget(self.tournaments_table)
        
        # Добавляем вкладки
        self.tabs.addTab(self.stats_tab, "Статистика")
        self.tabs.addTab(self.tournaments_tab, "Турниры")
        
        # Добавляем виджеты на сплиттер
        splitter.addWidget(self.sessions_tree)
        splitter.addWidget(self.tabs)
        
        # Устанавливаем начальные размеры
        splitter.setSizes([250, 950])
        
        # Добавляем сплиттер на основной layout
        main_layout.addWidget(splitter)
        
        # Прогресс-бар для отображения процесса загрузки файлов
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Строка состояния
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готово")
        
        # Создаем меню
        self._create_menu()
        
    def _create_menu(self):
        """
        Создает главное меню приложения.
        """
        # Меню "Файл"
        file_menu = self.menuBar().addMenu("Файл")
        
        # Выбор БД
        select_db_action = QAction("Выбрать базу данных", self)
        select_db_action.triggered.connect(self.show_database_dialog)
        file_menu.addAction(select_db_action)
        
        # Загрузка файлов
        load_files_action = QAction("Загрузить файлы", self)
        load_files_action.triggered.connect(self.load_files)
        file_menu.addAction(load_files_action)
        
        file_menu.addSeparator()
        
        # Выход
        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Меню "Сессия"
        session_menu = self.menuBar().addMenu("Сессия")
        
        # Новая сессия
        new_session_action = QAction("Новая сессия", self)
        new_session_action.triggered.connect(self.create_new_session)
        session_menu.addAction(new_session_action)
        
        # Переименовать сессию
        rename_session_action = QAction("Переименовать сессию", self)
        rename_session_action.triggered.connect(self.rename_selected_session)
        session_menu.addAction(rename_session_action)
        
        # Удалить сессию
        delete_session_action = QAction("Удалить сессию", self)
        delete_session_action.triggered.connect(self.delete_selected_session)
        session_menu.addAction(delete_session_action)
        
        # Меню "Инструменты"
        tools_menu = self.menuBar().addMenu("Инструменты")
        
        # Обновить статистику
        update_stats_action = QAction("Обновить статистику", self)
        update_stats_action.triggered.connect(self.update_statistics)
        tools_menu.addAction(update_stats_action)
        
        # Очистить все данные
        clear_data_action = QAction("Очистить все данные", self)
        clear_data_action.triggered.connect(self.clear_all_data)
        tools_menu.addAction(clear_data_action)
        
    def show_database_dialog(self):
        """
        Показывает диалог выбора базы данных.
        """
        dialog = DatabaseDialog(self.db_manager, self)
        dialog.db_selected.connect(self.on_database_selected)
        dialog.exec()
        
    def on_database_selected(self, db_path):
        """
        Обработчик выбора базы данных.
        
        Args:
            db_path: Путь к выбранной базе данных
        """
        # Запоминаем путь и имя базы
        self.current_db_path = db_path
        db_name = os.path.basename(db_path)
        
        # Обновляем интерфейс
        self.db_name_label.setText(f"База данных: {db_name}")
        self.load_files_button.setEnabled(True)
        
        # Инициализируем объект для работы с БД
        self.stats_db = StatsDatabase(self.db_manager)
        
        # Загружаем сессии из базы
        self.load_sessions()
        
        # Обновляем статистику
        self.update_statistics()
        
        # Отображаем сообщение
        self.status_bar.showMessage(f"Подключено к базе данных {db_name}")
        
    def load_sessions(self):
        """
        Загружает список сессий из базы данных.
        """
        if not self.stats_db:
            return
            
        # Очищаем дерево сессий
        self.sessions_tree.clear()
        
        # Создаем корневой элемент "Все"
        all_sessions_item = QTreeWidgetItem(["Все сессии"])
        all_sessions_item.setData(0, Qt.ItemDataRole.UserRole, "all")
        self.sessions_tree.addTopLevelItem(all_sessions_item)
        
        # Получаем список сессий
        try:
            sessions = self.stats_db.get_sessions()
            
            # Добавляем сессии в дерево
            for session in sessions:
                # Создаем элемент для сессии
                session_name = session['session_name']
                session_id = session['session_id']
                
                item_text = f"{session_name} ({session['tournaments_count']} турниров)"
                session_item = QTreeWidgetItem([item_text])
                session_item.setData(0, Qt.ItemDataRole.UserRole, session_id)
                
                # Добавляем элемент в дерево
                self.sessions_tree.addTopLevelItem(session_item)
                
            # Разворачиваем дерево
            self.sessions_tree.expandAll()
            
            # Выбираем "Все сессии"
            self.sessions_tree.setCurrentItem(all_sessions_item)
            self.on_session_selected(all_sessions_item, 0)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось загрузить сессии: {str(e)}"
            )
            
    def on_session_selected(self, item, column=0):
        """
        Обработчик выбора сессии в дереве.
        
        Args:
            item: Выбранный элемент
            column: Номер колонки
        """
        # Получаем ID сессии
        session_id = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Обновляем интерфейс в зависимости от выбранной сессии
        if session_id == "all":
            # Выбраны все сессии
            self.current_session_id = None
            self.update_statistics()
            self.load_all_tournaments()
        else:
            # Выбрана конкретная сессия
            self.current_session_id = session_id
            self.update_session_statistics(session_id)
            self.load_session_tournaments(session_id)
            
    def show_session_context_menu(self, position):
        """
        Показывает контекстное меню для сессии.
        
        Args:
            position: Позиция клика
        """
        # Получаем выбранный элемент
        item = self.sessions_tree.itemAt(position)
        if not item:
            return
            
        # Получаем ID сессии
        session_id = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Не показываем меню для "Все сессии"
        if session_id == "all":
            return
            
        # Создаем меню
        menu = QMenu(self)
        
        # Добавляем действия
        rename_action = menu.addAction("Переименовать")
        delete_action = menu.addAction("Удалить")
        
        # Показываем меню и обрабатываем действие
        action = menu.exec(self.sessions_tree.mapToGlobal(position))
        
        if action == rename_action:
            self.rename_session(session_id)
        elif action == delete_action:
            self.delete_session(session_id)
            
    def rename_session(self, session_id):
        """
        Переименовывает сессию.
        
        Args:
            session_id: ID сессии
        """
        # Получаем информацию о сессии
        session_info = self.stats_db.get_session_stats(session_id)
        if not session_info:
            return
            
        # Запрашиваем новое имя
        new_name, ok = QInputDialog.getText(
            self,
            "Переименование сессии",
            "Введите новое название для сессии:",
            text=session_info['session_name']
        )
        
        if ok and new_name:
            try:
                # Обновляем имя сессии в БД
                self.db_manager.cursor.execute(
                    "UPDATE sessions SET session_name = ? WHERE session_id = ?",
                    (new_name, session_id)
                )
                self.db_manager.connection.commit()
                
                # Обновляем список сессий
                self.load_sessions()
                
                # Отображаем сообщение
                self.status_bar.showMessage(f"Сессия успешно переименована")
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось переименовать сессию: {str(e)}"
                )
                
    def delete_session(self, session_id):
        """
        Удаляет сессию.
        
        Args:
            session_id: ID сессии
        """
        # Запрашиваем подтверждение
        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            "Вы уверены, что хотите удалить эту сессию?\n"
            "Это действие невозможно отменить!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Удаляем сессию из БД
                self.stats_db.delete_session(session_id)
                
                # Обновляем список сессий
                self.load_sessions()
                
                # Отображаем сообщение
                self.status_bar.showMessage(f"Сессия успешно удалена")
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось удалить сессию: {str(e)}"
                )
                
    def rename_selected_session(self):
        """
        Переименовывает выбранную сессию.
        """
        # Получаем выбранный элемент
        item = self.sessions_tree.currentItem()
        if not item:
            return
            
        # Получаем ID сессии
        session_id = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Не переименовываем "Все сессии"
        if session_id == "all":
            return
            
        # Переименовываем сессию
        self.rename_session(session_id)
        
    def delete_selected_session(self):
        """
        Удаляет выбранную сессию.
        """
        # Получаем выбранный элемент
        item = self.sessions_tree.currentItem()
        if not item:
            return
            
        # Получаем ID сессии
        session_id = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Не удаляем "Все сессии"
        if session_id == "all":
            return
            
        # Удаляем сессию
        self.delete_session(session_id)
        
    def create_new_session(self):
        """
        Создает новую сессию.
        """
        if not self.stats_db:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Сначала выберите базу данных!"
            )
            return
            
        # Запрашиваем название сессии
        name, ok = QInputDialog.getText(
            self,
            "Новая сессия",
            "Введите название для новой сессии:"
        )
        
        if ok and name:
            try:
                # Создаем новую сессию
                session_id = self.stats_db.create_session(name)
                
                # Обновляем список сессий
                self.load_sessions()
                
                # Выбираем новую сессию
                for i in range(self.sessions_tree.topLevelItemCount()):
                    item = self.sessions_tree.topLevelItem(i)
                    if item.data(0, Qt.ItemDataRole.UserRole) == session_id:
                        self.sessions_tree.setCurrentItem(item)
                        self.on_session_selected(item)
                        break
                        
                # Отображаем сообщение
                self.status_bar.showMessage(f"Сессия '{name}' успешно создана")
                
                # Возвращаем ID созданной сессии
                return session_id
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось создать сессию: {str(e)}"
                )
                
        return None
        
    def load_files(self):
        """
        Загружает файлы истории рук и сводки турниров.
        """
        if not self.stats_db:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Сначала выберите базу данных!"
            )
            return
            
        # Показываем диалог выбора файлов или папок
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, False)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.setWindowTitle("Выберите файлы или папки")

        # Список файлов для обработки
        file_paths = []

        if dialog.exec():
            # Получаем выбранные файлы и папки
            selected_paths = dialog.selectedFiles()
            
            for path in selected_paths:
                if os.path.isdir(path):
                    # Если это папка, добавляем все файлы из нее и ее подпапок
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            file_paths.append(os.path.join(root, file))
                else:
                    # Если это файл, просто добавляем его
                    file_paths.append(path)
        
        if not file_paths:
            return
            
        # Создаем новую сессию или используем текущую
        if not self.current_session_id or self.current_session_id == "all":
            session_id = self.create_new_session()
            if not session_id:
                return
        else:
            session_id = self.current_session_id
            
        # Показываем прогресс-бар
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(file_paths))
        self.progress_bar.setValue(0)
        
        # Отключаем кнопки
        self.load_files_button.setEnabled(False)
        
        # Создаем worker для обработки файлов в отдельном потоке
        worker = Worker(self.process_files, file_paths, session_id)
        
        # Подключаем сигналы
        worker.signals.finished.connect(self.on_files_processing_finished)
        worker.signals.error.connect(self.on_files_processing_error)
        worker.signals.result.connect(self.on_files_processing_result)
        worker.signals.progress.connect(self.progress_bar.setValue)
        
        # Запускаем обработку в отдельном потоке
        self.threadpool.start(worker)
        
    def process_files(self, file_paths, session_id):
        """
        Обрабатывает файлы истории рук и сводки турниров.
        
        Args:
            file_paths: Список путей к файлам
            session_id: ID сессии
            
        Returns:
            Статистика обработки
        """
        # Сортируем файлы на истории рук и сводки турниров
        hand_history_files = []
        tournament_summary_files = []
        
        for index, file_path in enumerate(file_paths):
            file_name = os.path.basename(file_path)
            
            # Проверяем соответствие имени файла шаблонам
            if file_name.endswith('9max.txt'):
                hand_history_files.append(file_path)
            elif ('Tournament #' in file_name and 'Mystery Battle Royale' in file_name and 
                  file_name.endswith('.txt')):
                tournament_summary_files.append(file_path)
                
            # Отправляем сигнал прогресса
            self.signals.progress.emit(index + 1)
                
        # Словарь для хранения результатов обработки
        results = {
            'total_files': len(file_paths),
            'tournament_summary_files': len(tournament_summary_files),
            'hand_history_files': len(hand_history_files),
            'processed_tournaments': 0,
            'processed_knockouts': 0,
            'errors': []
        }
        
        # Обрабатываем файлы сводки турниров
        for i, file_path in enumerate(tournament_summary_files):
            try:
                # Парсим файл
                tournament_data = self.tournament_summary_parser.parse_file(file_path)
                
                # Сохраняем данные в БД
                self.stats_db.save_tournament_data(tournament_data.__dict__, session_id)
                
                results['processed_tournaments'] += 1
            except Exception as e:
                results['errors'].append(f"Ошибка при обработке {file_path}: {str(e)}")
                
        # Обрабатываем файлы истории рук
        for i, file_path in enumerate(hand_history_files):
            try:
                # Парсим файл
                hand_history_data = self.hand_history_parser.parse_file(file_path)
                
                # Сохраняем нокауты в БД
                if hand_history_data.get('tournament_id') and hand_history_data.get('knockouts'):
                    self.stats_db.save_knockouts_data(
                        hand_history_data['tournament_id'],
                        hand_history_data['knockouts'],
                        session_id
                    )
                    
                    results['processed_knockouts'] += len(hand_history_data['knockouts'])
            except Exception as e:
                results['errors'].append(f"Ошибка при обработке {file_path}: {str(e)}")
                
        # Обновляем статистику сессии
        self.stats_db.update_session_stats(session_id)
        
        # Обновляем общую статистику
        self.stats_db.update_overall_statistics()
        
        return results

    def on_files_processing_result(self, results):
        """
        Обработчик получения результатов обработки файлов.
        
        Args:
            results: Словарь с результатами обработки
        """
        # Проверяем наличие ошибок
        if results.get('errors'):
            error_message = "При обработке файлов возникли ошибки:\n\n"
            error_message += "\n".join(results['errors'][:5])  # Показываем первые 5 ошибок
            
            if len(results['errors']) > 5:
                error_message += f"\n\n...и еще {len(results['errors']) - 5} ошибок."
                
            QMessageBox.warning(
                self,
                "Предупреждение",
                error_message
            )
        
        # Выводим статистику обработки
        stats_message = (
            f"Обработано файлов: {results['total_files']}\n"
            f"Файлов сводки турниров: {results['tournament_summary_files']}\n"
            f"Файлов истории рук: {results['hand_history_files']}\n"
            f"Обработано турниров: {results['processed_tournaments']}\n"
            f"Обработано нокаутов: {results['processed_knockouts']}"
        )
        
        self.status_bar.showMessage(stats_message, 5000)  # Показываем на 5 секунд
        
    def on_files_processing_finished(self):
        """
        Обработчик завершения обработки файлов.
        """
        # Скрываем прогресс-бар
        self.progress_bar.setVisible(False)
        
        # Включаем кнопки
        self.load_files_button.setEnabled(True)
        
        # Обновляем интерфейс
        self.load_sessions()
        self.update_statistics()
        
        # Отображаем сообщение
        self.status_bar.showMessage("Обработка файлов завершена")
        
    def on_files_processing_error(self, error_message):
        """
        Обработчик ошибки при обработке файлов.
        
        Args:
            error_message: Сообщение об ошибке
        """
        # Скрываем прогресс-бар
        self.progress_bar.setVisible(False)
        
        # Включаем кнопки
        self.load_files_button.setEnabled(True)
        
        # Отображаем сообщение об ошибке
        QMessageBox.critical(
            self,
            "Ошибка",
            f"Ошибка при обработке файлов: {error_message}"
        )
        
        # Обновляем интерфейс
        self.load_sessions()
        self.update_statistics()
        
    def update_statistics(self):
        """
        Обновляет статистику и графики.
        """
        if not self.stats_db:
            return
            
        try:
            # Обновляем общую статистику в БД
            self.stats_db.update_overall_statistics()
            
            # Получаем общую статистику
            stats = self.stats_db.get_overall_statistics()
            
            # Обновляем сетку с основными показателями
            self.stats_grid.update_stats(stats)
            
            # Получаем распределение мест
            places_distribution = self.stats_db.get_places_distribution()
            
            # Обновляем гистограмму
            self.place_chart.update_chart(places_distribution)
            
            # Отображаем сообщение
            self.status_bar.showMessage("Статистика обновлена")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось обновить статистику: {str(e)}"
            )
            
def update_session_statistics(self, session_id):
    """
    Обновляет статистику конкретной сессии.
    
    Args:
        session_id: ID сессии
    """
    if not self.stats_db:
        return
        
    try:
        # Получаем статистику сессии
        session_stats = self.stats_db.get_session_stats(session_id)
        
        if not session_stats:
            return
            
        # Подготавливаем данные для отображения
        stats = {
            'total_tournaments': session_stats['tournaments_count'],
            'total_knockouts': session_stats['knockouts_count'],
            'avg_finish_place': session_stats['avg_finish_place'],
            'total_prize': session_stats['total_prize'],
            
            # Получаем данные о местах из турниров сессии
            'first_places': 0,
            'second_places': 0,
            'third_places': 0,
            'total_knockouts_x2': 0,
            'total_knockouts_x10': 0,
            'total_knockouts_x100': 0,
            'total_knockouts_x1000': 0,
            'total_knockouts_x10000': 0
        }
        
        # Получаем турниры сессии
        tournaments = self.stats_db.get_session_tournaments(session_id)
        
        # Заполняем данные о местах и нокаутах
        for tournament in tournaments:
            place = tournament.get('finish_place')
            if place == 1:
                stats['first_places'] += 1
            elif place == 2:
                stats['second_places'] += 1
            elif place == 3:
                stats['third_places'] += 1
                
            stats['total_knockouts_x2'] += tournament.get('knockouts_x2', 0)
            stats['total_knockouts_x10'] += tournament.get('knockouts_x10', 0)
            stats['total_knockouts_x100'] += tournament.get('knockouts_x100', 0)
            stats['total_knockouts_x1000'] += tournament.get('knockouts_x1000', 0)
            stats['total_knockouts_x10000'] += tournament.get('knockouts_x10000', 0)
            
        # Обновляем сетку с основными показателями
        self.stats_grid.update_stats(stats)
        
        # Получаем распределение мест для сессии
        places_distribution = {i: 0 for i in range(1, 10)}
        for tournament in tournaments:
            place = tournament.get('finish_place')
            if place and 1 <= place <= 9:
                places_distribution[place] += 1
                
        # Обновляем гистограмму
        self.place_chart.update_chart(places_distribution)
        
        # Отображаем сообщение
        self.status_bar.showMessage(f"Статистика сессии '{session_stats['session_name']}' обновлена")
    except Exception as e:
        QMessageBox.critical(
            self,
            "Ошибка",
            f"Не удалось обновить статистику сессии: {str(e)}"
        )
                    
    def load_all_tournaments(self):
        """
        Загружает список всех турниров.
        """
        if not self.stats_db:
            return
            
        try:
            # Получаем все турниры
            self.db_manager.cursor.execute(
                "SELECT t.*, (SELECT COUNT(*) FROM knockouts k WHERE k.tournament_id = t.tournament_id) as knockouts_count FROM tournaments t ORDER BY start_time DESC"
            )
            tournaments = self.db_manager.cursor.fetchall()
            
            # Отображаем турниры в таблице
            self._update_tournaments_table(tournaments)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось загрузить турниры: {str(e)}"
            )
            
    def load_session_tournaments(self, session_id):
        """
        Загружает список турниров конкретной сессии.
        
        Args:
            session_id: ID сессии
        """
        if not self.stats_db:
            return
            
        try:
            # Получаем турниры сессии с количеством нокаутов для каждого
            self.db_manager.cursor.execute(
                """
                SELECT t.*, 
                       (SELECT COUNT(*) FROM knockouts k WHERE k.tournament_id = t.tournament_id 
                        AND k.session_id = t.session_id) as knockouts_count
                FROM tournaments t 
                WHERE t.session_id = ? 
                ORDER BY start_time DESC
                """,
                (session_id,)
            )
            tournaments = self.db_manager.cursor.fetchall()
            
            # Отображаем турниры в таблице
            self._update_tournaments_table(tournaments)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось загрузить турниры сессии: {str(e)}"
            )
            
    def _update_tournaments_table(self, tournaments):
        """
        Обновляет таблицу турниров.
        
        Args:
            tournaments: Список турниров
        """
        # Очищаем таблицу
        self.tournaments_table.setRowCount(0)
        
        # Заполняем таблицу
        for row, tournament in enumerate(tournaments):
            self.tournaments_table.insertRow(row)
            
            # ID турнира
            self.tournaments_table.setItem(
                row, 0, QTableWidgetItem(str(tournament['tournament_id']))
            )
            
            # Buy-in
            buy_in = tournament.get('buy_in', 0)
            self.tournaments_table.setItem(
                row, 1, QTableWidgetItem(f"${buy_in:.2f}" if buy_in else '')
            )
            
            # Место
            self.tournaments_table.setItem(
                row, 2, QTableWidgetItem(str(tournament.get('finish_place', '')))
            )
            
            # Выигрыш
            prize = tournament.get('prize', 0)
            self.tournaments_table.setItem(
                row, 3, QTableWidgetItem(f"${prize:.2f}" if prize else '')
            )
            
            # Нокаутов
            knockouts_count = tournament.get('knockouts_count', 0)
            self.tournaments_table.setItem(
                row, 4, QTableWidgetItem(str(knockouts_count))
            )
            
            # x10 Нокауты
            self.tournaments_table.setItem(
                row, 5, QTableWidgetItem(str(tournament.get('knockouts_x10', 0)))
            )
            
            # Дата
            start_time = tournament.get('start_time', '')
            self.tournaments_table.setItem(
                row, 6, QTableWidgetItem(str(start_time))
            )
            
    def clear_all_data(self):
        """
        Очищает все данные в текущей базе.
        """
        if not self.stats_db:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Сначала выберите базу данных!"
            )
            return
            
        # Запрашиваем подтверждение
        reply = QMessageBox.question(
            self,
            "Подтверждение очистки",
            "Вы уверены, что хотите очистить все данные в базе?\n"
            "Это действие невозможно отменить!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Очищаем данные
                self.stats_db.clear_all_data()
                
                # Обновляем интерфейс
                self.load_sessions()
                self.update_statistics()
                
                # Очищаем таблицы
                self.tournaments_table.setRowCount(0)
                
                # Отображаем сообщение
                self.status_bar.showMessage("Все данные успешно очищены")
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось очистить данные: {str(e)}"
                )
                
    def closeEvent(self, event):
        """
        Обработчик закрытия окна приложения.
        """
        # Ждем завершения всех потоков
        self.threadpool.waitForDone()
        
        # Закрываем соединение с БД, если оно открыто
        if self.db_manager:
            self.db_manager.close()
            
        # Принимаем событие закрытия
        event.accept()