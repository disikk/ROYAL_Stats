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
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

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
        if not 1 <= self.finish_place <= self.players:
            raise ValueError("finish_place out of bounds")

    # ---------------------------------------------------------------------
    # Convenience helpers
    # ---------------------------------------------------------------------

    @property
    def normalized_finish_place(self) -> int:
        """Место, нормированное к диапазону 1–9 (требование ТЗ)."""
        # ceil(place / players * 9)
        from math import ceil

        return min(max(ceil(self.finish_place / self.players * 9), 1), 9)

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
    _PLAYERS_RE = re.compile(r"Players\s*:.*?(?P<count>\d+)")
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
        players = self._search_int(self._PLAYERS_RE, text, default=9)
        start_time = self._search_datetime(self._START_RE, text)

        # Hero section ── на GG бывает блок вида «25th : Hero … $16.37»
        hero_block_match = None
        for match in re.finditer(
            rf"(?P<place>\d+)(?:st|nd|rd|th) :\s*{re.escape(self.hero_name)}[\s\S]*?\$(?P<prize>[\d,.]+)",
            text,
        ):
            hero_block_match = match  # берём последний (финальный) блок

        if hero_block_match is None:
            # fallback – взять первый встреченный «X place … $Y»
            hero_block_match = self._FINISH_RE.search(text)
        if hero_block_match is None:
            raise ValueError("Cannot locate Hero finish block in TS file")

        finish_place = int(hero_block_match.group("place"))
        prize_total = self._to_float(hero_block_match.group("prize"))

        # ----------------------------------------------------------------------------
        # Ключевая логика: отделяем гарантированный пэйаут (1–3 места) от баунти
        # ----------------------------------------------------------------------------
        base_payout = self._compute_base_payout(finish_place, buy_in)
        bounty_total = max(prize_total - base_payout, 0.0)

        # Считаем крупные нокауты
        k2, k10, k100, k1k, k10k = self._calculate_large_knockouts(bounty_total, buy_in, players)

        return TournamentSummary(
            tournament_id=tournament_id,
            buy_in=buy_in,
            players=players,
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
        return int(m.group(1)) if m else default

    @staticmethod
    def _search_float(pattern: re.Pattern[str], text: str, default: float = 0.0) -> float:
        m = pattern.search(text)
        return TournamentSummaryParser._to_float(m.group(1)) if m else default

    @staticmethod
    def _search_datetime(pattern: re.Pattern[str], text: str) -> Optional[datetime]:
        m = pattern.search(text)
        if not m:
            return None
        raw = m.group("ts").strip()
        for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        try:  # optional graceful fallback
            from dateutil import parser as _dt_parser  # type: ignore

            return _dt_parser.parse(raw)
        except Exception:  # pylint: disable=broad-except
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

        def _extract(cnt_bounty: float, multiplier: int) -> tuple[int, float]:
            one_price = buy_in * multiplier
            if one_price == 0:
                return 0, cnt_bounty
            qty = min(int(cnt_bounty // one_price), players - 1)
            return qty, cnt_bounty - qty * one_price

        x10k, remainder = _extract(bounty, 10_000)
        x1k, remainder = _extract(remainder, 1_000)
        x100, remainder = _extract(remainder, 100)
        x10, remainder = _extract(remainder, 10)
        x2, _ = _extract(remainder, 2)
        return x2, x10, x100, x1k, x10k

    # ------------------------------------------------------------------

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TournamentSummaryParser hero='{self.hero_name}'>"