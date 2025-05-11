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
        
        # Получаем общее количество нокаутов
        self.db_manager.cursor.execute("SELECT COUNT(*) FROM knockouts")
        total_knockouts = self.db_manager.cursor.fetchone()[0]
        
        # Получаем количество x2 нокаутов
        self.db_manager.cursor.execute("SELECT SUM(knockouts_x2) FROM tournaments")
        result = self.db_manager.cursor.fetchone()[0]
        total_knockouts_x2 = result if result is not None else 0
        
        # Получаем количество x10 нокаутов
        self.db_manager.cursor.execute("SELECT SUM(knockouts_x10) FROM tournaments")
        result = self.db_manager.cursor.fetchone()[0]
        total_knockouts_x10 = result if result is not None else 0
        
        # Получаем количество x100 нокаутов
        self.db_manager.cursor.execute("SELECT SUM(knockouts_x100) FROM tournaments")
        result = self.db_manager.cursor.fetchone()[0]
        total_knockouts_x100 = result if result is not None else 0
        
        # Получаем количество x1000 нокаутов
        self.db_manager.cursor.execute("SELECT SUM(knockouts_x1000) FROM tournaments")
        result = self.db_manager.cursor.fetchone()[0]
        total_knockouts_x1000 = result if result is not None else 0
        
        # Получаем количество x10000 нокаутов
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
            total_knockouts_x2,
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
        tournament_data.get('players_count', tournament_data.get('players', 9)),  # Поддержка обоих форматов
        tournament_data.get('prize_pool'),
        tournament_data.get('start_time'),
        tournament_data.get('finish_place'),
        tournament_data.get('prize', tournament_data.get('prize_total', 0)),  # Поддержка обоих форматов
        tournament_data.get('knockouts_x2', 0),
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