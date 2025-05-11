#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Схема базы данных для покерного трекера ROYAL_Stats.
Определяет структуру таблиц для хранения информации о турнирах, накаутах и статистике.
"""

# SQL-запросы для создания таблиц

# Таблица для хранения информации о турнирах
CREATE_TOURNAMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS tournaments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id TEXT,
    tournament_name TEXT,
    game_type TEXT,
    buy_in REAL,
    fee REAL,
    bounty REAL,
    total_buy_in REAL,
    players_count INTEGER,
    prize_pool REAL,
    start_time TEXT,
    finish_place INTEGER,
    prize REAL,
    knockouts_x10 INTEGER,
    knockouts_x100 INTEGER,
    knockouts_x1000 INTEGER,
    knockouts_x10000 INTEGER,
    session_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

# Таблица для хранения информации о накаутах
CREATE_KNOCKOUTS_TABLE = """
CREATE TABLE IF NOT EXISTS knockouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id TEXT,
    hand_id TEXT,
    knocked_out_player TEXT,
    pot_size INTEGER,
    multi_knockout BOOLEAN,
    session_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

# Таблица для хранения общей статистики
CREATE_STATISTICS_TABLE = """
CREATE TABLE IF NOT EXISTS statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    total_tournaments INTEGER DEFAULT 0,
    total_knockouts INTEGER DEFAULT 0,
    total_knockouts_x10 INTEGER DEFAULT 0,
    total_knockouts_x100 INTEGER DEFAULT 0,
    total_knockouts_x1000 INTEGER DEFAULT 0,
    total_knockouts_x10000 INTEGER DEFAULT 0,
    avg_finish_place REAL DEFAULT 0,
    first_places INTEGER DEFAULT 0,
    second_places INTEGER DEFAULT 0,
    third_places INTEGER DEFAULT 0,
    total_prize REAL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

# Таблица для хранения распределения мест
CREATE_PLACES_DISTRIBUTION_TABLE = """
CREATE TABLE IF NOT EXISTS places_distribution (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place INTEGER,
    count INTEGER DEFAULT 0,
    UNIQUE(place)
)
"""

# Таблица для хранения информации о сессиях загрузки
CREATE_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE,
    session_name TEXT,
    tournaments_count INTEGER DEFAULT 0,
    knockouts_count INTEGER DEFAULT 0,
    avg_finish_place REAL DEFAULT 0,
    total_prize REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

# Список всех SQL-запросов для создания таблиц
CREATE_TABLES_QUERIES = [
    CREATE_TOURNAMENTS_TABLE,
    CREATE_KNOCKOUTS_TABLE,
    CREATE_STATISTICS_TABLE,
    CREATE_PLACES_DISTRIBUTION_TABLE,
    CREATE_SESSIONS_TABLE
]

# SQL-запросы для вставки данных

# Вставка информации о турнире
INSERT_TOURNAMENT = """
INSERT INTO tournaments (
    tournament_id, tournament_name, game_type, buy_in, fee, bounty,
    total_buy_in, players_count, prize_pool, start_time, finish_place, prize,
    knockouts_x10, knockouts_x100, knockouts_x1000, knockouts_x10000, session_id
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

# Вставка информации о накауте
INSERT_KNOCKOUT = """
INSERT INTO knockouts (
    tournament_id, hand_id, knocked_out_player, pot_size, multi_knockout, session_id
) VALUES (?, ?, ?, ?, ?, ?)
"""

# Обновление общей статистики
UPDATE_STATISTICS = """
UPDATE statistics SET
    total_tournaments = ?,
    total_knockouts = ?,
    total_knockouts_x10 = ?,
    total_knockouts_x100 = ?,
    total_knockouts_x1000 = ?,
    total_knockouts_x10000 = ?,
    avg_finish_place = ?,
    first_places = ?,
    second_places = ?,
    third_places = ?,
    total_prize = ?,
    last_updated = CURRENT_TIMESTAMP
WHERE id = 1
"""

# Вставка или обновление начальной статистики
INSERT_INITIAL_STATISTICS = """
INSERT OR IGNORE INTO statistics (id) VALUES (1)
"""

# Вставка или обновление распределения мест
UPSERT_PLACE_DISTRIBUTION = """
INSERT INTO places_distribution (place, count) 
VALUES (?, ?)
ON CONFLICT(place) DO UPDATE SET
    count = count + excluded.count
"""

# Вставка информации о сессии
INSERT_SESSION = """
INSERT INTO sessions (
    session_id, session_name, tournaments_count, knockouts_count,
    avg_finish_place, total_prize
) VALUES (?, ?, ?, ?, ?, ?)
"""

# SQL-запросы для получения данных

# Получение общей статистики
GET_STATISTICS = """
SELECT * FROM statistics WHERE id = 1
"""

# Получение распределения мест
GET_PLACES_DISTRIBUTION = """
SELECT place, count FROM places_distribution ORDER BY place
"""

# Получение списка сессий
GET_SESSIONS = """
SELECT * FROM sessions ORDER BY created_at DESC
"""

# Получение информации о конкретной сессии
GET_SESSION_BY_ID = """
SELECT * FROM sessions WHERE session_id = ?
"""

# Получение турниров конкретной сессии
GET_TOURNAMENTS_BY_SESSION = """
SELECT * FROM tournaments WHERE session_id = ? ORDER BY start_time DESC
"""

# Получение накаутов конкретной сессии
GET_KNOCKOUTS_BY_SESSION = """
SELECT * FROM knockouts WHERE session_id = ?
"""

# Получение общего количества накаутов
GET_TOTAL_KNOCKOUTS = """
SELECT COUNT(*) FROM knockouts
"""

# Получение турниров по диапазону дат
GET_TOURNAMENTS_BY_DATE_RANGE = """
SELECT * FROM tournaments 
WHERE start_time BETWEEN ? AND ?
ORDER BY start_time DESC
"""

# Список запросов для удаления данных

# Удаление данных сессии
DELETE_SESSION_DATA = """
DELETE FROM tournaments WHERE session_id = ?;
DELETE FROM knockouts WHERE session_id = ?;
DELETE FROM sessions WHERE session_id = ?;
"""

# Удаление всех данных из базы
DELETE_ALL_DATA = """
DELETE FROM tournaments;
DELETE FROM knockouts;
DELETE FROM sessions;
DELETE FROM places_distribution;
UPDATE statistics SET
    total_tournaments = 0,
    total_knockouts = 0,
    total_knockouts_x10 = 0,
    total_knockouts_x100 = 0,
    total_knockouts_x1000 = 0,
    total_knockouts_x10000 = 0,
    avg_finish_place = 0,
    first_places = 0,
    second_places = 0,
    third_places = 0,
    total_prize = 0,
    last_updated = CURRENT_TIMESTAMP
WHERE id = 1;
"""