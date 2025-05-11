#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Компоненты для визуализации статистики покерного трекера ROYAL_Stats.
"""

import matplotlib
matplotlib.use('Qt5Agg')  # Используем бэкенд Qt для matplotlib

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QSizePolicy, QGroupBox, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class PlaceDistributionChart(QWidget):
    """
    Виджет для отображения гистограммы распределения мест.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._init_ui()
        
    def _init_ui(self):
        """
        Инициализирует элементы интерфейса.
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Создаем фигуру и канвас для matplotlib
        self.figure = Figure(figsize=(8, 5), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Добавляем тулбар для навигации (зум, перемещение и т.д.)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        # Добавляем виджеты на layout
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        # Создаем оси для графика
        self.ax = self.figure.add_subplot(111)
        
    def update_chart(self, data):
        """
        Обновляет гистограмму с новыми данными.
        
        Args:
            data: Словарь {место: количество}
        """
        # Очищаем оси
        self.ax.clear()
        
        # Получаем данные для построения
        places = list(data.keys())
        counts = list(data.values())
        
        # Строим гистограмму
        bars = self.ax.bar(places, counts, color='skyblue', edgecolor='navy')
        
        # Добавляем подписи к столбцам
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                self.ax.text(
                    bar.get_x() + bar.get_width() / 2.,
                    height,
                    f'{int(height)}',
                    ha='center', va='bottom'
                )
        
        # Настраиваем оси
        self.ax.set_xlabel('Место')
        self.ax.set_ylabel('Количество турниров')
        self.ax.set_title('Распределение занятых мест')
        self.ax.set_xticks(places)
        
        # Устанавливаем целочисленные метки на оси Y
        import matplotlib.ticker as ticker
        self.ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        
        # Отображаем сетку
        self.ax.grid(True, linestyle='--', alpha=0.7)
        
        # Обновляем канвас
        self.canvas.draw()


class StatsCard(QFrame):
    """
    Карточка для отображения отдельного статистического показателя.
    """
    
    def __init__(self, title, value="", parent=None):
        super().__init__(parent)
        
        self.title = title
        self.value = value
        
        self._init_ui()
        
    def _init_ui(self):
        """
        Инициализирует элементы интерфейса.
        """
        # Стилизуем карточку
        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(1)
        self.setMidLineWidth(0)
        self.setStyleSheet("""
            StatsCard {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
            }
        """)
        
        # Создаем layout
        layout = QVBoxLayout(self)
        
        # Заголовок
        self.title_label = QLabel(self.title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-weight: bold; color: #495057;")
        
        # Значение
        self.value_label = QLabel(str(self.value))
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.value_label.setFont(font)
        self.value_label.setStyleSheet("color: #0066cc;")
        
        # Добавляем виджеты на layout
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        
    def set_value(self, value):
        """
        Устанавливает новое значение для карточки.
        
        Args:
            value: Новое значение
        """
        self.value = value
        self.value_label.setText(str(value))


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
        knockouts_group = QGroupBox("Накауты")
        
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
        
        # Layout для группы накаутов
        knockouts_layout = QGridLayout()
        
        # Создаем карточки для группы накаутов
        self.cards['total_knockouts'] = StatsCard("Всего накаутов", "0")
        self.cards['knockouts_x10'] = StatsCard("x10 накаутов", "0")
        self.cards['knockouts_x100'] = StatsCard("x100 накаутов", "0")
        self.cards['knockouts_x1000'] = StatsCard("x1000 накаутов", "0")
        self.cards['knockouts_x10000'] = StatsCard("x10000 накаутов", "0")
        
        # Добавляем карточки на layout группы накаутов
        knockouts_layout.addWidget(self.cards['total_knockouts'], 0, 0)
        knockouts_layout.addWidget(self.cards['knockouts_x10'], 0, 1)
        knockouts_layout.addWidget(self.cards['knockouts_x100'], 0, 2)
        knockouts_layout.addWidget(self.cards['knockouts_x1000'], 1, 0)
        knockouts_layout.addWidget(self.cards['knockouts_x10000'], 1, 1)
        
        # Устанавливаем layout для группы накаутов
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
        
        # Обновляем карточки с данными о накаутах
        self.cards['total_knockouts'].set_value(stats.get('total_knockouts', 0))
        self.cards['knockouts_x10'].set_value(stats.get('total_knockouts_x10', 0))
        self.cards['knockouts_x100'].set_value(stats.get('total_knockouts_x100', 0))
        self.cards['knockouts_x1000'].set_value(stats.get('total_knockouts_x1000', 0))
        self.cards['knockouts_x10000'].set_value(stats.get('total_knockouts_x10000', 0))