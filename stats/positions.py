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
from math import ceil # Импортируем ceil один раз на уровне модуля


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
        Возвращает распределение мест в турнирах, нормализованное к 9-max.
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Словарь {нормализованное_место: количество_турниров}
        """
        if not self.db_manager or not self.db_manager.connection:
            return {i: 0 for i in range(1, 10)}
            
        cursor = self.db_manager.connection.cursor()
        
        # Собираем запрос для выборки finish_place и players_count
        query_parts = ["SELECT finish_place, players_count FROM tournaments"]
        conditions = ["finish_place IS NOT NULL"] # Учитываем только турниры с известным местом
        params: List[Union[str, int]] = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        
        if conditions:
            query_parts.append("WHERE " + " AND ".join(conditions))
        
        final_query = " ".join(query_parts)
        cursor.execute(final_query, tuple(params))
        
        all_tournament_results = cursor.fetchall() # Получаем список sqlite3.Row
        
        normalized_places_counts = {i: 0 for i in range(1, 10)}
        
        for row in all_tournament_results:
            place = row['finish_place']
            # Используем players_count из турнира, по умолчанию 9, если NULL или 0
            players_count = row['players_count'] if row['players_count'] and row['players_count'] > 0 else 9 
            
            if place is None or place < 1: # Пропускаем, если место неизвестно или некорректно
                continue

            # ИСПРАВЛЕНА ФОРМУЛА НОРМАЛИЗАЦИИ МЕСТ - главная ошибка проекта
            # Вместо ceil(place / players_count * 9) используем прямолинейную нормализацию
            if place <= players_count:
                # Расчет нормализованного места по формуле:
                # (place - 1) * 8 / (players_count - 1) + 1 для линейного масштабирования диапазона [1, players_count] в [1, 9]
                # Если place=1, то получается 1 место (первое)
                # Если place=players_count, то получается 9 место (последнее)
                if players_count > 1:  # Защита от деления на ноль
                    normalized_place = round((place - 1) * 8 / (players_count - 1) + 1)
                else:
                    normalized_place = 1  # Если только один игрок, то он на первом месте
                
                # Гарантируем, что место находится в диапазоне [1, 9]
                normalized_place = max(1, min(9, normalized_place))
            else:
                # Если place > players_count (что не должно происходить, но на всякий случай),
                # устанавливаем последнее место (9)
                normalized_place = 9
                
            normalized_places_counts[normalized_place] += 1
            
        return normalized_places_counts
        
    def get_average_position(self, session_id: Optional[str] = None) -> float:
        """
        Возвращает среднее фактическое место в турнирах (не нормализованное).
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Среднее место.
        """
        if not self.db_manager or not self.db_manager.connection:
            return 0.0
            
        cursor = self.db_manager.connection.cursor()
        
        query = "SELECT AVG(finish_place) FROM tournaments WHERE finish_place IS NOT NULL"
        params: List[str] = []
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
            
        cursor.execute(query, tuple(params))
        result = cursor.fetchone()
        return result[0] if result and result[0] is not None else 0.0 # Убедимся, что result[0] не None
        
    def get_normalized_average_position(self, session_id: Optional[str] = None) -> float:
        """
        Возвращает нормализованное среднее место в турнирах (в диапазоне 1-9).
        Использует распределение нормализованных мест.
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Нормализованное среднее место (1.0 - лучшее, 9.0 - худшее)
        """
        distribution = self.get_positions_distribution(session_id) # Это уже нормализованное распределение
        
        total_tournaments = sum(distribution.values())
        if total_tournaments == 0:
            return 0.0
            
        weighted_sum = sum(place * count for place, count in distribution.items())
        
        return weighted_sum / total_tournaments
        
    def get_top_positions_count(self, session_id: Optional[str] = None) -> Dict[str, int]:
        """
        Возвращает количество призовых мест (1-3 по фактическому месту).
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Словарь {место: количество}
        """
        if not self.db_manager or not self.db_manager.connection:
            return {'first': 0, 'second': 0, 'third': 0}
            
        cursor = self.db_manager.connection.cursor()
        
        base_query = """
            SELECT 
                SUM(CASE WHEN finish_place = 1 THEN 1 ELSE 0 END) as first,
                SUM(CASE WHEN finish_place = 2 THEN 1 ELSE 0 END) as second,
                SUM(CASE WHEN finish_place = 3 THEN 1 ELSE 0 END) as third
            FROM tournaments
        """
        params: List[str] = []

        if session_id:
            base_query += " WHERE session_id = ?"
            params.append(session_id)
            
        cursor.execute(base_query, tuple(params))
        result = cursor.fetchone() # sqlite3.Row
        
        if not result:
            return {'first': 0, 'second': 0, 'third': 0}
            
        return {
            'first': result['first'] if result['first'] is not None else 0,
            'second': result['second'] if result['second'] is not None else 0,
            'third': result['third'] if result['third'] is not None else 0
        }
        
    def get_positions_trend(self, 
                           start_date: Optional[str] = None, 
                           end_date: Optional[str] = None) -> Dict[str, List]:
        """
        Возвращает тренд фактических мест в турнирах по датам.
        
        Args:
            start_date: Начальная дата в формате "YYYY-MM-DD" (опционально)
            end_date: Конечная дата в формате "YYYY-MM-DD" (опционально)
            
        Returns:
            Словарь {dates: [...], positions: [...]}
        """
        if not self.db_manager or not self.db_manager.connection:
            return {'dates': [], 'positions': []}
            
        cursor = self.db_manager.connection.cursor()
        
        query_parts = ["SELECT start_time, finish_place FROM tournaments"]
        conditions = ["finish_place IS NOT NULL"]
        params: List[str] = []
        
        if start_date:
            conditions.append("DATE(start_time) >= DATE(?)") # Сравнение дат
            params.append(start_date)
        if end_date:
            conditions.append("DATE(start_time) <= DATE(?)") # Сравнение дат
            params.append(end_date)
                
        if conditions:
            query_parts.append("WHERE " + " AND ".join(conditions))
        
        query_parts.append("ORDER BY start_time")
        final_query = " ".join(query_parts)
        
        cursor.execute(final_query, tuple(params))
        result = cursor.fetchall()
        
        if not result:
            return {'dates': [], 'positions': []}
            
        # Преобразуем даты в строки для простоты, если они datetime объекты
        dates = [row['start_time'] if isinstance(row['start_time'], str) else row['start_time'].isoformat() for row in result]
        positions = [row['finish_place'] for row in result]
        
        return {'dates': dates, 'positions': positions}
        
    def get_prize_by_position(self, session_id: Optional[str] = None) -> Dict[int, float]:
        """
        Возвращает средний выигрыш для каждого фактического места (1-9).
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Словарь {место: средний_выигрыш}
        """
        if not self.db_manager or not self.db_manager.connection:
            return {i: 0.0 for i in range(1, 10)}
            
        cursor = self.db_manager.connection.cursor()
        
        query_parts = [
            "SELECT finish_place, AVG(prize) as avg_prize",
            "FROM tournaments"
        ]
        conditions = [
            "finish_place IS NOT NULL",
            "finish_place >= 1", # Учитываем места от 1
            "finish_place <= 9", # и до 9
            "prize IS NOT NULL"
        ]
        params: List[str] = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        
        if conditions:
            query_parts.append("WHERE " + " AND ".join(conditions))
        
        query_parts.append("GROUP BY finish_place")
        final_query = " ".join(query_parts)
        
        cursor.execute(final_query, tuple(params))
        result = cursor.fetchall()
        
        prize_by_position = {i: 0.0 for i in range(1, 10)}
        for row in result:
            place = row['finish_place']
            avg_prize = row['avg_prize']
            if place is not None and avg_prize is not None: # Доп. проверка
                 prize_by_position[place] = avg_prize
            
        return prize_by_position
        
    def plot_positions_distribution(self, 
                                   session_id: Optional[str] = None, 
                                   save_path: Optional[str] = None):
        """
        Создает гистограмму распределения нормализованных мест.
        """
        distribution = self.get_positions_distribution(session_id) # Уже нормализованное
        
        if not any(distribution.values()): # Проверка, есть ли данные для отображения
            print("Нет данных для построения графика распределения мест.")
            return

        plt.figure(figsize=(10, 6))
        
        places = sorted(distribution.keys()) # Убедимся, что места отсортированы
        counts = [distribution[p] for p in places]
        
        colors = plt.cm.Blues(np.linspace(0.8, 0.4, len(places)))
        bars = plt.bar(places, counts, color=colors)
        
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                plt.text(bar.get_x() + bar.get_width() / 2., height, f'{int(height)}',
                         ha='center', va='bottom')
        
        plt.title('Распределение нормализованных мест (9-max) в турнирах')
        plt.xlabel('Нормализованное место')
        plt.ylabel('Количество турниров')
        plt.xticks(places) # Устанавливаем тики для всех мест от 1 до 9
        plt.grid(True, linestyle='--', alpha=0.3, axis='y')
        
        if save_path:
            plt.savefig(save_path)
            plt.close() # Закрываем фигуру после сохранения
        else:
            plt.show()
            
    def plot_positions_trend(self, 
                            last_n_tournaments: Optional[int] = None,
                            save_path: Optional[str] = None):
        """
        Создает график тренда фактических мест в турнирах.
        """
        if not self.db_manager or not self.db_manager.connection:
            return
            
        cursor = self.db_manager.connection.cursor()
        
        query_parts = ["SELECT start_time, finish_place FROM tournaments"]
        conditions = ["finish_place IS NOT NULL"]
        params: List[Union[str, int]] = []
        
        # Сортировка всегда по start_time
        order_by_clause = "ORDER BY start_time"
        limit_clause = ""

        if last_n_tournaments and last_n_tournaments > 0:
            # Для получения ПОСЛЕДНИХ N турниров, нужно сначала отсортировать по убыванию,
            # взять лимит, а потом перевернуть результат для графика.
            # Или использовать подзапрос, что сложнее с sqlite.
            # Простой вариант: выбрать все, отсортировать, затем взять последние N в Python.
            # Либо, если БД большая, оптимизировать запрос.
            # Пока оставим выборку всех и обработку в Python для last_n_tournaments.
            pass # Будет обработано после выборки


        if conditions:
            query_parts.append("WHERE " + " AND ".join(conditions))
        
        query_parts.append(order_by_clause)
        final_query = " ".join(query_parts)

        cursor.execute(final_query, tuple(params))
        all_results = cursor.fetchall()

        if last_n_tournaments and last_n_tournaments > 0:
            result_for_plot = all_results[-last_n_tournaments:]
        else:
            result_for_plot = all_results
            
        if not result_for_plot:
            print("Нет данных для построения графика тренда мест.")
            return
            
        tournament_numbers = list(range(1, len(result_for_plot) + 1))
        positions = [row['finish_place'] for row in result_for_plot]
        
        plt.figure(figsize=(12, 6))
        plt.plot(tournament_numbers, positions, marker='o', linestyle='-', color='blue')
        plt.gca().invert_yaxis() # 1-е место вверху
        
        plt.title('Тренд фактических мест в турнирах')
        plt.xlabel(f'Номер турнира (последние {len(result_for_plot)})' if last_n_tournaments else 'Номер турнира (хронологически)')
        plt.ylabel('Место (1 - лучшее)')
        plt.grid(True, linestyle='--', alpha=0.7)
        
        plt.axhline(y=1, color='green', linestyle='--', alpha=0.5, label='1-е место')
        plt.axhline(y=3, color='orange', linestyle='--', alpha=0.5, label='Топ-3')
        plt.axhline(y=9, color='red', linestyle='--', alpha=0.5, label='9-е место')
        
        if positions: # Только если есть данные
            avg_position = np.mean(positions)
            plt.axhline(y=avg_position, color='purple', linestyle='-', alpha=0.7, 
                        label=f'Среднее: {avg_position:.2f}')
            # plt.text( # Текст может перекрываться, легенда лучше
            #     (tournament_numbers[-1] * 0.05) if tournament_numbers else 0, 
            #     avg_position, 
            #     f'Среднее место: {avg_position:.2f}', 
            #     color='purple', fontweight='bold'
            # )
        
        plt.ylim(max(positions + [9.5]), min(positions + [0.5])) # Динамический Y-лимит + небольшой отступ
        plt.legend() # Показать легенду для линий

        if save_path:
            plt.savefig(save_path)
            plt.close()
        else:
            plt.show()
            
    def plot_prize_by_position(self, 
                              session_id: Optional[str] = None,
                              save_path: Optional[str] = None):
        """
        Создает график среднего выигрыша для каждого фактического места (1-9).
        """
        prize_by_position = self.get_prize_by_position(session_id)
        
        # Фильтруем только те места, где есть выигрыш и которые мы хотим показать (1-9)
        filtered_prizes = {p: val for p, val in prize_by_position.items() if val > 0 and 1 <= p <= 9}
        
        if not filtered_prizes:
            print("Нет данных о выигрышах по местам для построения графика.")
            return
            
        plt.figure(figsize=(10, 6))
        
        places = sorted(filtered_prizes.keys())
        prizes = [filtered_prizes[p] for p in places]
        
        colors = plt.cm.Greens(np.linspace(0.4, 0.8, len(places)))
        bars = plt.bar(places, prizes, color=colors)
        
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                plt.text(bar.get_x() + bar.get_width() / 2., height, f'${height:.2f}',
                         ha='center', va='bottom')
        
        plt.title('Средний выигрыш по фактическим местам (1-9)')
        plt.xlabel('Место')
        plt.ylabel('Средний выигрыш ($)')
        plt.xticks(range(1,10)) # Показываем все тики от 1 до 9
        plt.grid(True, linestyle='--', alpha=0.3, axis='y')
        
        if save_path:
            plt.savefig(save_path)
            plt.close()
        else:
            plt.show()
            
    def generate_positions_report(self, session_id: Optional[str] = None) -> Dict[str, Union[int, float, Dict, str]]:
        """
        Генерирует полный отчет по позициям.
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Словарь с полной статистикой по позициям
        """
        # Используем нормализованное распределение для отчета
        distribution = self.get_positions_distribution(session_id)
        # Среднее нормализованное место
        avg_norm_position = self.get_normalized_average_position(session_id) 
        # Топ-3 по фактическим местам
        top_positions = self.get_top_positions_count(session_id) 
        # Выигрыш по фактическим местам
        prize_by_position = self.get_prize_by_position(session_id) 
        
        total_tournaments = 0
        if self.db_manager and self.db_manager.connection:
            cursor = self.db_manager.connection.cursor()
            query = "SELECT COUNT(*) FROM tournaments"
            params: List[str] = []
            if session_id:
                query += " WHERE session_id = ?"
                params.append(session_id)
            cursor.execute(query, tuple(params))
            result = cursor.fetchone()
            total_tournaments = result[0] if result else 0
        
        itm_percent = 0.0
        if total_tournaments > 0:
            itm_count = top_positions.get('first',0) + top_positions.get('second',0) + top_positions.get('third',0)
            itm_percent = round((itm_count / total_tournaments) * 100, 2)
        
        return {
            'normalized_distribution_9max': distribution, # Переименовано для ясности
            'average_normalized_position_9max': avg_norm_position, # Переименовано
            'top_3_actual_positions_count': top_positions, # Переименовано
            'average_prize_by_actual_position': prize_by_position, # Переименовано
            'total_tournaments_in_scope': total_tournaments, # Переименовано
            'itm_percent_top3_actual': itm_percent, # Переименовано
            'report_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


# Функции для удобства использования без создания экземпляра класса
# (Оставлены для обратной совместимости, если где-то используются)

def get_positions_distribution(db_manager, session_id=None):
    analyzer = PositionsAnalyzer(db_manager)
    return analyzer.get_positions_distribution(session_id)

def get_average_position(db_manager, session_id=None):
    analyzer = PositionsAnalyzer(db_manager)
    return analyzer.get_average_position(session_id) # Возвращает фактическое среднее

def get_top_positions_count(db_manager, session_id=None):
    analyzer = PositionsAnalyzer(db_manager)
    return analyzer.get_top_positions_count(session_id)