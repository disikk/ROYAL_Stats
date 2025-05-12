#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль с визуальными компонентами для отображения статистики в покерном трекере ROYAL_Stats.
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QGridLayout,
    QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor, QPalette


class StatsCard(QFrame):
    """
    Карточка для отображения одного статистического показателя.
    """
    
    def __init__(self, title, value, parent=None, value_color="#2c3e50"):
        super().__init__(parent)
        
        # Настраиваем стиль карточки
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        # Уменьшенные размеры: 150/1.5 = 100, 120/1.5 = 80
        self.setMinimumSize(100, 80) 
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # Задаем цвет фона с градиентом
        self.setStyleSheet(f"""
            QFrame {{
                background-color: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #f8f9fa, stop: 1 #e9ecef
                );
                border-radius: 6px; /* Немного уменьшил радиус */
                border: 1px solid #dee2e6;
            }}
            QLabel {{
                background-color: transparent;
            }}
        """)
        
        # Создаем layout
        layout = QVBoxLayout(self)
        # Уменьшенные отступы: 10/1.5 ~ 7, 15/1.5 = 10
        layout.setContentsMargins(7, 10, 7, 10) 
        
        # Заголовок
        self.title_label = QLabel(title)
        title_font = QFont()
        title_font.setBold(True)
        # Уменьшенный размер шрифта: 11pt / 1.5 ~ 7.33pt. Используем 8pt или 7pt.
        # Попробуем 8pt. Если будет слишком крупно, можно уменьшить до 7pt.
        self.title_label.setFont(title_font) 
        self.title_label.setStyleSheet(f"color: #343a40; font-size: 8pt;") # Изменено на 8pt
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Значение
        self.value_label = QLabel(str(value))
        value_font = QFont()
        # Уменьшенный размер шрифта: 18pt / 1.5 = 12pt
        value_font.setPointSize(12) 
        value_font.setBold(True)
        self.value_label.setFont(value_font)
        self.value_label.setStyleSheet(f"color: {value_color}; font-size: 12pt;") # Изменено на 12pt
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Добавляем виджеты на layout
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        
    def set_value(self, value):
        """
        Обновляет значение карточки.
        
        Args:
            value: Новое значение для отображения
        """
        self.value_label.setText(str(value))


class PlaceDistributionChart(QWidget):
    """
    Виджет для отображения гистограммы распределения мест.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Создаем layout
        layout = QVBoxLayout(self)
        
        # Заголовок
        title_label = QLabel("Распределение мест")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12) # Немного уменьшим для общей компактности
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #343a40; margin-bottom: 8px;") # Уменьшен margin
        
        # Создаем фрейм для графика
        chart_frame = QFrame()
        chart_frame.setFrameShape(QFrame.Shape.StyledPanel)
        chart_frame.setFrameShadow(QFrame.Shadow.Raised)
        chart_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #dee2e6;
            }
        """)
        chart_layout = QVBoxLayout(chart_frame)
        
        # Создаем фигуру matplotlib
        self.figure = Figure(figsize=(7, 3.5), dpi=90) # Немного уменьшим размер и dpi для компактности
        self.figure.patch.set_facecolor('white')
        self.canvas = FigureCanvas(self.figure)
        chart_layout.addWidget(self.canvas)
        
        # Добавляем виджеты на layout
        layout.addWidget(title_label)
        layout.addWidget(chart_frame)
        
        # Начальные данные для гистограммы
        self.places = list(range(1, 10))
        self.counts = [0] * 9
        
        # Создаем гистограмму
        self.update_chart({i: 0 for i in range(1, 10)})
        
    def update_chart(self, places_distribution):
        """
        Обновляет гистограмму с новыми данными.
        
        Args:
            places_distribution: Словарь {место: количество_турниров}
        """
        # Очищаем фигуру
        self.figure.clear()
        
        # Получаем данные
        # Убедимся, что ключи от 1 до 9 существуют, даже если их нет в places_distribution
        self.places = list(range(1, 10))
        self.counts = [places_distribution.get(p, 0) for p in self.places]

        # Создаем подграфик с заданным стилем
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#f8f9fa')
        self.figure.patch.set_facecolor('white')
        
        colors = []
        for place in self.places:
            if place == 1: colors.append('#28a745') 
            elif place == 2: colors.append('#17a2b8') 
            elif place == 3: colors.append('#6f42c1')  
            elif place <= 6: colors.append('#fd7e14') 
            else: colors.append('#dc3545') 
        
        bars = ax.bar(
            self.places, self.counts, 
            color=colors,
            edgecolor='#343a40',
            linewidth=0.5,
            alpha=0.8,
            width=0.7
        )
        
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2.,
                    height + 0.05 * max(self.counts if any(self.counts) else [1]), # Динамический отступ для текста
                    f'{int(height)}',
                    ha='center', va='bottom',
                    fontweight='bold',
                    fontsize=8 # Уменьшен шрифт подписей
                )
        
        ax.set_xlabel('Место', fontsize=10, fontweight='bold', labelpad=8) # Уменьшены размеры
        ax.set_ylabel('Количество турниров', fontsize=10, fontweight='bold', labelpad=8) # Уменьшены размеры
        ax.set_xticks(self.places)
        ax.set_xticklabels(self.places, fontsize=9) # Уменьшены размеры
        ax.set_yticklabels([f"{int(y)}" for y in ax.get_yticks()], fontsize=9) # Уменьшены размеры
        
        ax.grid(True, linestyle='--', alpha=0.3, axis='y')
        ax.set_xlim(0.5, len(self.places) + 0.5)
        
        if max(self.counts) == 0:
            ax.set_ylim(0, 5)
        else:
            ax.set_ylim(0, max(self.counts) * 1.25) # Немного больше места сверху
        
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_linewidth(0.5)
        ax.spines['bottom'].set_linewidth(0.5)
        
        total_tournaments = sum(self.counts)
        ax.set_title(
            f'Распределение мест (всего: {total_tournaments})', 
            fontsize=12, # Уменьшен размер
            fontweight='bold',
            pad=10 # Уменьшен pad
        )
        
        self.figure.tight_layout(pad=2.0) # Уменьшен pad
        self.canvas.draw()


class KnockoutsChart(QWidget): # Не просили изменять, но для консистентности можно тоже немного уменьшить
    """
    Виджет для отображения гистограммы распределения нокаутов.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        title_label = QLabel("Распределение нокаутов")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12) # Уменьшено
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #343a40; margin-bottom: 8px;") # Уменьшено

        chart_frame = QFrame()
        chart_frame.setFrameShape(QFrame.Shape.StyledPanel)
        chart_frame.setFrameShadow(QFrame.Shadow.Raised)
        chart_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #dee2e6;
            }
        """)
        chart_layout = QVBoxLayout(chart_frame)
        
        self.figure = Figure(figsize=(7, 3.5), dpi=90) # Уменьшено
        self.figure.patch.set_facecolor('white')
        self.canvas = FigureCanvas(self.figure)
        chart_layout.addWidget(self.canvas)
        
        layout.addWidget(title_label)
        layout.addWidget(chart_frame)
        
        self.labels = ['x2', 'x10', 'x100', 'x1000', 'x10000']
        self.values = [0] * 5
        self.update_chart({'x2': 0, 'x10': 0, 'x100': 0, 'x1000': 0, 'x10000': 0})
        
    def update_chart(self, knockouts_stats):
        """
        Обновляет гистограмму с новыми данными.
        """
        self.figure.clear()
        self.values = [
            knockouts_stats.get('x2', knockouts_stats.get('total_knockouts_x2',0)), # Поддержка обоих ключей
            knockouts_stats.get('x10', knockouts_stats.get('total_knockouts_x10',0)),
            knockouts_stats.get('x100', knockouts_stats.get('total_knockouts_x100',0)),
            knockouts_stats.get('x1000', knockouts_stats.get('total_knockouts_x1000',0)),
            knockouts_stats.get('x10000', knockouts_stats.get('total_knockouts_x10000',0))
        ]
        
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#f8f9fa')
        
        colors = ['#6610f2', '#6f42c1', '#d63384', '#dc3545', '#fd7e14']
        
        bars = ax.bar(self.labels, self.values, color=colors, edgecolor='#343a40', linewidth=0.5, alpha=0.8, width=0.6)
        
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2.,
                    height + 0.05 * max(self.values if any(self.values) else [1]), # Динамический отступ
                    f'{int(height)}',
                    ha='center', va='bottom',
                    fontweight='bold', fontsize=8 # Уменьшен шрифт
                )
        
        ax.set_xlabel('Тип нокаута', fontsize=10, fontweight='bold', labelpad=8) # Уменьшено
        ax.set_ylabel('Количество', fontsize=10, fontweight='bold', labelpad=8) # Уменьшено
        # ax.set_xticklabels([''] + self.labels, fontsize=9) # Оставим автоматические тики для X
        ax.tick_params(axis='x', labelsize=9)
        ax.tick_params(axis='y', labelsize=9)


        ax.grid(True, linestyle='--', alpha=0.3, axis='y')
        
        if max(self.values) == 0:
            ax.set_ylim(0, 5)
        else:
            ax.set_ylim(0, max(self.values) * 1.25) # Немного больше места
            
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_linewidth(0.5)
        ax.spines['bottom'].set_linewidth(0.5)
        
        total_knockouts = sum(self.values)
        ax.set_title(
            f'Нокауты по множителям (всего: {total_knockouts})', 
            fontsize=12, # Уменьшено
            fontweight='bold',
            pad=10 # Уменьшено
        )
        
        self.figure.tight_layout(pad=2.0) # Уменьшено
        self.canvas.draw()


class StatsGrid(QWidget):
    """
    Сетка карточек с основными статистическими показателями.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.cards = {}  # Словарь {id_карточки: экземпляр_StatsCard}
        
        self._init_ui()
        
    def _init_ui(self):
        """
        Инициализирует элементы интерфейса.
        """
        main_layout = QVBoxLayout(self)
        
        tournaments_group = QGroupBox("Турниры")
        tournaments_group.setStyleSheet("""
            QGroupBox {
                font-size: 12px; /* Уменьшен шрифт заголовка группы */
                font-weight: bold;
                border: 1px solid #6c757d; /* Тоньше рамка */
                border-radius: 6px; /* Уменьшен радиус */
                margin-top: 10px; /* Уменьшен отступ */
                padding-top: 8px; /* Уменьшен отступ */
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px; /* Уменьшен отступ */
                padding: 0 3px; /* Уменьшен отступ */
                color: #212529;
            }
        """)
        
        knockouts_group = QGroupBox("Нокауты")
        knockouts_group.setStyleSheet("""
            QGroupBox {
                font-size: 12px; /* Уменьшен шрифт заголовка группы */
                font-weight: bold;
                border: 1px solid #6c757d; /* Тоньше рамка */
                border-radius: 6px; /* Уменьшен радиус */
                margin-top: 10px; /* Уменьшен отступ */
                padding-top: 8px; /* Уменьшен отступ */
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px; /* Уменьшен отступ */
                padding: 0 3px; /* Уменьшен отступ */
                color: #212529;
            }
        """)
        
        tournaments_layout = QGridLayout()
        tournaments_layout.setSpacing(10)  # Уменьшен интервал между карточками
        
        self.cards['total_tournaments'] = StatsCard("Всего турниров", "0", value_color="#0d6efd")
        self.cards['avg_finish_place'] = StatsCard("Среднее место", "0.00", value_color="#fd7e14")
        self.cards['first_places'] = StatsCard("Первых мест", "0", value_color="#198754")
        self.cards['second_places'] = StatsCard("Вторых мест", "0", value_color="#0dcaf0")
        self.cards['third_places'] = StatsCard("Третьих мест", "0", value_color="#6f42c1")
        self.cards['total_prize'] = StatsCard("Общий выигрыш", "$0.00", value_color="#dc3545")
        
        tournaments_layout.addWidget(self.cards['total_tournaments'], 0, 0)
        tournaments_layout.addWidget(self.cards['avg_finish_place'], 0, 1)
        tournaments_layout.addWidget(self.cards['total_prize'], 0, 2) # Перенес сюда для лучшего вида
        tournaments_layout.addWidget(self.cards['first_places'], 1, 0)
        tournaments_layout.addWidget(self.cards['second_places'], 1, 1)
        tournaments_layout.addWidget(self.cards['third_places'], 1, 2)
        
        tournaments_group.setLayout(tournaments_layout)
        
        knockouts_layout = QGridLayout()
        knockouts_layout.setSpacing(10)  # Уменьшен интервал
        
        self.cards['total_knockouts'] = StatsCard("Всего нокаутов", "0", value_color="#0d6efd")
        self.cards['knockouts_x2'] = StatsCard("x2 нокаутов", "0", value_color="#6610f2")
        self.cards['knockouts_x10'] = StatsCard("x10 нокаутов", "0", value_color="#6f42c1")
        self.cards['knockouts_x100'] = StatsCard("x100 нокаутов", "0", value_color="#d63384")
        self.cards['knockouts_x1000'] = StatsCard("x1000 нокаутов", "0", value_color="#dc3545")
        self.cards['knockouts_x10000'] = StatsCard("x10000 нокаутов", "0", value_color="#fd7e14")
        
        knockouts_layout.addWidget(self.cards['total_knockouts'], 0, 0)
        knockouts_layout.addWidget(self.cards['knockouts_x2'], 0, 1)
        knockouts_layout.addWidget(self.cards['knockouts_x10'], 0, 2)
        knockouts_layout.addWidget(self.cards['knockouts_x100'], 1, 0)
        knockouts_layout.addWidget(self.cards['knockouts_x1000'], 1, 1)
        knockouts_layout.addWidget(self.cards['knockouts_x10000'], 1, 2)
        
        knockouts_group.setLayout(knockouts_layout)
        
        main_layout.addWidget(tournaments_group)
        main_layout.addWidget(knockouts_group)
        
    def update_stats(self, stats):
        """
        Обновляет все карточки с новыми данными.
        
        Args:
            stats: Словарь со статистикой
        """
        # Обновляем карточки с данными о турнирах
        self.cards['total_tournaments'].set_value(format_number(stats.get('total_tournaments', 0)))
        avg_finish_place = stats.get('avg_finish_place', 0.0)
        # Убедимся, что avg_finish_place это число перед форматированием
        try:
            avg_finish_place_float = float(avg_finish_place)
            self.cards['avg_finish_place'].set_value(f"{avg_finish_place_float:.2f}")
        except (ValueError, TypeError):
            self.cards['avg_finish_place'].set_value("0.00") # Значение по умолчанию, если не число

        self.cards['first_places'].set_value(format_number(stats.get('first_places', 0)))
        self.cards['second_places'].set_value(format_number(stats.get('second_places', 0)))
        self.cards['third_places'].set_value(format_number(stats.get('third_places', 0)))
        self.cards['total_prize'].set_value(f"${format_money(stats.get('total_prize', 0.0))}") # Используем 0.0 как дефолт
        
        # Обновляем карточки с данными о нокаутах
        self.cards['total_knockouts'].set_value(format_number(stats.get('total_knockouts', 0)))
        self.cards['knockouts_x2'].set_value(format_number(stats.get('total_knockouts_x2', 0)))
        self.cards['knockouts_x10'].set_value(format_number(stats.get('total_knockouts_x10', 0)))
        self.cards['knockouts_x100'].set_value(format_number(stats.get('total_knockouts_x100', 0)))
        self.cards['knockouts_x1000'].set_value(format_number(stats.get('total_knockouts_x1000', 0)))
        self.cards['knockouts_x10000'].set_value(format_number(stats.get('total_knockouts_x10000', 0)))


# Вспомогательные функции для форматирования чисел
def format_number(number):
    """
    Форматирует число с разделителями тысяч.
    """
    try:
        num = int(number)
        return f"{num:,}".replace(',', ' ')
    except (ValueError, TypeError):
        return str(number) # Возвращаем как есть, если не число

def format_money(amount):
    """
    Форматирует денежную сумму с разделителями тысяч и двумя знаками после запятой.
    """
    try:
        num = float(amount)
        return f"{num:,.2f}".replace(',', ' ')
    except (ValueError, TypeError):
        try: # Попытка отформатировать как целое, если float не удался
            num_int = int(amount)
            return f"{num_int:,.2f}".replace(',', ' ')
        except (ValueError, TypeError):
            return str(amount) # Возвращаем как есть, если не число
