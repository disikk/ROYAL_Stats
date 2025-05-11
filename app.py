#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ROYAL_Stats - Покерный трекер для анализа статистики игрока
"""

import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    """Основная функция запуска приложения"""
    app = QApplication(sys.argv)
    app.setApplicationName("ROYAL_Stats")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
