#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для работы с базой данных покерного трекера ROYAL_Stats.
Предоставляет классы и методы для сохранения и получения статистики.
"""

import os
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from db.schema import (
    CREATE_TABLES_QUERIES,
    INSERT_TOURNAMENT,
    INSERT_KNOCKOUT,
    UPDATE_STATISTICS,
    INSERT_INITIAL_STATISTICS,
    UPSERT_PLACE_DISTRIBUTION,
    INSERT_SESSION,
    GET_STATISTICS,
    GET_PLACES_DISTRIBUTION,
    GET_SESSIONS,
    GET_SESSION_BY_ID,
    GET_TOURNAMENTS_BY_SESSION,
    GET_KNOCKOUTS_BY_SESSION,
    GET_TOTAL_KNOCKOUTS,
    GET_TOURNAMENTS_BY_DATE_RANGE,
    DELETE_SESSION_DATA,
    DELETE_ALL_DATA
)


class DatabaseManager:
    """
    Класс для управления соединением с базой данных SQLite.
    """
    
    def __init__(self, db_folder: str = 'databases'):
        """
        Инициализирует менеджер БД.
        
        Args:
            db_folder: Папка для хранения баз данных
        """
        self.db_folder = db_folder
        self.connection = None
        self.cursor = None
        self.current_db_path = None
        
        # Создаем папку для баз данных, если она не существует
        if not os.path.exists(db_folder):
            os.makedirs(db_folder)
            
    def get_available_databases(self) -> List[str]:
        """
        Возвращает список доступных баз данных.
        
        Returns:
            Список имен баз данных
        """
        if not os.path.exists(self.db_folder):
            return []
            
        return [f for f in os.listdir(self.db_folder) 
                if f.endswith('.db') and os.path.isfile(os.path.join(self.db_folder, f))]
        
    def create_database(self, db_name: str) -> str:
        """
        Создает новую базу данных.
        
        Args:
            db_name: Имя новой базы данных (без расширения .db)
            
        Returns:
            Путь к созданной базе данных
        """
        if not db_name.endswith('.db'):
            db_name += '.db'
            
        db_path = os.path.join(self.db_folder, db_name)
        
        # Подключаемся к новой базе данных
        self.connect(db_path)
        
        # Создаем необходимые таблицы
        self._create_tables()
        
        # Вставляем начальную запись статистики
        self.cursor.execute(INSERT_INITIAL_STATISTICS)
        
        # Инициализируем распределение мест
        for place in range(1, 10):
            self.cursor.execute(UPSERT_PLACE_DISTRIBUTION, (place, 0))
            
        self.connection.commit()
        
        return db_path
        
    def connect(self, db_path: str) -> None:
        """
        Подключается к указанной базе данных.
        
        Args:
            db_path: Путь к файлу базы данных
        """
        # Закрываем текущее соединение, если оно открыто
        if self.connection:
            self.connection.close()
            
        # Создаем новое соединение
        self.connection = sqlite3.connect(db_path)
        self.connection.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
        self.cursor = self.connection.cursor()
        self.current_db_path = db_path
        
    def _create_tables(self) -> None:
        """
        Создает необходимые таблицы в базе данных.
        """
        for query in CREATE_TABLES_QUERIES:
            self.cursor.execute(query)
        self.connection.commit()
            
    def close(self) -> None:
        """
        Закрывает соединение с базой данных.
        """
        if self.connection:
            self.connection.close()
            self.connection = None
            self.cursor = None
            self.current_db_path = None


class StatsDatabase:
    """
    Класс для работы с базой данных статистики.
    Предоставляет методы для сохранения и получения данных.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Инициализирует объект для работы с базой данных.
        
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
            tournament_data.get('players_count'),
            tournament_data.get('prize_pool'),
            tournament_data.get('start_time'),
            tournament_data.get('finish_place'),
            tournament_data.get('prize'),
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
        Сохраняет данные о накаутах в базу.
        
        Args:
            tournament_id: ID турнира
            knockouts: Список словарей с данными о накаутах
            session_id: ID сессии загрузки
        """
        # Проверяем подключение к БД
        if not self.db_manager.connection:
            raise ValueError("Не подключена база данных")
            
        # Вставляем каждый накаут
        for knockout in knockouts:
            params = (
                tournament_id,
                knockout.get('hand_id'),
                knockout.get('knocked_out_player'),
                knockout.get('pot_size'),
                knockout.get('multi_knockout', False),
                session_id
            )
            
            self.db_manager.cursor.execute(INSERT_KNOCKOUT, params)
            
        self.db_manager.connection.commit()
    
    def create_session(self, session_name: str = None) -> str:
        """
        Создает новую сессию загрузки данных.
        
        Args:
            session_name: Название сессии
            
        Returns:
            ID созданной сессии
        """
        session_id = str(uuid.uuid4())
        
        if session_name is None:
            session_name = f"Сессия {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
        # Вставляем информацию о сессии
        params = (
            session_id,
            session_name,
            0,  # tournaments_count
            0,  # knockouts_count
            0,  # avg_finish_place
            0   # total_prize
        )
        
        self.db_manager.cursor.execute(INSERT_SESSION, params)
        self.db_manager.connection.commit()
        
        return session_id
    
    def update_session_stats(self, session_id: str) -> None:
        """
        Обновляет статистику сессии.
        
        Args:
            session_id: ID сессии
        """
        # Получаем данные о турнирах сессии
        self.db_manager.cursor.execute(GET_TOURNAMENTS_BY_SESSION, (session_id,))
        tournaments = self.db_manager.cursor.fetchall()
        
        # Получаем данные о накаутах сессии
        self.db_manager.cursor.execute(GET_KNOCKOUTS_BY_SESSION, (session_id,))
        knockouts = self.db_manager.cursor.fetchall()
        
        # Рассчитываем статистику
        tournaments_count = len(tournaments)
        knockouts_count = len(knockouts)
        
        # Рассчитываем среднее место
        places = [t['finish_place'] for t in tournaments if t['finish_place']]
        avg_place = sum(places) / len(places) if places else 0
        
        # Рассчитываем общий выигрыш
        total_prize = sum(t['prize'] for t in tournaments if t['prize'])
        
        # Обновляем статистику сессии
        params = (
            session_id,
            tournaments_count,
            knockouts_count,
            avg_place,
            total_prize
        )
        
        query = """
        UPDATE sessions SET
            tournaments_count = ?,
            knockouts_count = ?,
            avg_finish_place = ?,
            total_prize = ?
        WHERE session_id = ?
        """
        
        self.db_manager.cursor.execute(query, (
            tournaments_count,
            knockouts_count,
            avg_place,
            total_prize,
            session_id
        ))
        
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
        
        # Получаем общее количество накаутов
        self.db_manager.cursor.execute("SELECT COUNT(*) FROM knockouts")
        total_knockouts = self.db_manager.cursor.fetchone()[0]
        
        # Получаем количество x10 накаутов
        self.db_manager.cursor.execute("SELECT SUM(knockouts_x10) FROM tournaments")
        result = self.db_manager.cursor.fetchone()[0]
        total_knockouts_x10 = result if result is not None else 0
        
        # Получаем количество x100 накаутов
        self.db_manager.cursor.execute("SELECT SUM(knockouts_x100) FROM tournaments")
        result = self.db_manager.cursor.fetchone()[0]
        total_knockouts_x100 = result if result is not None else 0
        
        # Получаем количество x1000 накаутов
        self.db_manager.cursor.execute("SELECT SUM(knockouts_x1000) FROM tournaments")
        result = self.db_manager.cursor.fetchone()[0]
        total_knockouts_x1000 = result if result is not None else 0
        
        # Получаем количество x10000 накаутов
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
        Возвращает общую статистику.
        
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
            # Если нет данных, возвращаем пустую статистику
            return {
                'total_tournaments': 0,
                'total_knockouts': 0,
                'total_knockouts_x10': 0,
                'total_knockouts_x100': 0,
                'total_knockouts_x1000': 0,
                'total_knockouts_x10000': 0,
                'avg_finish_place': 0,
                'first_places': 0,
                'second_places': 0,
                'third_places': 0,
                'total_prize': 0,
                'last_updated': None
            }
            
        # Преобразуем Row в словарь
        return dict(row)
    
    def get_places_distribution(self) -> Dict[int, int]:
        """
        Возвращает распределение мест.
        
        Returns:
            Словарь {место: количество}
        """
        # Проверяем подключение к БД
        if not self.db_manager.connection:
            raise ValueError("Не подключена база данных")
            
        # Получаем распределение
        self.db_manager.cursor.execute(GET_PLACES_DISTRIBUTION)
        rows = self.db_manager.cursor.fetchall()
        
        # Преобразуем результат в словарь
        distribution = {i: 0 for i in range(1, 10)}
        for row in rows:
            distribution[row['place']] = row['count']
            
        return distribution
    
    def get_sessions(self) -> List[Dict]:
        """
        Возвращает список сессий загрузки.
        
        Returns:
            Список словарей с информацией о сессиях
        """
        # Проверяем подключение к БД
        if not self.db_manager.connection:
            raise ValueError("Не подключена база данных")
            
        # Получаем список сессий
        self.db_manager.cursor.execute(GET_SESSIONS)
        rows = self.db_manager.cursor.fetchall()
        
        # Преобразуем результат в список словарей
        return [dict(row) for row in rows]
    
    def get_session_stats(self, session_id: str) -> Dict:
        """
        Возвращает статистику конкретной сессии.
        
        Args:
            session_id: ID сессии
            
        Returns:
            Словарь со статистикой сессии
        """
        # Проверяем подключение к БД
        if not self.db_manager.connection:
            raise ValueError("Не подключена база данных")
            
        # Получаем информацию о сессии
        self.db_manager.cursor.execute(GET_SESSION_BY_ID, (session_id,))
        row = self.db_manager.cursor.fetchone()
        
        if not row:
            return None
            
        # Преобразуем в словарь
        return dict(row)
    
    def get_session_tournaments(self, session_id: str) -> List[Dict]:
        """
        Возвращает список турниров конкретной сессии.
        
        Args:
            session_id: ID сессии
            
        Returns:
            Список словарей с информацией о турнирах
        """
        # Проверяем подключение к БД
        if not self.db_manager.connection:
            raise ValueError("Не подключена база данных")
            
        # Получаем список турниров
        self.db_manager.cursor.execute(GET_TOURNAMENTS_BY_SESSION, (session_id,))
        rows = self.db_manager.cursor.fetchall()
        
        # Преобразуем результат в список словарей
        return [dict(row) for row in rows]
    
    def get_session_knockouts(self, session_id: str) -> List[Dict]:
        """
        Возвращает список накаутов конкретной сессии.
        
        Args:
            session_id: ID сессии
            
        Returns:
            Список словарей с информацией о накаутах
        """
        # Проверяем подключение к БД
        if not self.db_manager.connection:
            raise ValueError("Не подключена база данных")
            
        # Получаем список накаутов
        self.db_manager.cursor.execute(GET_KNOCKOUTS_BY_SESSION, (session_id,))
        rows = self.db_manager.cursor.fetchall()
        
        # Преобразуем результат в список словарей
        return [dict(row) for row in rows]
    
    def delete_session(self, session_id: str) -> None:
        """
        Удаляет данные сессии из базы.
        
        Args:
            session_id: ID сессии
        """
        # Проверяем подключение к БД
        if not self.db_manager.connection:
            raise ValueError("Не подключена база данных")
            
        # Удаляем турниры сессии
        self.db_manager.cursor.execute("DELETE FROM tournaments WHERE session_id = ?", (session_id,))
        
        # Удаляем накауты сессии
        self.db_manager.cursor.execute("DELETE FROM knockouts WHERE session_id = ?", (session_id,))
        
        # Удаляем информацию о сессии
        self.db_manager.cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        
        self.db_manager.connection.commit()
        
        # Обновляем общую статистику
        self.update_overall_statistics()
    
    def clear_all_data(self) -> None:
        """
        Очищает все данные в базе.
        """
        # Проверяем подключение к БД
        if not self.db_manager.connection:
            raise ValueError("Не подключена база данных")
            
        # Выполняем скрипт удаления всех данных
        for statement in DELETE_ALL_DATA.split(';'):
            if statement.strip():
                self.db_manager.cursor.execute(statement)
                
        # Инициализируем распределение мест
        for place in range(1, 10):
            self.db_manager.cursor.execute(UPSERT_PLACE_DISTRIBUTION, (place, 0))
                
        self.db_manager.connection.commit()


# Пример использования
if __name__ == "__main__":
    # Инициализируем менеджер БД
    db_manager = DatabaseManager(db_folder='databases')
    
    # Создаем или подключаемся к базе данных
    db_path = os.path.join(db_manager.db_folder, 'test.db')
    if not os.path.exists(db_path):
        db_path = db_manager.create_database('test.db')
    else:
        db_manager.connect(db_path)
        
    # Инициализируем объект для работы с БД
    stats_db = StatsDatabase(db_manager)
    
    # Создаем сессию
    session_id = stats_db.create_session("Тестовая сессия")
    
    # Добавляем тестовые данные
    test_tournament = {
        'tournament_id': '123456',
        'tournament_name': 'Test Tournament',
        'game_type': 'Hold\'em No Limit',
        'buy_in': 10.0,
        'fee': 1.0,
        'bounty': 10.0,
        'total_buy_in': 21.0,
        'players_count': 9,
        'prize_pool': 189.0,
        'start_time': '2025/05/01 17:00:00',
        'finish_place': 1,
        'prize': 150.0,
        'knockouts_x10': 1,
        'knockouts_x100': 0,
        'knockouts_x1000': 0,
        'knockouts_x10000': 0
    }
    
    # Сохраняем турнир
    stats_db.save_tournament_data(test_tournament, session_id)
    
    # Добавляем тестовые накауты
    test_knockouts = [
        {
            'hand_id': 'hand-1',
            'knocked_out_player': 'Player1',
            'pot_size': 1000,
            'multi_knockout': False
        },
        {
            'hand_id': 'hand-2',
            'knocked_out_player': 'Player2',
            'pot_size': 2000,
            'multi_knockout': True
        }
    ]
    
    # Сохраняем накауты
    stats_db.save_knockouts_data(test_tournament['tournament_id'], test_knockouts, session_id)
    
    # Обновляем статистику сессии
    stats_db.update_session_stats(session_id)
    
    # Обновляем общую статистику
    stats_db.update_overall_statistics()
    
    # Получаем общую статистику
    overall_stats = stats_db.get_overall_statistics()
    print("Общая статистика:")
    print(f"Всего турниров: {overall_stats['total_tournaments']}")
    print(f"Всего накаутов: {overall_stats['total_knockouts']}")
    print(f"Среднее место: {overall_stats['avg_finish_place']:.2f}")
    
    # Закрываем соединение
    db_manager.close()