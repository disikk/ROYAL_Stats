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