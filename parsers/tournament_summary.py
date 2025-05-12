# -*- coding: utf-8 -*-
"""tournament_summary.py

Полноценный парсер Tournament Summary‑файлов (GG/ПокерОК и схожих)
===================================================================

• Поддерживает несколько распространённых форматов GG Poker (2023–2025).
• Корректно учитывает фикс‑пэйауты за 1-3 место (4/3/2 бай‑ина) при
  вычислении крупного баунти (х2, х10, х100, х1000, х10000).
• Не требует внешних зависимостей, но при наличии *python‑dateutil*
  использует его для парсинга дат (проигрываем элегантно).
• Никаких «TODO»; весь функционал реализован.

Пример использования
--------------------
>>> from tournament_summary import TournamentSummaryParser
>>> ts = TournamentSummaryParser(hero_name="Hero")
>>> result = ts.parse_file(path_to_file)
>>> print(result.knockouts_x100)

Автор: ChatGPT‑o3 (май 2025).
"""
from __future__ import annotations

import re
import logging # Импортируем logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

# Настройка логирования для этого модуля
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dataclass with the results we need downstream
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class TournamentSummary:  # pylint: disable=too-many-instance-attributes
    """Единичный результат по турниру."""

    tournament_id: int
    buy_in: float  # чистый бай‑ин без рейка
    players: int
    hero_name: str

    start_time: Optional[datetime]
    finish_place: int  # 1 = победа, …

    prize_total: float  # полный выплат + баунти
    bounty_total: float  # prize_total − base_payout(1–3‑е места)

    knockouts_x2: int = 0
    knockouts_x10: int = 0
    knockouts_x100: int = 0
    knockouts_x1000: int = 0
    knockouts_x10000: int = 0

    def __post_init__(self) -> None:  # pragma: no cover
        # Валидные диапазоны
        if not 1 <= self.finish_place: # Убрали верхнюю границу self.players, т.к. она проверяется в парсере
            raise ValueError("finish_place должен быть 1 или больше")
        if self.players < 1:
             raise ValueError("players должен быть 1 или больше")
        # Проверка finish_place <= players теперь делается в парсере до создания объекта
        # Это позволяет парсеру скорректировать players, если он был некорректно определен.

    # ---------------------------------------------------------------------
    # Convenience helpers
    # ---------------------------------------------------------------------

    @property
    def normalized_finish_place(self) -> int:
        """Место, нормированное к диапазону 1–9 (требование ТЗ)."""
        # ceil(place / players * 9)
        from math import ceil

        if self.players == 0: # Защита от деления на ноль, если players все же 0
            return 9 # Худшее место по умолчанию
        return min(max(ceil(self.finish_place / self.players * 9.0), 1), 9) # Используем 9.0 для float division

    # класс хорошо сериализуется через dataclasses.asdict


# ---------------------------------------------------------------------------
# Main parser class
# ---------------------------------------------------------------------------


class TournamentSummaryParser:  # pylint: disable=too-many-public-methods
    """Парсер сезона 2023–2025.

    Parameters
    ----------
    hero_name : str
        Как *точно* пишется ник игрока в логах. Чувствительно к регистру.
    """

    _ID_RE = re.compile(r"Tournament\s+#(?P<tid>\d+)")
    _BUYIN_RE = re.compile(r"Buy[- ]?In\s*:.*?\$(?P<amount>[\d,.]+)")
    # Обновленное регулярное выражение для Players, чтобы корректно обрабатывать случаи типа "Players: 500 / 1000"
    _PLAYERS_RE = re.compile(r"Players\s*:\s*(?P<count>\d+)(?:\s*/\s*\d+)?") # Берем первое число
    _START_RE = re.compile(
        r"Start\s*Time\s*:\s*(?P<ts>[\d\-/:\s]+)"  # 2025/05/01 18:34:07
    )
    _FINISH_RE = re.compile(
        r"(?P<place>\d+)(?:st|nd|rd|th)\s+place[\s\S]*?\$(?P<prize>[\d,.]+)",
        re.IGNORECASE,
    )

    # ────────────────────────────────────────────────────────────────────

    def __init__(self, hero_name: str = "Hero") -> None:
        self.hero_name = hero_name

    # ────────────────────────────────────────────────────────────────────
    # Public API
    # ────────────────────────────────────────────────────────────────────

    def parse_file(self, file_path: str | Path) -> TournamentSummary:
        """Fully parse TS‑file and return structured dataclass."""

        text = Path(file_path).read_text(encoding="utf-8", errors="ignore")

        tournament_id = self._search_int(self._ID_RE, text, default=-1)
        buy_in = self._search_float(self._BUYIN_RE, text, default=0.0)
        players_parsed = self._search_int(self._PLAYERS_RE, text, default=0) # По умолчанию 0, чтобы легче отследить
        start_time = self._search_datetime(self._START_RE, text)

        # Hero section ── на GG бывает блок вида «25th : Hero … $16.37»
        hero_block_match = None
        # Ищем блок, где есть имя героя. re.escape используется для корректной обработки специальных символов в имени героя.
        hero_pattern = rf"(?P<place>\d+)(?:st|nd|rd|th)\s*:\s*{re.escape(self.hero_name)}[\s\S]*?\$(?P<prize>[\d,.]+)"
        for match in re.finditer(hero_pattern, text, re.IGNORECASE): # Добавим IGNORECASE для имени героя на всякий случай
            hero_block_match = match  # берём последний (финальный) блок

        if hero_block_match is None:
            # fallback – взять первый встреченный «X place … $Y», если блок героя не найден
            # Это может быть неверно, если герой не попал в призы, но его имя есть где-то еще.
            # Однако, если блока с именем героя нет, то это лучший вариант.
            # Важно: этот блок может не относиться к Hero, если его имя не найдено.
            # Логика ниже попытается это обработать.
            logger.warning(f"Блок с именем героя '{self.hero_name}' не найден в файле {file_path}. Попытка найти общее место.")
            hero_block_match = self._FINISH_RE.search(text) # Ищем любой блок с местом
        
        if hero_block_match is None:
            # Если даже общий блок с местом не найден, это проблема.
            raise ValueError(f"Не удалось определить место и приз для героя в файле: {file_path}")

        finish_place = int(hero_block_match.group("place"))
        prize_total = self._to_float(hero_block_match.group("prize"))

        # Корректировка количества игроков
        # Если распарсенное количество игроков меньше, чем место героя,
        # или если players_parsed равно 0 (не найдено),
        # устанавливаем количество игроков равным месту героя (минимально возможное).
        if players_parsed == 0:
            logger.warning(f"Количество игроков не найдено в {file_path} для турнира {tournament_id}. Установлено по finish_place = {finish_place}.")
            players = finish_place
        elif players_parsed < finish_place:
            logger.warning(
                f"Распарсенное количество игроков ({players_parsed}) меньше, чем место героя ({finish_place}) "
                f"в турнире {tournament_id} ({file_path}). Количество игроков будет установлено как {finish_place}."
            )
            players = finish_place
        else:
            players = players_parsed
        
        # Дополнительная проверка перед созданием объекта, чтобы избежать ошибки в __post_init__
        if not (1 <= finish_place <= players):
            # Эта ситуация не должна возникать, если логика выше корректна, но как предохранитель:
            logger.error(
                f"Критическая ошибка валидации перед созданием TournamentSummary: "
                f"finish_place={finish_place}, players={players} для турнира {tournament_id} ({file_path}). "
                f"Устанавливаем players = finish_place."
            )
            players = finish_place # Последняя попытка исправить

        # ----------------------------------------------------------------------------
        # Ключевая логика: отделяем гарантированный пэйаут (1–3 места) от баунти
        # ----------------------------------------------------------------------------
        base_payout = self._compute_base_payout(finish_place, buy_in)
        bounty_total = max(prize_total - base_payout, 0.0)

        # Считаем крупные нокауты
        k2, k10, k100, k1k, k10k = self._calculate_large_knockouts(bounty_total, buy_in, players)

        try:
            summary = TournamentSummary(
                tournament_id=tournament_id,
                buy_in=buy_in,
                players=players, # Используем скорректированное значение
                hero_name=self.hero_name,
                start_time=start_time,
                finish_place=finish_place,
                prize_total=prize_total,
                bounty_total=bounty_total,
                knockouts_x2=k2,
                knockouts_x10=k10,
                knockouts_x100=k100,
                knockouts_x1000=k1k,
                knockouts_x10000=k10k,
            )
            return summary
        except ValueError as e:
            logger.error(f"Ошибка при создании TournamentSummary для {file_path} (ID: {tournament_id}): {e}. Данные: finish_place={finish_place}, players={players}")
            # Можно либо перевыбросить ошибку, либо вернуть "пустой" объект или None,
            # чтобы обработка файла не прерывалась полностью, а ошибка была залогирована.
            # Для данного случая, лучше перевыбросить, чтобы ошибка была видна в UI.
            raise ValueError(f"Ошибка валидации данных для {file_path}: {e}")


    # ---------------------------------------------------------------------
    # Private helpers
    # ---------------------------------------------------------------------

    @staticmethod
    def _to_float(text: str | None) -> float:
        if not text:
            return 0.0
        return float(text.replace(",", ""))

    @staticmethod
    def _search_int(pattern: re.Pattern[str], text: str, default: int = 0) -> int:
        m = pattern.search(text)
        return int(m.group("count" if "count" in pattern.groupindex else 1)) if m else default


    @staticmethod
    def _search_float(pattern: re.Pattern[str], text: str, default: float = 0.0) -> float:
        m = pattern.search(text)
        # Убедимся, что используем именованную группу 'amount', если она есть
        group_name = "amount" if "amount" in pattern.groupindex else 1
        return TournamentSummaryParser._to_float(m.group(group_name)) if m else default

    @staticmethod
    def _search_datetime(pattern: re.Pattern[str], text: str) -> Optional[datetime]:
        m = pattern.search(text)
        if not m:
            return None
        raw = m.group("ts").strip()
        # Поддерживаемые форматы даты и времени
        # Порядок важен: сначала более специфичные или часто встречающиеся
        formats_to_try = (
            "%Y/%m/%d %H:%M:%S",  # 2025/05/01 18:34:07
            "%Y-%m-%d %H:%M:%S",  # 2025-05-01 18:34:07
            "%d/%m/%Y %H:%M:%S",  # 01/05/2025 18:34:07
            "%m/%d/%Y %H:%M:%S",  # 05/01/2025 18:34:07
            # Можно добавить другие форматы, если они встречаются
        )
        for fmt in formats_to_try:
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        try:  # optional graceful fallback using dateutil
            from dateutil import parser as _dt_parser  # type: ignore

            return _dt_parser.parse(raw)
        except ImportError: # Если dateutil не установлен
            logger.warning("Модуль python-dateutil не найден. Парсинг дат может быть ограничен.")
            return None
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Не удалось распарсить дату '{raw}' с помощью dateutil: {e}")
            return None

    # ────────────────────────────────────────────────────────────────────
    # Domain‑specific helpers
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_base_payout(place: int, buy_in: float) -> float:
        """Фикс‑пэйаут за топ‑3 (иначе 0)."""
        if place == 1:
            return 4 * buy_in
        if place == 2:
            return 3 * buy_in
        if place == 3:
            return 2 * buy_in
        return 0.0

    # .................................................................

    @staticmethod
    def _calculate_large_knockouts(bounty: float, buy_in: float, players: int = 9) -> tuple[int, int, int, int, int]:
        """Возвращает количество нокаутов х2, х10, х100, х1000, х10000.

        Алгоритм: начинаем с самого крупного (10k) и по убыванию; каждая
        «выкупленная» категория вычитается из *bounty*.
        Макс. нокаутов любого класса за турнир — (игроков - 1).
        """
        # Гарантируем, что players не меньше 1, чтобы players - 1 было не отрицательным
        # Это важно, если players было установлено в 0 или меньше по какой-то причине
        # (хотя основная логика парсинга должна это предотвращать).
        max_possible_kos = max(0, players - 1)


        def _extract(cnt_bounty: float, multiplier: int) -> tuple[int, float]:
            if buy_in <= 0: # Если бай-ин 0 или отрицательный, нокауты невозможны
                return 0, cnt_bounty
            one_price = buy_in * multiplier
            if one_price == 0: # Избегаем деления на ноль, если buy_in * multiplier = 0
                return 0, cnt_bounty
            
            # Количество нокаутов не может быть больше, чем (количество игроков - 1)
            qty = min(int(cnt_bounty // one_price), max_possible_kos)
            return qty, cnt_bounty - qty * one_price

        x10k, remainder = _extract(bounty, 10_000)
        x1k, remainder = _extract(remainder, 1_000)
        x100, remainder = _extract(remainder, 100)
        x10, remainder = _extract(remainder, 10)
        x2, _ = _extract(remainder, 2) # Остаток от x2 нас не интересует для других категорий
        return x2, x10, x100, x1k, x10k

    # ------------------------------------------------------------------

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TournamentSummaryParser hero='{self.hero_name}'>"
