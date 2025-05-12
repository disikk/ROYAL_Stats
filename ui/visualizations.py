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
    
    def __init__(self, title, value, parent=None):
        super().__init__(parent)
        
        # Настраиваем стиль карточки
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setMinimumSize(150, 100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # Задаем цвет фона
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(240, 248, 255))  # Светло-голубой
        self.setPalette(palette)
        self.setAutoFillBackground(True)
        
        # Создаем layout
        layout = QVBoxLayout(self)
        
        # Заголовок
        self.title_label = QLabel(title)
        title_font = QFont()
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Значение
        self.value_label = QLabel(str(value))
        value_font = QFont()
        value_font.setPointSize(14)
        value_font.setBold(True)
        self.value_label.setFont(value_font)
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
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Создаем фигуру matplotlib
        self.figure = Figure(figsize=(8, 4))
        self.canvas = FigureCanvas(self.figure)
        
        # Добавляем виджеты на layout
        layout.addWidget(title_label)
        layout.addWidget(self.canvas)
        
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
        self.places = list(places_distribution.keys())
        self.counts = list(places_distribution.values())
        
        # Создаем подграфик
        ax = self.figure.add_subplot(111)
        
        # Создаем цветовую гамму от темного к светлому
        # Первое место - самый темный (лучший)
        colors = plt.cm.Blues(np.linspace(0.8, 0.4, len(self.places)))
        
        # Создаем столбцы
        bars = ax.bar(self.places, self.counts, color=colors)
        
        # Добавляем подписи к столбцам
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2.,
                    height,
                    f'{int(height)}',
                    ha='center', va='bottom'
                )
        
        # Настраиваем оси
        ax.set_xlabel('Место')
        ax.set_ylabel('Количество турниров')
        ax.set_xticks(self.places)
        ax.grid(True, linestyle='--', alpha=0.3, axis='y')
        
        # Обновляем canvas
        self.canvas.draw()


class KnockoutsChart(QWidget):
    """
    Виджет для отображения гистограммы распределения нокаутов.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Создаем layout
        layout = QVBoxLayout(self)
        
        # Заголовок
        title_label = QLabel("Распределение нокаутов")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Создаем фигуру matplotlib
        self.figure = Figure(figsize=(8, 4))
        self.canvas = FigureCanvas(self.figure)
        
        # Добавляем виджеты на layout
        layout.addWidget(title_label)
        layout.addWidget(self.canvas)
        
        # Начальные данные для гистограммы
        self.labels = ['x2', 'x10', 'x100', 'x1000', 'x10000']
        self.values = [0] * 5
        
        # Создаем гистограмму
        self.update_chart({'x2': 0, 'x10': 0, 'x100': 0, 'x1000': 0, 'x10000': 0})
        
    def update_chart(self, knockouts_stats):
        """
        Обновляет гистограмму с новыми данными.
        
        Args:
            knockouts_stats: Словарь {тип_нокаута: количество}
        """
        # Очищаем фигуру
        self.figure.clear()
        
        # Получаем данные
        self.values = [
            knockouts_stats.get('x2', 0),
            knockouts_stats.get('x10', 0),
            knockouts_stats.get('x100', 0),
            knockouts_stats.get('x1000', 0),
            knockouts_stats.get('x10000', 0)
        ]
        
        # Создаем подграфик
        ax = self.figure.add_subplot(111)
        
        # Создаем цветовую гамму
        colors = plt.cm.Reds(np.linspace(0.4, 0.8, len(self.labels)))
        
        # Создаем столбцы
        bars = ax.bar(self.labels, self.values, color=colors)
        
        # Добавляем подписи к столбцам
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2.,
                    height,
                    f'{int(height)}',
                    ha='center', va='bottom'
                )
        
        # Настраиваем оси
        ax.set_xlabel('Тип нокаута')
        ax.set_ylabel('Количество')
        ax.grid(True, linestyle='--', alpha=0.3, axis='y')
        
        # Обновляем canvas
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
        # Основной layout
        main_layout = QVBoxLayout(self)
        
        # Создаем группы карточек
        tournaments_group = QGroupBox("Турниры")
        knockouts_group = QGroupBox("Нокауты")
        
        # Layout для группы турниров
        tournaments_layout = QGridLayout()
        
        # Создаем карточки для группы турниров
        self.cards['total_tournaments'] = StatsCard("Всего турниров", "0")
        self.cards['avg_finish_place'] = StatsCard("Среднее место", "0.00")
        self.cards['first_places'] = StatsCard("Первых мест", "0")
        self.cards['second_places'] = StatsCard("Вторых мест", "0")
        self.cards['third_places'] = StatsCard("Третьих мест", "0")
        self.cards['total_prize'] = StatsCard("Общий выигрыш", "$0.00")
        
        # Добавляем карточки на layout группы турниров
        tournaments_layout.addWidget(self.cards['total_tournaments'], 0, 0)
        tournaments_layout.addWidget(self.cards['avg_finish_place'], 0, 1)
        tournaments_layout.addWidget(self.cards['first_places'], 1, 0)
        tournaments_layout.addWidget(self.cards['second_places'], 1, 1)
        tournaments_layout.addWidget(self.cards['third_places'], 1, 2)
        tournaments_layout.addWidget(self.cards['total_prize'], 0, 2)
        
        # Устанавливаем layout для группы турниров
        tournaments_group.setLayout(tournaments_layout)
        
        # Layout для группы нокаутов
        knockouts_layout = QGridLayout()
        
        # Создаем карточки для группы нокаутов
        self.cards['total_knockouts'] = StatsCard("Всего нокаутов", "0")
        self.cards['knockouts_x2'] = StatsCard("x2 нокаутов", "0")
        self.cards['knockouts_x10'] = StatsCard("x10 нокаутов", "0")
        self.cards['knockouts_x100'] = StatsCard("x100 нокаутов", "0")
        self.cards['knockouts_x1000'] = StatsCard("x1000 нокаутов", "0")
        self.cards['knockouts_x10000'] = StatsCard("x10000 нокаутов", "0")
        
        # Добавляем карточки на layout группы нокаутов
        knockouts_layout.addWidget(self.cards['total_knockouts'], 0, 0)
        knockouts_layout.addWidget(self.cards['knockouts_x2'], 0, 1)
        knockouts_layout.addWidget(self.cards['knockouts_x10'], 0, 2)
        knockouts_layout.addWidget(self.cards['knockouts_x100'], 1, 0)
        knockouts_layout.addWidget(self.cards['knockouts_x1000'], 1, 1)
        knockouts_layout.addWidget(self.cards['knockouts_x10000'], 1, 2)
        
        # Устанавливаем layout для группы нокаутов
        knockouts_group.setLayout(knockouts_layout)
        
        # Добавляем группы на основной layout
        main_layout.addWidget(tournaments_group)
        main_layout.addWidget(knockouts_group)
        
    def update_stats(self, stats):
        """
        Обновляет все карточки с новыми данными.
        
        Args:
            stats: Словарь со статистикой
        """
        # Обновляем карточки с данными о турнирах
        self.cards['total_tournaments'].set_value(stats.get('total_tournaments', 0))
        self.cards['avg_finish_place'].set_value(f"{stats.get('avg_finish_place', 0):.2f}")
        self.cards['first_places'].set_value(stats.get('first_places', 0))
        self.cards['second_places'].set_value(stats.get('second_places', 0))
        self.cards['third_places'].set_value(stats.get('third_places', 0))
        self.cards['total_prize'].set_value(f"${stats.get('total_prize', 0):.2f}")
        
        # Обновляем карточки с данными о нокаутах
        self.cards['total_knockouts'].set_value(stats.get('total_knockouts', 0))
        self.cards['knockouts_x2'].set_value(stats.get('total_knockouts_x2', 0))
        self.cards['knockouts_x10'].set_value(stats.get('total_knockouts_x10', 0))
        self.cards['knockouts_x100'].set_value(stats.get('total_knockouts_x100', 0))
        self.cards['knockouts_x1000'].set_value(stats.get('total_knockouts_x1000', 0))
        self.cards['knockouts_x10000'].set_value(stats.get('total_knockouts_x10000', 0))