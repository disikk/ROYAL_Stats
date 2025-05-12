#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ROYAL_Stats - Покерный трекер для анализа статистики игрока

Основной модуль запуска приложения.
Инициализирует графический интерфейс и запускает главное окно приложения.

Функциональность:
1. Подсчет нокаутов (когда Hero выбил другого игрока)
2. Подсчет среднего места, с которого игрок вылетел (1-9)
3. Подсчет количества x10, x100, x1000, x10000 нокаутов
4. Построение гистограммы распределения позиций
5. Сохранение и обновление статистики в базе данных
6. Управление несколькими базами данных

Автор: Royal Team
Версия: 1.0
Дата: 2025
"""

import sys
import os
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtCore import QLocale, QTranslator, QCoreApplication
from ui.main_window import MainWindow

# Глобальная настройка кодировки
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Настройка логирования
def setup_logging():
    """Настраивает систему логирования приложения"""
    # Создаем папку для логов, если она не существует
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    # Настраиваем логирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/royal_stats.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # Создаем логгер
    logger = logging.getLogger('ROYAL_Stats')
    logger.info('Запуск приложения ROYAL_Stats')
    
    return logger

# Основная точка входа
def main():
    """
    Основная функция запуска приложения.
    Инициализирует графический интерфейс и запускает главное окно приложения.
    """
    # Настраиваем логирование
    logger = setup_logging()
    
    try:
        # Создаем приложение Qt
        app = QApplication(sys.argv)
        app.setApplicationName("ROYAL_Stats")
        app.setApplicationVersion("1.0")
        
        # Настраиваем локализацию для поддержки кириллицы
        locale = QLocale(QLocale.Language.Russian)
        QLocale.setDefault(locale)
        
        # Настраиваем стиль приложения с указанием шрифта, поддерживающего кириллицу
        app.setStyle("Fusion")
        
        # Устанавливаем шрифт по умолчанию с поддержкой кириллицы
        default_font = QFont("Arial", 9)  # Arial обычно хорошо поддерживает кириллицу
        app.setFont(default_font)
        
        # Создаем главное окно приложения
        window = MainWindow()
        window.show()
        
        # Запускаем цикл обработки событий
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
        raise

# Точка входа при запуске скрипта
if __name__ == "__main__":
    main()
