#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для анализа нокаутов в покерных турнирах.
Предоставляет функции для анализа обычных и крупных (x10, x100, x1000, x10000) нокаутов.
"""

from typing import Dict, List, Optional, Union, Tuple
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime


class KnockoutsAnalyzer:
    """
    Класс для анализа и визуализации статистики нокаутов в покерных турнирах.
    """
    
    def __init__(self, db_manager=None):
        """
        Инициализирует анализатор нокаутов.
        
        Args:
            db_manager: Экземпляр менеджера базы данных (опционально)
        """
        self.db_manager = db_manager
    
    def get_total_knockouts(self, session_id: Optional[str] = None) -> int:
        """
        Возвращает общее количество нокаутов, сделанных игроком.
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Общее количество нокаутов
        """
        if not self.db_manager or not self.db_manager.connection:
            return 0
            
        cursor = self.db_manager.connection.cursor()
        
        if session_id:
            cursor.execute(
                "SELECT COUNT(*) FROM knockouts WHERE session_id = ?",
                (session_id,)
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM knockouts")
            
        result = cursor.fetchone()
        return result[0] if result else 0
    
    def get_large_knockouts_stats(self, session_id: Optional[str] = None) -> Dict[str, int]:
        """
        Возвращает статистику по крупным нокаутам (x10, x100, x1000, x10000).
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Словарь со статистикой крупных нокаутов
        """
        if not self.db_manager or not self.db_manager.connection:
            return {
                'x10': 0,
                'x100': 0,
                'x1000': 0,
                'x10000': 0
            }
            
        cursor = self.db_manager.connection.cursor()
        
        if session_id:
            cursor.execute(
                """
                SELECT 
                    SUM(knockouts_x10) as x10,
                    SUM(knockouts_x100) as x100,
                    SUM(knockouts_x1000) as x1000,
                    SUM(knockouts_x10000) as x10000
                FROM tournaments 
                WHERE session_id = ?
                """,
                (session_id,)
            )
        else:
            cursor.execute(
                """
                SELECT 
                    SUM(knockouts_x10) as x10,
                    SUM(knockouts_x100) as x100,
                    SUM(knockouts_x1000) as x1000,
                    SUM(knockouts_x10000) as x10000
                FROM tournaments
                """
            )
            
        result = cursor.fetchone()
        
        if not result:
            return {
                'x10': 0,
                'x100': 0,
                'x1000': 0,
                'x10000': 0
            }
            
        return {
            'x10': result[0] or 0,
            'x100': result[1] or 0,
            'x1000': result[2] or 0,
            'x10000': result[3] or 0
        }
    
    def get_knockouts_by_tournament(self, session_id: Optional[str] = None) -> Dict[str, int]:
        """
        Возвращает количество нокаутов, сгруппированных по турнирам.
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Словарь {tournament_id: количество_нокаутов}
        """
        if not self.db_manager or not self.db_manager.connection:
            return {}
            
        cursor = self.db_manager.connection.cursor()
        
        if session_id:
            cursor.execute(
                """
                SELECT tournament_id, COUNT(*) 
                FROM knockouts 
                WHERE session_id = ?
                GROUP BY tournament_id
                """,
                (session_id,)
            )
        else:
            cursor.execute(
                """
                SELECT tournament_id, COUNT(*) 
                FROM knockouts 
                GROUP BY tournament_id
                """
            )
            
        result = cursor.fetchall()
        
        return {str(row[0]): row[1] for row in result}
    
    def get_knockouts_by_date(self, 
                             start_date: Optional[str] = None, 
                             end_date: Optional[str] = None) -> Dict[str, int]:
        """
        Возвращает количество нокаутов, сгруппированных по датам.
        
        Args:
            start_date: Начальная дата в формате "YYYY-MM-DD" (опционально)
            end_date: Конечная дата в формате "YYYY-MM-DD" (опционально)
            
        Returns:
            Словарь {дата: количество_нокаутов}
        """
        if not self.db_manager or not self.db_manager.connection:
            return {}
            
        cursor = self.db_manager.connection.cursor()
        
        query = """
        SELECT 
            t.start_time, 
            COUNT(k.id) 
        FROM 
            knockouts k
        JOIN 
            tournaments t ON k.tournament_id = t.tournament_id
        """
        
        params = []
        if start_date or end_date:
            query += " WHERE "
            
            if start_date:
                query += "t.start_time >= ?"
                params.append(start_date)
                
                if end_date:
                    query += " AND t.start_time <= ?"
                    params.append(end_date)
            elif end_date:
                query += "t.start_time <= ?"
                params.append(end_date)
                
        query += " GROUP BY strftime('%Y-%m-%d', t.start_time)"
        
        cursor.execute(query, params)
        result = cursor.fetchall()
        
        return {row[0].split(' ')[0]: row[1] for row in result}
    
    def get_multi_knockout_stats(self, session_id: Optional[str] = None) -> Dict[str, int]:
        """
        Возвращает статистику по обычным нокаутам и мульти-нокаутам.
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Словарь со статистикой {обычные: N, мульти: M}
        """
        if not self.db_manager or not self.db_manager.connection:
            return {'single': 0, 'multi': 0}
            
        cursor = self.db_manager.connection.cursor()
        
        if session_id:
            cursor.execute(
                """
                SELECT 
                    SUM(CASE WHEN multi_knockout = 0 THEN 1 ELSE 0 END) as single,
                    SUM(CASE WHEN multi_knockout = 1 THEN 1 ELSE 0 END) as multi
                FROM knockouts 
                WHERE session_id = ?
                """,
                (session_id,)
            )
        else:
            cursor.execute(
                """
                SELECT 
                    SUM(CASE WHEN multi_knockout = 0 THEN 1 ELSE 0 END) as single,
                    SUM(CASE WHEN multi_knockout = 1 THEN 1 ELSE 0 END) as multi
                FROM knockouts
                """
            )
            
        result = cursor.fetchone()
        
        if not result:
            return {'single': 0, 'multi': 0}
            
        return {
            'single': result[0] or 0,
            'multi': result[1] or 0
        }
    
    def plot_knockouts_trend(self, 
                            save_path: Optional[str] = None, 
                            last_n_days: Optional[int] = None):
        """
        Создает график тренда нокаутов по датам.
        
        Args:
            save_path: Путь для сохранения графика (опционально)
            last_n_days: Количество последних дней для отображения (опционально)
        """
        if not self.db_manager or not self.db_manager.connection:
            return
            
        cursor = self.db_manager.connection.cursor()
        
        query = """
        SELECT 
            strftime('%Y-%m-%d', t.start_time) as date, 
            COUNT(k.id) as ko_count
        FROM 
            knockouts k
        JOIN 
            tournaments t ON k.tournament_id = t.tournament_id
        """
        
        if last_n_days:
            query += f" WHERE t.start_time >= date('now', '-{last_n_days} days')"
            
        query += " GROUP BY date ORDER BY date"
        
        cursor.execute(query)
        result = cursor.fetchall()
        
        if not result:
            return
            
        dates = [row[0] for row in result]
        ko_counts = [row[1] for row in result]
        
        plt.figure(figsize=(12, 6))
        plt.plot(dates, ko_counts, marker='o', linestyle='-', color='blue')
        plt.title('Тренд нокаутов по датам')
        plt.xlabel('Дата')
        plt.ylabel('Количество нокаутов')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
        else:
            plt.show()
            
    def plot_large_knockouts_distribution(self, save_path: Optional[str] = None):
        """
        Создает график распределения крупных нокаутов.
        
        Args:
            save_path: Путь для сохранения графика (опционально)
        """
        stats = self.get_large_knockouts_stats()
        
        labels = ['x10', 'x100', 'x1000', 'x10000']
        values = [stats['x10'], stats['x100'], stats['x1000'], stats['x10000']]
        
        plt.figure(figsize=(10, 6))
        
        # Создаем цветовую гамму от светлого к темному
        colors = plt.cm.Blues(np.linspace(0.4, 0.8, len(values)))
        
        bars = plt.bar(labels, values, color=colors)
        
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
        
        plt.title('Распределение крупных нокаутов')
        plt.xlabel('Тип нокаута')
        plt.ylabel('Количество')
        plt.grid(True, linestyle='--', alpha=0.3, axis='y')
        
        if save_path:
            plt.savefig(save_path)
        else:
            plt.show()
            
    def plot_multi_knockout_ratio(self, save_path: Optional[str] = None):
        """
        Создает круговую диаграмму соотношения обычных нокаутов и мульти-нокаутов.
        
        Args:
            save_path: Путь для сохранения графика (опционально)
        """
        stats = self.get_multi_knockout_stats()
        
        labels = ['Обычные нокауты', 'Мульти-нокауты']
        values = [stats['single'], stats['multi']]
        
        # Проверяем, есть ли данные
        if sum(values) == 0:
            return
            
        plt.figure(figsize=(8, 8))
        
        # Создаем круговую диаграмму
        plt.pie(values, labels=labels, autopct='%1.1f%%', 
                shadow=True, startangle=90, 
                colors=['#4CAF50', '#2196F3'])
                
        plt.axis('equal')  # Круговая диаграмма выглядит лучше в равных осях
        plt.title('Соотношение обычных и мульти-нокаутов')
        
        if save_path:
            plt.savefig(save_path)
        else:
            plt.show()
            
    def calculate_knockout_efficiency(self, session_id: Optional[str] = None) -> Dict[str, float]:
        """
        Рассчитывает эффективность нокаутов (отношение нокаутов к количеству турниров).
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Словарь с показателями эффективности
        """
        if not self.db_manager or not self.db_manager.connection:
            return {
                'knockouts_per_tournament': 0.0,
                'large_knockouts_per_tournament': 0.0
            }
            
        cursor = self.db_manager.connection.cursor()
        
        # Получаем количество турниров
        if session_id:
            cursor.execute(
                "SELECT COUNT(*) FROM tournaments WHERE session_id = ?", 
                (session_id,)
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM tournaments")
            
        result = cursor.fetchone()
        total_tournaments = result[0] if result else 0
        
        if total_tournaments == 0:
            return {
                'knockouts_per_tournament': 0.0,
                'large_knockouts_per_tournament': 0.0
            }
            
        # Получаем количество нокаутов
        total_knockouts = self.get_total_knockouts(session_id)
        
        # Получаем количество крупных нокаутов
        large_stats = self.get_large_knockouts_stats(session_id)
        total_large_knockouts = sum(large_stats.values())
        
        return {
            'knockouts_per_tournament': round(total_knockouts / total_tournaments, 2),
            'large_knockouts_per_tournament': round(total_large_knockouts / total_tournaments, 2)
        }
        
    def generate_knockout_report(self, session_id: Optional[str] = None) -> Dict[str, Union[int, float, Dict]]:
        """
        Генерирует полный отчет по нокаутам.
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Словарь с полной статистикой по нокаутам
        """
        total_knockouts = self.get_total_knockouts(session_id)
        large_knockouts = self.get_large_knockouts_stats(session_id)
        multi_stats = self.get_multi_knockout_stats(session_id)
        efficiency = self.calculate_knockout_efficiency(session_id)
        
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
        
        return {
            'total_knockouts': total_knockouts,
            'large_knockouts': large_knockouts,
            'multi_knockouts': multi_stats,
            'efficiency': efficiency,
            'total_tournaments': total_tournaments,
            'report_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


# Функции для удобства использования без создания экземпляра класса

def get_total_knockouts(db_manager, session_id=None):
    """
    Возвращает общее количество нокаутов.
    
    Args:
        db_manager: Экземпляр менеджера базы данных
        session_id: ID сессии для фильтрации (опционально)
        
    Returns:
        Общее количество нокаутов
    """
    analyzer = KnockoutsAnalyzer(db_manager)
    return analyzer.get_total_knockouts(session_id)

def get_large_knockouts_stats(db_manager, session_id=None):
    """
    Возвращает статистику по крупным нокаутам.
    
    Args:
        db_manager: Экземпляр менеджера базы данных
        session_id: ID сессии для фильтрации (опционально)
        
    Returns:
        Словарь со статистикой крупных нокаутов
    """
    analyzer = KnockoutsAnalyzer(db_manager)
    return analyzer.get_large_knockouts_stats(session_id)

def calculate_knockout_efficiency(db_manager, session_id=None):
    """
    Рассчитывает эффективность нокаутов.
    
    Args:
        db_manager: Экземпляр менеджера базы данных
        session_id: ID сессии для фильтрации (опционально)
        
    Returns:
        Словарь с показателями эффективности
    """
    analyzer = KnockoutsAnalyzer(db_manager)
    return analyzer.calculate_knockout_efficiency(session_id)