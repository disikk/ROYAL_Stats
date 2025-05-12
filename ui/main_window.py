#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Главное окно покерного трекера ROYAL_Stats.
"""

import os
import uuid
import logging
import re
import sqlite3 
import dataclasses 
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTabWidget, QFileDialog, QMessageBox, QProgressBar,
    QStatusBar, QSplitter, QTreeWidget, QTreeWidgetItem, QMenu,
    QDialog, QInputDialog, QHeaderView, QTableWidget, QTableWidgetItem,
    QGroupBox, QScrollArea
)
from PyQt6.QtCore import Qt, QThreadPool, QRunnable, pyqtSignal, pyqtSlot, QObject, QSize, QThread 
from PyQt6.QtGui import QAction, QIcon, QFont

from db.database import DatabaseManager, StatsDatabase
from ui.db_dialog import DatabaseDialog
from ui.visualizations import PlaceDistributionChart, StatsGrid # Используем royal_stats_visualizations_py_v2
from parsers.hand_history import HandHistoryParser
from parsers.tournament_summary import TournamentSummaryParser, TournamentSummary 

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
        
        self.worker_logger = logging.getLogger('ROYAL_Stats.Worker') 
        
    @pyqtSlot()
    def run(self):
        """
        Выполняет функцию в отдельном потоке.
        """
        try:
            self.signals.started.emit()
            self.worker_logger.debug(f"Worker начал выполнение функции {self.fn.__name__}")
            
            current_kwargs = self.kwargs.copy()
            current_kwargs['worker_signals'] = self.signals
            
            result = self.fn(*self.args, **current_kwargs)
            
            self.signals.result.emit(result)
            self.worker_logger.debug(f"Worker успешно выполнил функцию {self.fn.__name__}")
            
        except Exception as e:
            self.worker_logger.error(f"Ошибка в Worker при выполнении {self.fn.__name__}: {str(e)}", 
                            exc_info=True)
            self.signals.error.emit(str(e))
            
        finally:
            self.signals.finished.emit()
            self.worker_logger.debug(f"Worker завершил выполнение функции {self.fn.__name__}")

class MainWindow(QMainWindow):
    """
    Главное окно приложения ROYAL_Stats.
    """
    
    def __init__(self):
        super().__init__()
        
        self.db_manager = DatabaseManager(db_folder='databases')
        self.stats_db = None 
        
        self.hand_history_parser = HandHistoryParser()
        self.tournament_summary_parser = TournamentSummaryParser(hero_name="Hero") 
        
        self.threadpool = QThreadPool()
        logger.info(f"Максимальное количество потоков в пуле: {self.threadpool.maxThreadCount()}")
        
        self.current_session_id = None
        self.current_db_path = None 
        
        self._init_ui()
        self.show_database_dialog()
        
    def _init_ui(self):
        """
        Инициализирует элементы интерфейса.
        """
        self.setWindowTitle("Royal Stats by disikk")
        self.setMinimumSize(1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        toolbar_layout = QHBoxLayout()
        
        self.db_button = QPushButton("Выбрать БД")
        self.db_button.clicked.connect(self.show_database_dialog)
        toolbar_layout.addWidget(self.db_button)
        
        self.load_files_button = QPushButton("Загрузить файлы")
        self.load_files_button.clicked.connect(self.load_files)
        self.load_files_button.setEnabled(False)  
        toolbar_layout.addWidget(self.load_files_button)
        
        self.db_name_label = QLabel("База данных не выбрана")
        self.db_name_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        font = QFont()
        font.setBold(True)
        self.db_name_label.setFont(font)
        toolbar_layout.addWidget(self.db_name_label)
        
        main_layout.addLayout(toolbar_layout)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.sessions_tree = QTreeWidget()
        self.sessions_tree.setHeaderLabels(["Сессии"])
        self.sessions_tree.setMinimumWidth(250)
        self.sessions_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sessions_tree.customContextMenuRequested.connect(self.show_session_context_menu)
        self.sessions_tree.itemClicked.connect(self.on_session_selected)
        
        self.tabs = QTabWidget()
        
        self.stats_tab = QWidget()
        stats_layout = QVBoxLayout(self.stats_tab)
        
        self.stats_grid = StatsGrid()
        stats_layout.addWidget(self.stats_grid)
        
        self.place_chart = PlaceDistributionChart()
        stats_layout.addWidget(self.place_chart)
        
        self.tournaments_tab = QWidget()
        tournaments_layout = QVBoxLayout(self.tournaments_tab)
        
        self.tournaments_table = QTableWidget()
        self.tournaments_table.setColumnCount(7)
        self.tournaments_table.setHorizontalHeaderLabels([
            "ID турнира", "Buy-in", "Место", "Выигрыш", "Нокаутов", "x10 Нокауты", "Дата"
        ])
        self.tournaments_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tournaments_layout.addWidget(self.tournaments_table)
        
        self.tabs.addTab(self.stats_tab, "Статистика")
        self.tabs.addTab(self.tournaments_tab, "Турниры")
        
        splitter.addWidget(self.sessions_tree)
        splitter.addWidget(self.tabs)
        splitter.setSizes([250, 950])
        main_layout.addWidget(splitter)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готово")
        
        self._create_menu()
        
    def _create_menu(self):
        """
        Создает главное меню приложения.
        """
        file_menu = self.menuBar().addMenu("Файл")
        
        select_db_action = QAction("Выбрать базу данных", self)
        select_db_action.triggered.connect(self.show_database_dialog)
        file_menu.addAction(select_db_action)
        
        load_files_action = QAction("Загрузить файлы", self)
        load_files_action.triggered.connect(self.load_files)
        file_menu.addAction(load_files_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        session_menu = self.menuBar().addMenu("Сессия")
        
        new_session_action = QAction("Новая сессия", self)
        new_session_action.triggered.connect(self.create_new_session)
        session_menu.addAction(new_session_action)
        
        rename_session_action = QAction("Переименовать сессию", self)
        rename_session_action.triggered.connect(self.rename_selected_session)
        session_menu.addAction(rename_session_action)
        
        delete_session_action = QAction("Удалить сессию", self)
        delete_session_action.triggered.connect(self.delete_selected_session)
        session_menu.addAction(delete_session_action)
        
        tools_menu = self.menuBar().addMenu("Инструменты")
        
        update_stats_action = QAction("Обновить статистику", self)
        update_stats_action.triggered.connect(self.update_statistics)
        tools_menu.addAction(update_stats_action)
        
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
        
    def on_database_selected(self, db_path: str):
        """
        Обработчик выбора базы данных.
        """
        self.current_db_path = db_path 
        db_name = os.path.basename(db_path)
        
        self.db_name_label.setText(f"База данных: {db_name}")
        self.load_files_button.setEnabled(True)
        
        try:
            self.db_manager.connect(self.current_db_path) 
            self.stats_db = StatsDatabase(self.db_manager)
            
            self.load_sessions()
            self.update_statistics()
            self.status_bar.showMessage(f"Подключено к базе данных {db_name}")
        except Exception as e:
            logger.error(f"Ошибка при инициализации StatsDatabase или загрузке данных: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться или загрузить данные из БД: {str(e)}")
            self.load_files_button.setEnabled(False)
            self.db_name_label.setText("Ошибка подключения к БД")

            
    def load_sessions(self):
        """
        Загружает список сессий из базы данных.
        """
        if not self.stats_db:
            logger.warning("Попытка загрузить сессии без инициализированного self.stats_db")
            return
            
        self.sessions_tree.clear()
        
        all_sessions_item = QTreeWidgetItem(["Все сессии"])
        all_sessions_item.setData(0, Qt.ItemDataRole.UserRole, "all")
        self.sessions_tree.addTopLevelItem(all_sessions_item)
        
        try:
            sessions = self.stats_db.get_sessions()
            for session in sessions:
                session_name = session['session_name']
                session_id = session['session_id']
                item_text = f"{session_name} ({session.get('tournaments_count', 0)} турниров)"
                session_item = QTreeWidgetItem([item_text])
                session_item.setData(0, Qt.ItemDataRole.UserRole, session_id)
                self.sessions_tree.addTopLevelItem(session_item)
                
            self.sessions_tree.expandAll()
            if self.sessions_tree.topLevelItemCount() > 0:
                 self.sessions_tree.setCurrentItem(all_sessions_item)
                 self.on_session_selected(all_sessions_item, 0)

        except Exception as e:
            logger.error(f"Не удалось загрузить сессии: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить сессии: {str(e)}")
            
    def on_session_selected(self, item: QTreeWidgetItem, column: int = 0):
        """
        Обработчик выбора сессии в дереве.
        """
        if not item: 
            return

        session_id = item.data(0, Qt.ItemDataRole.UserRole)
        
        if session_id == "all":
            self.current_session_id = None
            self.update_statistics() 
            self.load_all_tournaments()
        else:
            self.current_session_id = session_id
            self.update_session_statistics(session_id)
            self.load_session_tournaments(session_id)
            
    def show_session_context_menu(self, position):
        """
        Показывает контекстное меню для сессии.
        """
        item = self.sessions_tree.itemAt(position)
        if not item:
            return
            
        session_id = item.data(0, Qt.ItemDataRole.UserRole)
        if session_id == "all":
            return
            
        menu = QMenu(self)
        rename_action = menu.addAction("Переименовать")
        delete_action = menu.addAction("Удалить")
        
        action = menu.exec(self.sessions_tree.mapToGlobal(position))
        
        if action == rename_action:
            self.rename_session(session_id)
        elif action == delete_action:
            self.delete_session(session_id)
            
    def rename_session(self, session_id: str):
        """
        Переименовывает сессию.
        """
        if not self.stats_db: return

        session_info = self.stats_db.get_session_stats(session_id)
        if not session_info:
            return
            
        new_name, ok = QInputDialog.getText(
            self, "Переименование сессии", "Введите новое название для сессии:",
            text=session_info['session_name']
        )
        
        if ok and new_name:
            try:
                self.db_manager.cursor.execute(
                    "UPDATE sessions SET session_name = ? WHERE session_id = ?",
                    (new_name, session_id)
                )
                self.db_manager.connection.commit()
                self.load_sessions()
                self.status_bar.showMessage(f"Сессия успешно переименована")
            except Exception as e:
                logger.error(f"Не удалось переименовать сессию: {str(e)}", exc_info=True)
                QMessageBox.critical(self, "Ошибка", f"Не удалось переименовать сессию: {str(e)}")
                
    def delete_session(self, session_id: str):
        """
        Удаляет сессию.
        """
        if not self.stats_db: return

        reply = QMessageBox.question(
            self, "Подтверждение удаления",
            "Вы уверены, что хотите удалить эту сессию?\nЭто действие невозможно отменить!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.stats_db.delete_session(session_id)
                self.load_sessions() 
                if self.current_session_id == session_id:
                    self.current_session_id = None
                    if self.sessions_tree.topLevelItemCount() > 0:
                        self.sessions_tree.setCurrentItem(self.sessions_tree.topLevelItem(0))
                        self.on_session_selected(self.sessions_tree.topLevelItem(0))
                    else: 
                        self.update_statistics() 
                        self.load_all_tournaments() 

                self.status_bar.showMessage(f"Сессия успешно удалена")
            except Exception as e:
                logger.error(f"Не удалось удалить сессию: {str(e)}", exc_info=True)
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить сессию: {str(e)}")
                
    def rename_selected_session(self):
        """ Переименовывает выбранную сессию. """
        item = self.sessions_tree.currentItem()
        if not item or item.data(0, Qt.ItemDataRole.UserRole) == "all":
            return
        self.rename_session(item.data(0, Qt.ItemDataRole.UserRole))
        
    def delete_selected_session(self):
        """ Удаляет выбранную сессию. """
        item = self.sessions_tree.currentItem()
        if not item or item.data(0, Qt.ItemDataRole.UserRole) == "all":
            return
        self.delete_session(item.data(0, Qt.ItemDataRole.UserRole))
        
    def create_new_session(self) -> Optional[str]:
        """ Создает новую сессию. """
        if not self.stats_db:
            QMessageBox.warning(self, "Предупреждение", "Сначала выберите базу данных!")
            return None
            
        name, ok = QInputDialog.getText(self, "Новая сессия", "Введите название для новой сессии:")
        
        if ok and name:
            try:
                session_id = self.stats_db.create_session(name)
                self.load_sessions()
                for i in range(self.sessions_tree.topLevelItemCount()):
                    item = self.sessions_tree.topLevelItem(i)
                    if item.data(0, Qt.ItemDataRole.UserRole) == session_id:
                        self.sessions_tree.setCurrentItem(item)
                        self.on_session_selected(item) 
                        break
                self.status_bar.showMessage(f"Сессия '{name}' успешно создана")
                return session_id
            except Exception as e:
                logger.error(f"Не удалось создать сессию: {str(e)}", exc_info=True)
                QMessageBox.critical(self, "Ошибка", f"Не удалось создать сессию: {str(e)}")
        return None
        
    def load_files(self):
        """ Загружает файлы истории рук и сводки турниров. """
        if not self.stats_db or not self.current_db_path: 
            QMessageBox.warning(self, "Предупреждение", "Сначала выберите базу данных!")
            return
            
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles) 
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, False)
        dialog.setWindowTitle("Выберите файлы или папки с историей")
        dialog.setNameFilter("Текстовые файлы (*.txt);;Все файлы (*)")


        file_paths_to_process = []
        if dialog.exec():
            selected_items = dialog.selectedFiles()
            for item_path in selected_items:
                if os.path.isdir(item_path):
                    for root, _, files in os.walk(item_path):
                        for file in files:
                            if file.endswith('.txt'): 
                                file_paths_to_process.append(os.path.join(root, file))
                elif os.path.isfile(item_path) and item_path.endswith('.txt'): 
                     file_paths_to_process.append(item_path)
        
        if not file_paths_to_process:
            return
            
        session_id_for_processing = self.current_session_id
        if not session_id_for_processing or session_id_for_processing == "all":
            session_id_for_processing = self.create_new_session()
            if not session_id_for_processing: 
                return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(file_paths_to_process)) 
        self.progress_bar.setValue(0)
        
        self.load_files_button.setEnabled(False)
        
        worker = Worker(self._process_files_worker, file_paths_to_process, session_id_for_processing)
        
        worker.signals.started.connect(lambda: self.status_bar.showMessage("Обработка файлов началась..."))
        worker.signals.finished.connect(self.on_files_processing_finished)
        worker.signals.error.connect(self.on_files_processing_error)
        worker.signals.result.connect(self.on_files_processing_result)
        worker.signals.progress.connect(self.progress_bar.setValue) 
        
        self.threadpool.start(worker)
        
    def _process_files_worker(self, file_paths: List[str], session_id: str, worker_signals: WorkerSignals):
        """
        Функция для обработки файлов в отдельном потоке.
        """
        worker_logger = logging.getLogger('ROYAL_Stats.Worker') 
        worker_logger.debug(f"Worker thread ({QThread.currentThreadId()}) for session {session_id} started processing {len(file_paths)} files.")
        
        worker_db_manager = DatabaseManager(db_folder=self.db_manager.db_folder)
        worker_stats_db = None
        try:
            if not self.current_db_path: 
                err_msg = "Путь к базе данных не установлен перед запуском worker."
                worker_logger.error(err_msg)
                raise Exception(err_msg) 
            
            worker_logger.debug(f"Worker connecting to DB: {self.current_db_path}")
            worker_db_manager.connect(self.current_db_path)
            worker_stats_db = StatsDatabase(worker_db_manager)
            worker_logger.debug(f"Worker DB connection successful.")
            
            results = self.process_files(file_paths, session_id, 
                                         stats_db_instance=worker_stats_db, 
                                         progress_signal=worker_signals.progress)
            worker_logger.debug(f"Worker processing finished. Results: {results}")
            return results
        except Exception as e:
            worker_logger.error(f"Критическая ошибка в _process_files_worker: {str(e)}", exc_info=True)
            raise 
        finally:
            if worker_db_manager:
                worker_logger.debug(f"Worker closing DB connection.")
                worker_db_manager.close()
            worker_logger.debug(f"Worker thread ({QThread.currentThreadId()}) finished.")

        
    def process_files(self, file_paths: List[str], session_id: str, 
                      stats_db_instance: StatsDatabase, progress_signal: Optional[pyqtSignal] = None):
        """
        Обрабатывает файлы истории рук и сводки турниров.
        """
        current_stats_db = stats_db_instance 

        if not current_stats_db:
            error_msg = "Экземпляр StatsDatabase не предоставлен в process_files."
            logger.error(error_msg) 
            return {'errors': [error_msg]} 

        hand_history_files = []
        tournament_summary_files = []
        
        progress_value = 0
        
        for file_path in file_paths:
            file_name = os.path.basename(file_path)
            
            if '9max' in file_name.lower() and file_name.endswith('.txt'): 
                hand_history_files.append(file_path)
            elif 'tournament #' in file_name.lower() and 'mystery battle royale' in file_name.lower() and file_name.endswith('.txt'):
                tournament_summary_files.append(file_path)
            # else:
            #     logger.info(f"Файл {file_name} не соответствует известным шаблонам и будет пропущен.")

            progress_value += 1
            if progress_signal:
                progress_signal.emit(progress_value)
                
        results = {
            'total_files': len(file_paths),
            'tournament_summary_files_found': len(tournament_summary_files), 
            'hand_history_files_found': len(hand_history_files),       
            'processed_tournaments': 0,
            'processed_knockouts': 0,
            'skipped_tournaments_high_finish_place': 0, # Счетчик пропущенных турниров
            'errors': []
        }
        
        logger.info(f"Найдено файлов сводки турниров: {len(tournament_summary_files)}")
        logger.info(f"Найдено файлов истории рук: {len(hand_history_files)}")

        for file_path in tournament_summary_files:
            try:
                logger.debug(f"Парсинг файла сводки турнира: {file_path}")
                tournament_data_obj = self.tournament_summary_parser.parse_file(file_path)
                
                # Проверяем finish_place перед сохранением
                if tournament_data_obj.finish_place >= 10:
                    logger.info(f"Турнир {tournament_data_obj.tournament_id} из файла {file_path} пропущен (finish_place: {tournament_data_obj.finish_place} >= 10).")
                    results['skipped_tournaments_high_finish_place'] += 1
                    continue # Переходим к следующему файлу

                if isinstance(tournament_data_obj, TournamentSummary):
                    data_to_save = dataclasses.asdict(tournament_data_obj)
                else: 
                    data_to_save = tournament_data_obj.__dict__ if hasattr(tournament_data_obj, '__dict__') else dict(tournament_data_obj)

                current_stats_db.save_tournament_data(data_to_save, session_id)
                results['processed_tournaments'] += 1
                logger.debug(f"Успешно обработан файл сводки: {file_path}")
            except Exception as e:
                err_msg = f"Ошибка при обработке файла сводки {file_path}: {str(e)}"
                logger.error(err_msg, exc_info=True)
                results['errors'].append(err_msg)
                
        for file_path in hand_history_files:
            try:
                logger.debug(f"Парсинг файла истории рук: {file_path}")
                hand_history_data = self.hand_history_parser.parse_file(file_path) 
                if hand_history_data.get('tournament_id') and hand_history_data.get('knockouts'):
                    # Здесь не нужна проверка finish_place, так как это история рук, а не сводка турнира
                    current_stats_db.save_knockouts_data(
                        hand_history_data['tournament_id'],
                        hand_history_data['knockouts'],
                        session_id
                    )
                    results['processed_knockouts'] += len(hand_history_data['knockouts'])
                logger.debug(f"Успешно обработан файл истории рук: {file_path}")
            except Exception as e:
                err_msg = f"Ошибка при обработке файла истории рук {file_path}: {str(e)}"
                logger.error(err_msg, exc_info=True)
                results['errors'].append(err_msg)
                
        try:
            logger.debug(f"Обновление статистики сессии {session_id}")
            current_stats_db.update_session_stats(session_id)
            logger.debug(f"Обновление общей статистики")
            current_stats_db.update_overall_statistics()
        except Exception as e:
            err_msg = f"Ошибка при обновлении статистики после обработки файлов: {str(e)}"
            logger.error(err_msg, exc_info=True)
            results['errors'].append(err_msg)
            
        return results

    def on_files_processing_result(self, results: Dict):
        """ Обработчик получения результатов обработки файлов. """
        if not isinstance(results, dict): 
            logger.error(f"Получен некорректный результат обработки файлов: {results}")
            QMessageBox.critical(self, "Критическая ошибка", "Внутренняя ошибка при обработке файлов.")
            return

        if results.get('errors'):
            error_message = "При обработке файлов возникли ошибки:\n\n"
            error_message += "\n".join(results['errors'][:5])
            if len(results['errors']) > 5:
                error_message += f"\n\n...и еще {len(results['errors']) - 5} ошибок."
            QMessageBox.warning(self, "Предупреждение", error_message)
        
        stats_message = (
            f"Всего файлов для обработки: {results.get('total_files', 0)}\n"
            f"Найдено файлов сводки: {results.get('tournament_summary_files_found', 0)}\n"
            f"Найдено файлов истории: {results.get('hand_history_files_found', 0)}\n"
            f"Обработано турниров: {results.get('processed_tournaments',0)}\n"
            f"Пропущено турниров (место >= 10): {results.get('skipped_tournaments_high_finish_place',0)}\n" # Новая строка
            f"Обработано нокаутов: {results.get('processed_knockouts',0)}"
        )
        self.status_bar.showMessage(stats_message, 10000) 
        
    def on_files_processing_finished(self):
        """ Обработчик завершения обработки файлов. """
        self.progress_bar.setVisible(False)
        self.load_files_button.setEnabled(True)
        
        self.load_sessions() 
        
        current_item = self.sessions_tree.currentItem()
        if current_item:
            self.on_session_selected(current_item)
        else: 
            self.update_statistics()
            
        self.status_bar.showMessage("Обработка файлов завершена", 5000)
        
    def on_files_processing_error(self, error_message: str):
        """ Обработчик ошибки при обработке файлов. """
        self.progress_bar.setVisible(False)
        self.load_files_button.setEnabled(True)
        
        QMessageBox.critical(self, "Ошибка", f"Ошибка при обработке файлов: {error_message}")
        
        self.load_sessions()
        current_item = self.sessions_tree.currentItem()
        if current_item:
            self.on_session_selected(current_item)
        else:
            self.update_statistics()
        
    def update_statistics(self):
        """ Обновляет общую статистику и графики. """
        if not self.stats_db:
            return
        try:
            self.stats_db.update_overall_statistics() 
            stats = self.stats_db.get_overall_statistics()
            self.stats_grid.update_stats(stats)
            places_distribution = self.stats_db.get_places_distribution()
            self.place_chart.update_chart(places_distribution)
            self.status_bar.showMessage("Общая статистика обновлена", 3000)
        except Exception as e:
            logger.error(f"Не удалось обновить общую статистику: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить общую статистику: {str(e)}")
            
    def update_session_statistics(self, session_id: str):
        """ Обновляет статистику конкретной сессии. """
        if not self.stats_db:
            return
        try:
            self.stats_db.update_session_stats(session_id) 
            session_stats_from_db = self.stats_db.get_session_stats(session_id)
            
            if not session_stats_from_db:
                logger.warning(f"Статистика для сессии {session_id} не найдена.")
                self.stats_grid.update_stats({}) 
                self.place_chart.update_chart({i: 0 for i in range(1, 10)}) 
                return
                
            stats_for_grid = {
                'total_tournaments': session_stats_from_db.get('tournaments_count', 0),
                'total_knockouts': session_stats_from_db.get('knockouts_count', 0),
                'avg_finish_place': session_stats_from_db.get('avg_finish_place', 0.0),
                'total_prize': session_stats_from_db.get('total_prize', 0.0),
                'first_places': 0, 'second_places': 0, 'third_places': 0,
                'total_knockouts_x2': 0, 'total_knockouts_x10': 0,
                'total_knockouts_x100': 0, 'total_knockouts_x1000': 0,
                'total_knockouts_x10000': 0
            }

            tournaments_in_session = self.stats_db.get_session_tournaments(session_id)
            places_distribution_session = {i: 0 for i in range(1, 10)}

            for tournament in tournaments_in_session:
                place = tournament.get('finish_place')
                if place == 1: stats_for_grid['first_places'] += 1
                elif place == 2: stats_for_grid['second_places'] += 1
                elif place == 3: stats_for_grid['third_places'] += 1
                
                # Для гистограммы мест сессии используем нормализованное место
                # только если фактическое место находится в диапазоне 1-9.
                # Турниры с местом >= 10 уже не должны попадать в БД.
                if place and 1 <= place <= 9: 
                    players_count_in_tournament = tournament.get('players_count', 9) or 9 
                    from math import ceil 
                    normalized_place = min(max(ceil(place / players_count_in_tournament * 9.0), 1), 9) 
                    places_distribution_session[normalized_place] +=1


                stats_for_grid['total_knockouts_x2'] += tournament.get('knockouts_x2', 0)
                stats_for_grid['total_knockouts_x10'] += tournament.get('knockouts_x10', 0)
                stats_for_grid['total_knockouts_x100'] += tournament.get('knockouts_x100', 0)
                stats_for_grid['total_knockouts_x1000'] += tournament.get('knockouts_x1000', 0)
                stats_for_grid['total_knockouts_x10000'] += tournament.get('knockouts_x10000', 0)
                
            self.stats_grid.update_stats(stats_for_grid)
            self.place_chart.update_chart(places_distribution_session) 
            
            self.status_bar.showMessage(f"Статистика сессии '{session_stats_from_db.get('session_name', session_id)}' обновлена", 3000)
        except Exception as e:
            logger.error(f"Не удалось обновить статистику сессии {session_id}: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить статистику сессии: {str(e)}")
                    
    def load_all_tournaments(self):
        """ Загружает список всех турниров. """
        if not self.stats_db: return
        try:
            self.db_manager.cursor.execute(
                """
                SELECT t.*, 
                       (SELECT COUNT(k.id) FROM knockouts k WHERE k.tournament_id = t.tournament_id) as knockouts_count 
                FROM tournaments t 
                ORDER BY t.start_time DESC
                """
            )
            tournaments = self.db_manager.cursor.fetchall() 
            self._update_tournaments_table(tournaments)
        except Exception as e:
            logger.error(f"Не удалось загрузить все турниры: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить турниры: {str(e)}")
            
    def load_session_tournaments(self, session_id: str):
        """ Загружает список турниров конкретной сессии. """
        if not self.stats_db: return
        try:
            self.db_manager.cursor.execute(
                """
                SELECT t.*, 
                       (SELECT COUNT(k.id) FROM knockouts k 
                        WHERE k.tournament_id = t.tournament_id AND k.session_id = t.session_id) as knockouts_count
                FROM tournaments t 
                WHERE t.session_id = ? 
                ORDER BY t.start_time DESC
                """, (session_id,)
            )
            tournaments = self.db_manager.cursor.fetchall()
            self._update_tournaments_table(tournaments)
        except Exception as e:
            logger.error(f"Не удалось загрузить турниры сессии {session_id}: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить турниры сессии: {str(e)}")
            
    def _update_tournaments_table(self, tournaments: List[sqlite3.Row]):
        """ 
        Обновляет таблицу турниров.
        """
        self.tournaments_table.setRowCount(0)
        for row_idx, tournament_row in enumerate(tournaments):
            tournament = dict(tournament_row)
            self.tournaments_table.insertRow(row_idx)
            
            self.tournaments_table.setItem(row_idx, 0, QTableWidgetItem(str(tournament.get('tournament_id', 'N/A'))))
            buy_in = tournament.get('buy_in', 0)
            self.tournaments_table.setItem(row_idx, 1, QTableWidgetItem(f"${buy_in:.2f}" if buy_in is not None else 'N/A'))
            self.tournaments_table.setItem(row_idx, 2, QTableWidgetItem(str(tournament.get('finish_place', 'N/A'))))
            prize = tournament.get('prize', 0)
            self.tournaments_table.setItem(row_idx, 3, QTableWidgetItem(f"${prize:.2f}" if prize is not None else 'N/A'))
            self.tournaments_table.setItem(row_idx, 4, QTableWidgetItem(str(tournament.get('knockouts_count', 0)))) 
            x10_ko = tournament.get('knockouts_x10', 0)
            self.tournaments_table.setItem(row_idx, 5, QTableWidgetItem(str(x10_ko if x10_ko is not None else 0)))
            start_time_str = tournament.get('start_time', 'N/A')
            try:
                if start_time_str and start_time_str != 'N/A':
                    dt_obj = None
                    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
                        try:
                            dt_obj = datetime.strptime(start_time_str, fmt)
                            break
                        except ValueError:
                            continue
                    if dt_obj:
                         formatted_time = dt_obj.strftime('%Y-%m-%d %H:%M')
                    else: 
                        formatted_time = start_time_str 
                else:
                    formatted_time = 'N/A'
            except Exception: 
                formatted_time = start_time_str 

            self.tournaments_table.setItem(row_idx, 6, QTableWidgetItem(formatted_time))
            
    def clear_all_data(self):
        """ Очищает все данные в текущей базе. """
        if not self.stats_db:
            QMessageBox.warning(self, "Предупреждение", "Сначала выберите базу данных!")
            return
            
        reply = QMessageBox.question(
            self, "Подтверждение очистки",
            "Вы уверены, что хотите очистить все данные в базе?\nЭто действие невозможно отменить!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.stats_db.clear_all_data()
                self.load_sessions() 
                self.update_statistics() 
                self.tournaments_table.setRowCount(0) 
                self.status_bar.showMessage("Все данные успешно очищены")
            except Exception as e:
                logger.error(f"Не удалось очистить данные: {str(e)}", exc_info=True)
                QMessageBox.critical(self, "Ошибка", f"Не удалось очистить данные: {str(e)}")
                
    def closeEvent(self, event):
        """ Обработчик закрытия окна приложения. """
        logger.info("Закрытие приложения. Ожидание завершения потоков...")
        self.threadpool.waitForDone(-1) 
        logger.info("Все потоки завершены.")
        
        if self.db_manager:
            logger.info("Закрытие соединения с БД.")
            self.db_manager.close()
            
        event.accept()

