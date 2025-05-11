#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для анализа позиций (мест) в покерных турнирах.
Предоставляет функции для анализа и визуализации распределения мест,
расчета среднего места и других статистических метрик.
"""

from typing import Dict, List, Optional, Union, Tuple
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime


class PositionsAnalyzer:
    """
    Класс для анализа и визуализации позиций (мест) в покерных турнирах.
    """
    
    def __init__(self, db_manager=None):
        """
        Инициализирует анализатор позиций.
        
        Args:
            db_manager: Экземпляр менеджера базы данных (опционально)
        """
        self.db_manager = db_manager
        
    def get_positions_distribution(self, session_id: Optional[str] = None) -> Dict[int, int]:
        """
        Возвращает распределение мест в турнирах.
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Словарь {место: количество_турниров}
        """
        if not self.db_manager or not self.db_manager.connection:
            return {i: 0 for i in range(1, 10)}
            
        cursor = self.db_manager.connection.cursor()
        
        if session_id:
            # Для заданной сессии сначала получаем все места
            cursor.execute(
                "SELECT finish_place FROM tournaments WHERE session_id = ? AND finish_place IS NOT NULL",
                (session_id,)
            )
        else:
            # Для всех турниров получаем все места
            cursor.execute(
                "SELECT finish_place FROM tournaments WHERE finish_place IS NOT NULL"
            )
            
        # Получаем все места
        all_places = [row[0] for row in cursor.fetchall()]
        
        # Нормализуем места в диапазон 1-9
        normalized_places = []
        for place in all_places:
            # Получаем количество игроков для этого турнира
            cursor.execute(
                "SELECT players_count FROM tournaments WHERE finish_place = ?",
                (place,)
            )
            result = cursor.fetchone()
            players_count = result[0] if result else 9  # По умолчанию 9 игроков
            
            # Нормализуем место
            from math import ceil
            normalized_place = min(max(ceil(place / players_count * 9), 1), 9)
            normalized_places.append(normalized_place)
            
        # Создаем распределение мест
        distribution = {i: 0 for i in range(1, 10)}
        for place in normalized_places:
            distribution[place] += 1
            
        return distribution
        
    def get_average_position(self, session_id: Optional[str] = None) -> float:
        """
        Возвращает среднее место в турнирах.
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Среднее место (1.0 - лучшее, 9.0 - худшее)
        """
        if not self.db_manager or not self.db_manager.connection:
            return 0.0
            
        cursor = self.db_manager.connection.cursor()
        
        if session_id:
            cursor.execute(
                "SELECT AVG(finish_place) FROM tournaments WHERE session_id = ? AND finish_place IS NOT NULL",
                (session_id,)
            )
        else:
            cursor.execute(
                "SELECT AVG(finish_place) FROM tournaments WHERE finish_place IS NOT NULL"
            )
            
        result = cursor.fetchone()
        return result[0] if result and result[0] else 0.0
        
    def get_normalized_average_position(self, session_id: Optional[str] = None) -> float:
        """
        Возвращает нормализованное среднее место в турнирах (в диапазоне 1-9).
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Нормализованное среднее место (1.0 - лучшее, 9.0 - худшее)
        """
        distribution = self.get_positions_distribution(session_id)
        
        # Считаем общее количество турниров и взвешенную сумму мест
        total_tournaments = sum(distribution.values())
        weighted_sum = sum(place * count for place, count in distribution.items())
        
        # Возвращаем среднее место
        return weighted_sum / total_tournaments if total_tournaments > 0 else 0.0
        
    def get_top_positions_count(self, session_id: Optional[str] = None) -> Dict[str, int]:
        """
        Возвращает количество призовых мест (1-3).
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Словарь {место: количество}
        """
        if not self.db_manager or not self.db_manager.connection:
            return {'first': 0, 'second': 0, 'third': 0}
            
        cursor = self.db_manager.connection.cursor()
        
        if session_id:
            cursor.execute(
                """
                SELECT 
                    SUM(CASE WHEN finish_place = 1 THEN 1 ELSE 0 END) as first,
                    SUM(CASE WHEN finish_place = 2 THEN 1 ELSE 0 END) as second,
                    SUM(CASE WHEN finish_place = 3 THEN 1 ELSE 0 END) as third
                FROM tournaments 
                WHERE session_id = ?
                """,
                (session_id,)
            )
        else:
            cursor.execute(
                """
                SELECT 
                    SUM(CASE WHEN finish_place = 1 THEN 1 ELSE 0 END) as first,
                    SUM(CASE WHEN finish_place = 2 THEN 1 ELSE 0 END) as second,
                    SUM(CASE WHEN finish_place = 3 THEN 1 ELSE 0 END) as third
                FROM tournaments
                """
            )
            
        result = cursor.fetchone()
        
        if not result:
            return {'first': 0, 'second': 0, 'third': 0}
            
        return {
            'first': result[0] or 0,
            'second': result[1] or 0,
            'third': result[2] or 0
        }
        
    def get_positions_trend(self, 
                           start_date: Optional[str] = None, 
                           end_date: Optional[str] = None) -> Dict[str, List]:
        """
        Возвращает тренд мест в турнирах по датам.
        
        Args:
            start_date: Начальная дата в формате "YYYY-MM-DD" (опционально)
            end_date: Конечная дата в формате "YYYY-MM-DD" (опционально)
            
        Returns:
            Словарь {dates: [...], positions: [...]}
        """
        if not self.db_manager or not self.db_manager.connection:
            return {'dates': [], 'positions': []}
            
        cursor = self.db_manager.connection.cursor()
        
        query = """
        SELECT 
            start_time, 
            finish_place 
        FROM 
            tournaments 
        WHERE 
            finish_place IS NOT NULL
        """
        
        params = []
        if start_date or end_date:
            if start_date:
                query += " AND start_time >= ?"
                params.append(start_date)
                
            if end_date:
                query += " AND start_time <= ?"
                params.append(end_date)
                
        query += " ORDER BY start_time"
        
        cursor.execute(query, params)
        result = cursor.fetchall()
        
        if not result:
            return {'dates': [], 'positions': []}
            
        dates = [row[0] for row in result]
        positions = [row[1] for row in result]
        
        return {
            'dates': dates,
            'positions': positions
        }
        
    def get_prize_by_position(self, session_id: Optional[str] = None) -> Dict[int, float]:
        """
        Возвращает средний выигрыш для каждого места.
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Словарь {место: средний_выигрыш}
        """
        if not self.db_manager or not self.db_manager.connection:
            return {i: 0.0 for i in range(1, 10)}
            
        cursor = self.db_manager.connection.cursor()
        
        if session_id:
            cursor.execute(
                """
                SELECT 
                    finish_place, 
                    AVG(prize) 
                FROM 
                    tournaments 
                WHERE 
                    session_id = ? AND 
                    finish_place IS NOT NULL AND 
                    finish_place <= 9 AND
                    prize IS NOT NULL
                GROUP BY 
                    finish_place
                """,
                (session_id,)
            )
        else:
            cursor.execute(
                """
                SELECT 
                    finish_place, 
                    AVG(prize) 
                FROM 
                    tournaments 
                WHERE 
                    finish_place IS NOT NULL AND 
                    finish_place <= 9 AND
                    prize IS NOT NULL
                GROUP BY 
                    finish_place
                """
            )
            
        result = cursor.fetchall()
        
        prize_by_position = {i: 0.0 for i in range(1, 10)}
        for row in result:
            prize_by_position[row[0]] = row[1]
            
        return prize_by_position
        
    def plot_positions_distribution(self, 
                                   session_id: Optional[str] = None, 
                                   save_path: Optional[str] = None):
        """
        Создает гистограмму распределения мест.
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            save_path: Путь для сохранения графика (опционально)
        """
        distribution = self.get_positions_distribution(session_id)
        
        plt.figure(figsize=(10, 6))
        
        places = list(distribution.keys())
        counts = list(distribution.values())
        
        # Создаем цветовую гамму от темного к светлому
        # Первое место - самый темный (лучший)
        colors = plt.cm.Blues(np.linspace(0.8, 0.4, len(places)))
        
        bars = plt.bar(places, counts, color=colors)
        
        # Добавляем подписи к столбцам
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                plt.text(
                    bar.get_x() + bar.get_width() / 2.,
                    height,
                    f'{int(height)}',
                    ha='center', va='bottom'
                )
        
        plt.title('Распределение мест в турнирах')
        plt.xlabel('Место')
        plt.ylabel('Количество турниров')
        plt.xticks(places)
        plt.grid(True, linestyle='--', alpha=0.3, axis='y')
        
        if save_path:
            plt.savefig(save_path)
        else:
            plt.show()
            
    def plot_positions_trend(self, 
                            last_n_tournaments: Optional[int] = None,
                            save_path: Optional[str] = None):
        """
        Создает график тренда мест в турнирах.
        
        Args:
            last_n_tournaments: Количество последних турниров для отображения (опционально)
            save_path: Путь для сохранения графика (опционально)
        """
        if not self.db_manager or not self.db_manager.connection:
            return
            
        cursor = self.db_manager.connection.cursor()
        
        query = """
        SELECT 
            start_time, 
            finish_place 
        FROM 
            tournaments 
        WHERE 
            finish_place IS NOT NULL
        ORDER BY 
            start_time
        """
        
        if last_n_tournaments:
            query = """
            SELECT 
                start_time, 
                finish_place 
            FROM 
                tournaments 
            WHERE 
                finish_place IS NOT NULL
            ORDER BY 
                start_time DESC
            LIMIT ?
            """
            cursor.execute(query, (last_n_tournaments,))
            result = cursor.fetchall()
            result.reverse()  # Переворачиваем, чтобы сохранить хронологический порядок
        else:
            cursor.execute(query)
            result = cursor.fetchall()
            
        if not result:
            return
            
        tournament_numbers = list(range(1, len(result) + 1))
        positions = [row[1] for row in result]
        
        plt.figure(figsize=(12, 6))
        
        # Инвертируем ось Y, чтобы 1-е место было вверху (лучше)
        plt.plot(tournament_numbers, positions, marker='o', linestyle='-', color='blue')
        plt.gca().invert_yaxis()
        
        plt.title('Тренд мест в турнирах')
        plt.xlabel('Номер турнира')
        plt.ylabel('Место (1 - лучшее)')
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Добавляем горизонтальные линии для визуального ориентира
        plt.axhline(y=1, color='green', linestyle='--', alpha=0.5)  # 1-е место
        plt.axhline(y=3, color='orange', linestyle='--', alpha=0.5)  # 3-е место
        plt.axhline(y=9, color='red', linestyle='--', alpha=0.5)    # 9-е место
        
        # Добавляем линию среднего места
        avg_position = np.mean(positions)
        plt.axhline(y=avg_position, color='purple', linestyle='-', alpha=0.7)
        plt.text(
            tournament_numbers[-1] * 0.05, 
            avg_position, 
            f'Среднее место: {avg_position:.2f}', 
            color='purple', fontweight='bold'
        )
        
        # Ограничиваем ось Y диапазоном мест 1-9
        plt.ylim(9.5, 0.5)
        
        if save_path:
            plt.savefig(save_path)
        else:
            plt.show()
            
    def plot_prize_by_position(self, 
                              session_id: Optional[str] = None,
                              save_path: Optional[str] = None):
        """
        Создает график среднего выигрыша для каждого места.
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            save_path: Путь для сохранения графика (опционально)
        """
        prize_by_position = self.get_prize_by_position(session_id)
        
        # Удаляем места с нулевым выигрышем
        prize_by_position = {k: v for k, v in prize_by_position.items() if v > 0}
        
        if not prize_by_position:
            return
            
        plt.figure(figsize=(10, 6))
        
        places = list(prize_by_position.keys())
        prizes = list(prize_by_position.values())
        
        # Создаем цветовую гамму
        colors = plt.cm.Greens(np.linspace(0.4, 0.8, len(places)))
        
        bars = plt.bar(places, prizes, color=colors)
        
        # Добавляем подписи к столбцам
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                plt.text(
                    bar.get_x() + bar.get_width() / 2.,
                    height,
                    f'${height:.2f}',
                    ha='center', va='bottom'
                )
        
        plt.title('Средний выигрыш по местам')
        plt.xlabel('Место')
        plt.ylabel('Средний выигрыш ($)')
        plt.xticks(places)
        plt.grid(True, linestyle='--', alpha=0.3, axis='y')
        
        if save_path:
            plt.savefig(save_path)
        else:
            plt.show()
            
    def generate_positions_report(self, session_id: Optional[str] = None) -> Dict[str, Union[int, float, Dict]]:
        """
        Генерирует полный отчет по позициям.
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Словарь с полной статистикой по позициям
        """
        distribution = self.get_positions_distribution(session_id)
        avg_position = self.get_normalized_average_position(session_id)
        top_positions = self.get_top_positions_count(session_id)
        prize_by_position = self.get_prize_by_position(session_id)
        
        # Получаем общее количество турниров
        cursor = self.db_manager.connection.cursor()
        if session_id:
            cursor.execute(
                "SELECT COUNT(*) FROM tournaments WHERE session_id = ?", 
                (session_id,)
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM tournaments")
            
        result = cursor.fetchone()
        total_tournaments = result[0] if result else 0
        
        # Рассчитываем ITM (In The Money) - процент попадания в призы (топ-3)
        itm_percent = 0.0
        if total_tournaments > 0:
            itm_count = sum(top_positions.values())
            itm_percent = round((itm_count / total_tournaments) * 100, 2)
        
        return {
            'distribution': distribution,
            'average_position': avg_position,
            'top_positions': top_positions,
            'prize_by_position': prize_by_position,
            'total_tournaments': total_tournaments,
            'itm_percent': itm_percent,
            'report_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


# Функции для удобства использования без создания экземпляра класса

def get_positions_distribution(db_manager, session_id=None):
    """
    Возвращает распределение мест в турнирах.
    
    Args:
        db_manager: Экземпляр менеджера базы данных
        session_id: ID сессии для фильтрации (опционально)
        
    Returns:
        Словарь {место: количество_турниров}
    """
    analyzer = PositionsAnalyzer(db_manager)
    return analyzer.get_positions_distribution(session_id)

def get_average_position(db_manager, session_id=None):
    """
    Возвращает среднее место в турнирах.
    
    Args:
        db_manager: Экземпляр менеджера базы данных
        session_id: ID сессии для фильтрации (опционально)
        
    Returns:
        Среднее место (1.0 - лучшее, 9.0 - худшее)
    """
    analyzer = PositionsAnalyzer(db_manager)
    return analyzer.get_average_position(session_id)

def get_top_positions_count(db_manager, session_id=None):
    """
    Возвращает количество призовых мест (1-3).
    
    Args:
        db_manager: Экземпляр менеджера базы данных
        session_id: ID сессии для фильтрации (опционально)
        
    Returns:
        Словарь {место: количество}
    """
    analyzer = PositionsAnalyzer(db_manager)
    return analyzer.get_top_positions_count(session_id)