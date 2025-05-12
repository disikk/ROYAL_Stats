#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для работы с базой данных в покерном трекере ROYAL_Stats.
Содержит классы для управления подключением к БД и выполнения запросов.
"""

import os
import sqlite3
import uuid
import logging
from typing import Dict, List, Optional, Union, Tuple, Any
from datetime import datetime

from db.schema import (
    CREATE_TABLES_QUERIES, INSERT_TOURNAMENT, INSERT_KNOCKOUT,
    UPDATE_STATISTICS, INSERT_INITIAL_STATISTICS, UPSERT_PLACE_DISTRIBUTION,
    INSERT_SESSION, GET_STATISTICS, GET_PLACES_DISTRIBUTION,
    GET_SESSIONS, GET_SESSION_BY_ID, GET_TOURNAMENTS_BY_SESSION,
    GET_KNOCKOUTS_BY_SESSION, DELETE_SESSION_DATA, DELETE_ALL_DATA
)

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.Database')


class DatabaseManager:
    """
    Класс для управления подключением к базе данных SQLite.
    """
    
    def __init__(self, db_folder='databases'):
        """
        Инициализирует менеджер БД.
        
        Args:
            db_folder: Путь к папке с базами данных
        """
        # Путь к папке с БД
        self.db_folder = db_folder
        
        # Создаем папку, если она не существует
        if not os.path.exists(db_folder):
            os.makedirs(db_folder)
            
        # Объявляем атрибуты для соединения и курсора
        self.connection = None
        self.cursor = None
        self.current_db_path = None
        
    def connect(self, db_path: str) -> None:
        """
        Подключается к указанной базе данных.
        
        Args:
            db_path: Путь к файлу базы данных
        """
        try:
            # Закрываем текущее соединение, если оно открыто
            if self.connection:
                self.close()
                
            # Создаем новое соединение
            self.connection = sqlite3.connect(db_path)
            self.connection.row_factory = sqlite3.Row  # Для доступа к результатам по имени столбца
            self.cursor = self.connection.cursor()
            self.current_db_path = db_path
            
            # Создаем таблицы, если их нет
            self._create_tables()
            
            logger.info(f"Подключено к базе данных: {db_path}")
        except Exception as e:
            logger.error(f"Ошибка при подключении к БД {db_path}: {str(e)}")
            raise
            
    def close(self) -> None:
        """
        Закрывает соединение с базой данных.
        """
        if self.connection:
            self.connection.close()
            self.connection = None
            self.cursor = None
            self.current_db_path = None
            
    def _create_tables(self) -> None:
        """
        Создает необходимые таблицы в базе данных, если их нет.
        """
        if not self.connection:
            return
            
        for query in CREATE_TABLES_QUERIES:
            self.cursor.execute(query)
            
        self.connection.commit()
        
    def create_database(self, db_name: str) -> str:
        """
        Создает новую базу данных с указанным именем.
        
        Args:
            db_name: Имя новой базы данных
            
        Returns:
            Путь к созданной базе данных
        """
        # Формируем путь к новой БД
        db_path = os.path.join(self.db_folder, db_name)
        
        # Подключаемся к новой БД (она будет создана автоматически)
        self.connect(db_path)
        
        return db_path
        
    def get_available_databases(self) -> List[str]:
        """
        Возвращает список доступных баз данных в папке.
        
        Returns:
            Список имен файлов баз данных
        """
        # Проверяем наличие папки
        if not os.path.exists(self.db_folder):
            return []
            
        # Получаем список файлов .db в папке
        db_files = []
        for file_name in os.listdir(self.db_folder):
            if file_name.endswith('.db'):
                db_files.append(file_name)
                
        return db_files


class StatsDatabase:
    """
    Класс для работы со статистическими данными в базе.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Инициализирует объект для работы со статистикой.
        
        Args:
            db_manager: Экземпляр менеджера базы данных
        """
        self.db_manager = db_manager
        
    def save_tournament_data(self, tournament_data: Dict, session_id: str) -> None:
        """
        Сохраняет данные о турнире в базу.
        
        Args:
            tournament_data: Словарь с данными о турнире
            session_id: ID сессии загрузки
        """
        # Проверяем подключение к БД
        if not self.db_manager.connection:
            raise ValueError("Не подключена база данных")
            
        # Подготавливаем параметры для вставки
        params = (
            tournament_data.get('tournament_id'),
            tournament_data.get('tournament_name'),
            tournament_data.get('game_type'),
            tournament_data.get('buy_in'),
            tournament_data.get('fee'),
            tournament_data.get('bounty'),
            tournament_data.get('total_buy_in'),
            tournament_data.get('players_count', tournament_data.get('players', 9)),  # Поддержка обоих форматов
            tournament_data.get('prize_pool'),
            tournament_data.get('start_time'),
            tournament_data.get('finish_place'),
            tournament_data.get('prize', tournament_data.get('prize_total', 0)),  # Поддержка обоих форматов
            tournament_data.get('knockouts_x2', 0),
            tournament_data.get('knockouts_x10', 0),
            tournament_data.get('knockouts_x100', 0),
            tournament_data.get('knockouts_x1000', 0),
            tournament_data.get('knockouts_x10000', 0),
            session_id
        )
        
        # Выполняем вставку
        self.db_manager.cursor.execute(INSERT_TOURNAMENT, params)
        self.db_manager.connection.commit()
        
        # Обновляем распределение мест
        place = tournament_data.get('finish_place')
        if place and 1 <= place <= 9:
            self.db_manager.cursor.execute(UPSERT_PLACE_DISTRIBUTION, (place, 1))
            self.db_manager.connection.commit()
            
    def save_knockouts_data(self, tournament_id: str, knockouts: List[Dict], session_id: str) -> None:
        """
        Сохраняет данные о нокаутах в базу.
        
        Args:
            tournament_id: ID турнира
            knockouts: Список словарей с данными о нокаутах
            session_id: ID сессии загрузки
        """
        # Проверяем подключение к БД
        if not self.db_manager.connection:
            raise ValueError("Не подключена база данных")
            
        # Добавляем каждый нокаут в базу
        for ko in knockouts:
            params = (
                tournament_id,
                ko.get('hand_id'),
                ko.get('knocked_out_player'),
                ko.get('pot_size'),
                ko.get('multi_knockout', False),
                session_id
            )
            
            # Выполняем вставку
            self.db_manager.cursor.execute(INSERT_KNOCKOUT, params)
            
        # Сохраняем изменения
        self.db_manager.connection.commit()
        
    def create_session(self, session_name: str) -> str:
        """
        Создает новую сессию загрузки.
        
        Args:
            session_name: Название сессии
            
        Returns:
            ID созданной сессии
        """
        # Проверяем подключение к БД
        if not self.db_manager.connection:
            raise ValueError("Не подключена база данных")
            
        # Генерируем уникальный ID сессии
        session_id = str(uuid.uuid4())
        
        # Создаем запись о сессии
        params = (
            session_id,
            session_name,
            0,  # tournaments_count
            0,  # knockouts_count
            0.0,  # avg_finish_place
            0.0   # total_prize
        )
        
        # Выполняем вставку
        self.db_manager.cursor.execute(INSERT_SESSION, params)
        self.db_manager.connection.commit()
        
        return session_id
        
    def update_session_stats(self, session_id: str) -> None:
        """
        Обновляет статистику указанной сессии.
        
        Args:
            session_id: ID сессии
        """
        # Проверяем подключение к БД
        if not self.db_manager.connection:
            raise ValueError("Не подключена база данных")
            
        # Получаем количество турниров в сессии
        self.db_manager.cursor.execute(
            "SELECT COUNT(*) FROM tournaments WHERE session_id = ?",
            (session_id,)
        )
        tournaments_count = self.db_manager.cursor.fetchone()[0]
        
        # Получаем количество нокаутов в сессии
        self.db_manager.cursor.execute(
            "SELECT COUNT(*) FROM knockouts WHERE session_id = ?",
            (session_id,)
        )
        knockouts_count = self.db_manager.cursor.fetchone()[0]
        
        # Рассчитываем среднее место
        self.db_manager.cursor.execute(
            "SELECT AVG(finish_place) FROM tournaments WHERE session_id = ? AND finish_place IS NOT NULL",
            (session_id,)
        )
        result = self.db_manager.cursor.fetchone()[0]
        avg_finish_place = result if result is not None else 0.0
        
        # Получаем общий выигрыш
        self.db_manager.cursor.execute(
            "SELECT SUM(prize) FROM tournaments WHERE session_id = ? AND prize IS NOT NULL",
            (session_id,)
        )
        result = self.db_manager.cursor.fetchone()[0]
        total_prize = result if result is not None else 0.0
        
        # Обновляем статистику сессии
        self.db_manager.cursor.execute(
            """
            UPDATE sessions SET
                tournaments_count = ?,
                knockouts_count = ?,
                avg_finish_place = ?,
                total_prize = ?
            WHERE session_id = ?
            """,
            (tournaments_count, knockouts_count, avg_finish_place, total_prize, session_id)
        )
        
        # Сохраняем изменения
        self.db_manager.connection.commit()
        
    def update_overall_statistics(self) -> None:
        """
        Обновляет общую статистику на основе всех данных в базе.
        """
        # Проверяем подключение к БД
        if not self.db_manager.connection:
            raise ValueError("Не подключена база данных")
            
        # Получаем количество турниров
        self.db_manager.cursor.execute("SELECT COUNT(*) FROM tournaments")
        total_tournaments = self.db_manager.cursor.fetchone()[0]
        
        # Получаем общее количество нокаутов
        self.db_manager.cursor.execute("SELECT COUNT(*) FROM knockouts")
        total_knockouts = self.db_manager.cursor.fetchone()[0]
        
        # Получаем количество x2 нокаутов
        self.db_manager.cursor.execute("SELECT SUM(knockouts_x2) FROM tournaments")
        result = self.db_manager.cursor.fetchone()[0]
        total_knockouts_x2 = result if result is not None else 0
        
        # Получаем количество x10 нокаутов
        self.db_manager.cursor.execute("SELECT SUM(knockouts_x10) FROM tournaments")
        result = self.db_manager.cursor.fetchone()[0]
        total_knockouts_x10 = result if result is not None else 0
        
        # Получаем количество x100 нокаутов
        self.db_manager.cursor.execute("SELECT SUM(knockouts_x100) FROM tournaments")
        result = self.db_manager.cursor.fetchone()[0]
        total_knockouts_x100 = result if result is not None else 0
        
        # Получаем количество x1000 нокаутов
        self.db_manager.cursor.execute("SELECT SUM(knockouts_x1000) FROM tournaments")
        result = self.db_manager.cursor.fetchone()[0]
        total_knockouts_x1000 = result if result is not None else 0
        
        # Получаем количество x10000 нокаутов
        self.db_manager.cursor.execute("SELECT SUM(knockouts_x10000) FROM tournaments")
        result = self.db_manager.cursor.fetchone()[0]
        total_knockouts_x10000 = result if result is not None else 0
        
        # Рассчитываем среднее место
        self.db_manager.cursor.execute("SELECT AVG(finish_place) FROM tournaments WHERE finish_place IS NOT NULL")
        result = self.db_manager.cursor.fetchone()[0]
        avg_finish_place = result if result is not None else 0
        
        # Получаем количество первых мест
        self.db_manager.cursor.execute("SELECT COUNT(*) FROM tournaments WHERE finish_place = 1")
        first_places = self.db_manager.cursor.fetchone()[0]
        
        # Получаем количество вторых мест
        self.db_manager.cursor.execute("SELECT COUNT(*) FROM tournaments WHERE finish_place = 2")
        second_places = self.db_manager.cursor.fetchone()[0]
        
        # Получаем количество третьих мест
        self.db_manager.cursor.execute("SELECT COUNT(*) FROM tournaments WHERE finish_place = 3")
        third_places = self.db_manager.cursor.fetchone()[0]
        
        # Получаем общий выигрыш
        self.db_manager.cursor.execute("SELECT SUM(prize) FROM tournaments WHERE prize IS NOT NULL")
        result = self.db_manager.cursor.fetchone()[0]
        total_prize = result if result is not None else 0
        
        # Обновляем общую статистику
        params = (
            total_tournaments,
            total_knockouts,
            total_knockouts_x2,
            total_knockouts_x10,
            total_knockouts_x100,
            total_knockouts_x1000,
            total_knockouts_x10000,
            avg_finish_place,
            first_places,
            second_places,
            third_places,
            total_prize
        )
        
        # Убеждаемся, что запись существует
        self.db_manager.cursor.execute(INSERT_INITIAL_STATISTICS)
        
        # Обновляем статистику
        self.db_manager.cursor.execute(UPDATE_STATISTICS, params)
        self.db_manager.connection.commit()
        
    def get_overall_statistics(self) -> Dict:
        """
        Возвращает общую статистику из базы данных.
        
        Returns:
            Словарь с общей статистикой
        """
        # Проверяем подключение к БД
        if not self.db_manager.connection:
            raise ValueError("Не подключена база данных")
            
        # Получаем статистику
        self.db_manager.cursor.execute(GET_STATISTICS)
        row = self.db_manager.cursor.fetchone()
        
        if not row:
            return {
                'total_tournaments': 0,
                'total_knockouts': 0,
                'total_knockouts_x2': 0,
                'total_knockouts_x10': 0,
                'total_knockouts_x100': 0,
                'total_knockouts_x1000': 0,
                'total_knockouts_x10000': 0,
                'avg_finish_place': 0.0,
                'first_places': 0,
                'second_places': 0,
                'third_places': 0,
                'total_prize': 0.0
            }
            
        # Преобразуем результат в словарь
        return {
            'total_tournaments': row['total_tournaments'],
            'total_knockouts': row['total_knockouts'],
            'total_knockouts_x2': row['total_knockouts_x2'],
            'total_knockouts_x10': row['total_knockouts_x10'],
            'total_knockouts_x100': row['total_knockouts_x100'],
            'total_knockouts_x1000': row['total_knockouts_x1000'],
            'total_knockouts_x10000': row['total_knockouts_x10000'],
            'avg_finish_place': row['avg_finish_place'],
            'first_places': row['first_places'],
            'second_places': row['second_places'],
            'third_places': row['third_places'],
            'total_prize': row['total_prize']
        }
        
    def get_places_distribution(self) -> Dict[int, int]:
        """
        Возвращает распределение мест из базы данных.
        
        Returns:
            Словарь {место: количество_турниров}
        """
        # Проверяем подключение к БД
        if not self.db_manager.connection:
            return {i: 0 for i in range(1, 10)}
            
        # Получаем распределение мест
        self.db_manager.cursor.execute(GET_PLACES_DISTRIBUTION)
        rows = self.db_manager.cursor.fetchall()
        
        # Преобразуем результат в словарь
        distribution = {i: 0 for i in range(1, 10)}
        for row in rows:
            distribution[row['place']] = row['count']
            
        return distribution
        
    def get_sessions(self) -> List[Dict]:
        """
        Возвращает список всех сессий.
        
        Returns:
            Список словарей с информацией о сессиях
        """
        # Проверяем подключение к БД
        if not self.db_manager.connection:
            return []
            
        # Получаем список сессий
        self.db_manager.cursor.execute(GET_SESSIONS)
        rows = self.db_manager.cursor.fetchall()
        
        # Преобразуем результат в список словарей
        sessions = []
        for row in rows:
            sessions.append(dict(row))
            
        return sessions
        
    def get_session_stats(self, session_id: str) -> Optional[Dict]:
        """
        Возвращает статистику указанной сессии.
        
        Args:
            session_id: ID сессии
            
        Returns:
            Словарь со статистикой сессии или None, если сессия не найдена
        """
        # Проверяем подключение к БД
        if not self.db_manager.connection:
            return None
            
        # Получаем информацию о сессии
        self.db_manager.cursor.execute(GET_SESSION_BY_ID, (session_id,))
        row = self.db_manager.cursor.fetchone()
        
        if not row:
            return None
            
        # Преобразуем результат в словарь
        return dict(row)
        
    def get_session_tournaments(self, session_id: str) -> List[Dict]:
        """
        Возвращает список турниров указанной сессии.
        
        Args:
            session_id: ID сессии
            
        Returns:
            Список словарей с информацией о турнирах
        """
        # Проверяем подключение к БД
        if not self.db_manager.connection:
            return []
            
        # Получаем список турниров
        self.db_manager.cursor.execute(GET_TOURNAMENTS_BY_SESSION, (session_id,))
        rows = self.db_manager.cursor.fetchall()
        
        # Преобразуем результат в список словарей
        tournaments = []
        for row in rows:
            tournaments.append(dict(row))
            
        return tournaments
        
    def get_session_knockouts(self, session_id: str) -> List[Dict]:
        """
        Возвращает список нокаутов указанной сессии.
        
        Args:
            session_id: ID сессии
            
        Returns:
            Список словарей с информацией о нокаутах
        """
        # Проверяем подключение к БД
        if not self.db_manager.connection:
            return []
            
        # Получаем список нокаутов
        self.db_manager.cursor.execute(GET_KNOCKOUTS_BY_SESSION, (session_id,))
        rows = self.db_manager.cursor.fetchall()
        
        # Преобразуем результат в список словарей
        knockouts = []
        for row in rows:
            knockouts.append(dict(row))
            
        return knockouts
        
    def delete_session(self, session_id: str) -> None:
        """
        Удаляет указанную сессию и все связанные с ней данные.
        
        Args:
            session_id: ID сессии
        """
        # Проверяем подключение к БД
        if not self.db_manager.connection:
            raise ValueError("Не подключена база данных")
            
        # Удаляем данные сессии
        self.db_manager.cursor.executescript(DELETE_SESSION_DATA.replace('?', f"'{session_id}'"))
        self.db_manager.connection.commit()
        
    def clear_all_data(self) -> None:
        """
        Очищает все данные в базе.
        """
        # Проверяем подключение к БД
        if not self.db_manager.connection:
            raise ValueError("Не подключена база данных")
            
        # Удаляем все данные
        self.db_manager.cursor.executescript(DELETE_ALL_DATA)
        self.db_manager.connection.commit()