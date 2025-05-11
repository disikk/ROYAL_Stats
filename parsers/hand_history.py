#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Парсер файлов истории рук (hand history) для покерного трекера ROYAL_Stats.
Извлекает информацию о раздачах, стеках игроков и накаутах.
Использует проверенный алгоритм обнаружения накаутов, который корректно
обрабатывает мультипоты, сайд-поты и дележки.
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional


class Pot:
    """
    Класс для представления банка (основного или сайд-пота).
    
    Attributes:
        size: Размер банка
        eligible: Множество игроков, имеющих право на этот банк
        winners: Множество игроков, которые выиграли часть этого банка
    """
    __slots__ = ('size', 'eligible', 'winners')
    
    def __init__(self, size: int, eligible: Set[str]):
        self.size = size
        self.eligible: Set[str] = eligible
        self.winners: Set[str] = set()


class Hand:
    """
    Класс для представления одной покерной раздачи.
    
    Attributes:
        seats: Словарь стеков игроков в начале раздачи
        contrib: Словарь с итоговыми вложениями каждого игрока в банк
        collects: Словарь с выигрышами каждого игрока из банка
        pots: Список всех банков (основной и сайд-поты)
    """
    __slots__ = ('seats', 'contrib', 'collects', 'pots')
    
    def __init__(self, seats: Dict[str, int], contrib: Dict[str, int],
                 collects: Dict[str, int], pots: List[Pot]):
        self.seats = seats        # стеки в начале
        self.contrib = contrib    # итоговые ставки игроков
        self.collects = collects  # выигрыши игроков
        self.pots = pots          # банки с победителями


class HandHistoryParser:
    """
    Парсер файлов истории рук для покерного трекера ROYAL_Stats.
    Использует проверенный алгоритм для определения накаутов.
    """

    def __init__(self):
        # Регулярные выражения для извлечения данных
        self.re_tournament_id = re.compile(r'Tournament #(\d+)')
        self.re_hand_start = re.compile(r'^Poker Hand #')
        self.re_seat = re.compile(r'^Seat \d+: ([^()]+?) \(([-\d,]+) in chips\)')
        self.re_action = re.compile(
            r'^(?P<p>[^:]+): (?P<act>posts|bets|calls|raises|all-in|checks|folds)\b(?:.*?)(?P<amt>[\d,]+)?'
        )
        self.re_raise_to = re.compile(r'raises [\d,]+ to ([\d,]+)')
        self.re_uncalled = re.compile(r'^Uncalled bet \(([\d,]+)\) returned to ([^\n]+)')
        self.re_collected = re.compile(r'^([^:]+) collected ([\d,]+) from pot')
        self.re_summary = re.compile(r'^\*\*\* SUMMARY \*\*\*')
        self.re_total_pot = re.compile(r'Total pot (\d+)')

    def parse_file(self, file_path: str) -> Dict:
        """
        Анализирует файл истории рук и возвращает информацию о накаутах.
        
        Args:
            file_path: Путь к файлу истории рук
            
        Returns:
            Словарь с результатами парсинга
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        # Начальная структура результата
        result = {
            'tournament_id': None,
            'hands_count': 0,
            'knockouts': [],  # Список накаутов Hero
            'hands': []       # Детальная информация по раздачам
        }
        
        # Извлекаем ID турнира из файла
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            tournament_match = self.re_tournament_id.search(content)
            if tournament_match:
                result['tournament_id'] = tournament_match.group(1)
        
        # Анализируем раздачи с помощью алгоритма экспертов
        hands = self._parse_file(Path(file_path))
        result['hands_count'] = len(hands)
        
        # Для каждой раздачи определяем, были ли накауты
        for idx, hand in enumerate(hands):
            next_hand = hands[idx+1] if idx+1 < len(hands) else None
            eliminated = self._eliminated(hand, next_hand)
            
            # Преобразуем информацию о раздаче в наш формат для совместимости
            hand_info = {
                'hand_id': f"hand-{idx}",  # У нас нет прямого ID раздачи
                'players': {},
                'knockouts_by_hero': []
            }
            
            # Добавляем информацию об игроках
            for player, stack in hand.seats.items():
                hand_info['players'][player] = {
                    'initial_stack': stack,
                    'final_stack': None,  # Будет заполнено ниже
                    'collected': hand.collects.get(player, 0)
                }
                
                # Если игрок что-то собрал, обновляем его конечный стек
                if player in hand.collects:
                    hand_info['players'][player]['final_stack'] = stack + hand.collects[player]
            
            # Проверяем, совершил ли Hero накаут в этой раздаче
            ko_count = self._ko_in_hand(hand, eliminated, 'Hero')
            if ko_count > 0:
                # Добавляем информацию о каждом накауте
                for player in eliminated:
                    # Проверяем, был ли этот игрок накаутнут Hero
                    for pot in hand.pots:
                        if player in pot.eligible and 'Hero' in pot.winners:
                            # Накаут был совершен Hero
                            # Добавляем в список накаутов Hero
                            knockout_info = {
                                'player': player,
                                'amount': hand.collects.get('Hero', 0),
                                'multi_knockout': len(pot.winners) > 1
                            }
                            hand_info['knockouts_by_hero'].append(knockout_info)
                            
                            # Также добавляем в общий список накаутов
                            result['knockouts'].append({
                                'hand_id': hand_info['hand_id'],
                                'knocked_out_player': player,
                                'pot_size': hand.collects.get('Hero', 0),
                                'multi_knockout': len(pot.winners) > 1
                            })
            
            # Добавляем информацию о раздаче в результат
            result['hands'].append(hand_info)
            
        return result

    def _parse_file(self, path: Path) -> List[Hand]:
        """
        Разбирает файл истории рук на отдельные раздачи.
        Реализация из оригинального алгоритма экспертов.
        
        Args:
            path: Путь к файлу
            
        Returns:
            Список объектов Hand
        """
        lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
        hands: List[Hand] = []
        i = 0
        while i < len(lines):
            if self.re_hand_start.match(lines[i]):
                i, h = self._parse_hand(lines, i)
                hands.append(h)
            else:
                i += 1
        return hands

    def _parse_hand(self, lines: List[str], idx: int) -> Tuple[int, Hand]:
        """
        Парсит одну раздачу, начиная с указанной строки.
        Реализация из оригинального алгоритма экспертов.
        
        Args:
            lines: Список строк файла
            idx: Индекс строки, с которой начинается раздача
            
        Returns:
            Кортеж (новый индекс, объект Hand)
        """
        seats: Dict[str, int] = {}
        idx += 1  # переходим к следующей строке после заголовка
        
        # Парсим строки с местами игроков
        while idx < len(lines) and not lines[idx].startswith('*** HOLE'):
            m = self.re_seat.match(lines[idx])
            if m:
                name, chips = m.groups()
                seats[self._name(name)] = self._chip(chips)
            idx += 1
            
        # Пропускаем до действий
        while idx < len(lines) and not lines[idx].startswith('*** HOLE'):
            idx += 1
        while idx < len(lines) and not lines[idx].startswith('*** SHOWDOWN') and \
              not lines[idx].startswith('*** SUMMARY'):
            idx += 1
            
        # Парсим блок действий
        idx, contrib = self._parse_actions(lines, idx)
        
        # Ищем выигрыши до SUMMARY
        collects: Dict[str, int] = {}
        collect_idx_search = idx
        while collect_idx_search < len(lines) and not lines[collect_idx_search].startswith('*** SUMMARY'):
            line = lines[collect_idx_search]
            m = self.re_collected.match(line)
            if m:
                pl, amt = m.groups()
                collects[self._name(pl)] = collects.get(self._name(pl), 0) + self._chip(amt)
            collect_idx_search += 1
            
        # Пропускаем блок SUMMARY до конца раздачи (пустая строка)
        while idx < len(lines) and lines[idx].strip():
            idx += 1
        while idx < len(lines) and not lines[idx].strip():
            idx += 1
            
        # Строим сайд-поты и назначаем победителей
        pots = self._build_pots(contrib)
        self._assign_winners(pots, collects)
        
        return idx, Hand(seats, contrib, collects, pots)

    def _parse_actions(self, lines: List[str], idx: int) -> Tuple[int, Dict[str, int]]:
        """
        Парсит строки с действиями игроков до SUMMARY.
        Реализация из оригинального алгоритма экспертов.
        
        Args:
            lines: Список строк файла
            idx: Индекс строки, с которой начинаются действия
            
        Returns:
            Кортеж (новый индекс, вклады игроков)
        """
        contrib: Dict[str, int] = {}
        committed: Dict[str, int] = {}
        
        while idx < len(lines) and not self.re_summary.match(lines[idx]):
            line = lines[idx]
            # Возврат несравненных ставок
            m_unc = self.re_uncalled.match(line)
            if m_unc:
                amt, pl = m_unc.groups()
                pl = self._name(pl)
                val = self._chip(amt)
                contrib[pl] = contrib.get(pl, 0) - val
                committed[pl] = committed.get(pl, 0) - val
                idx += 1
                continue

            m = self.re_action.match(line)
            if m:
                pl, act, amt_s = m.groups()
                pl = self._name(pl)
                amt = self._chip(amt_s)
                if act in ('posts', 'bets', 'calls', 'all-in'):
                    contrib[pl] = contrib.get(pl, 0) + amt
                    committed[pl] = committed.get(pl, 0) + amt
                elif act == 'raises':
                    # Нужна сумма "to X"
                    to_m = self.re_raise_to.search(line)
                    if not to_m:
                        idx += 1
                        continue
                    total_to = self._chip(to_m.group(1))
                    prev = committed.get(pl, 0)
                    diff = total_to - prev
                    contrib[pl] = contrib.get(pl, 0) + diff
                    committed[pl] = total_to
            idx += 1
            
        return idx, contrib

    def _build_pots(self, contrib: Dict[str, int]) -> List[Pot]:
        """
        Строит список банков на основе вкладов игроков.
        Реализация из оригинального алгоритма экспертов.
        
        Args:
            contrib: Словарь вкладов игроков
            
        Returns:
            Список банков
        """
        pots: List[Pot] = []
        if not contrib:
            return pots
            
        # Уникальные положительные вклады, отсортированные по возрастанию
        levels = sorted({v for v in contrib.values() if v > 0})
        prev = 0
        
        for lv in levels:
            elig = {p for p, a in contrib.items() if a >= lv}
            layer = lv - prev
            size = layer * len(elig)
            pots.append(Pot(size, elig))
            prev = lv
            
        return pots

    def _assign_winners(self, pots: List[Pot], collects: Dict[str, int]):
        """
        Распределяет выигрыши по банкам и отмечает победителей.
        Реализация из оригинального алгоритма экспертов.
        
        Args:
            pots: Список банков
            collects: Словарь выигрышей игроков
        """
        remaining = collects.copy()
        
        # Обрабатываем сначала сайд-поты (с наименьшим набором игроков)
        for pot in sorted(pots, key=lambda p: len(p.eligible)):
            pot_left = pot.size
            
            # Игроки, имеющие право на банк и с положительным остатком
            for p in pot.eligible:
                r = remaining.get(p, 0)
                if r <= 0 or pot_left <= 0:
                    continue
                take = min(r, pot_left)
                if take > 0:
                    pot.winners.add(p)
                    remaining[p] -= take
                    pot_left -= take
                    
            # Если остались фишки, приписываем любому имеющему право
            if pot_left > 0 and pot.eligible:
                p = next(iter(pot.eligible))
                pot.winners.add(p)

    def _eliminated(self, curr: Hand, nxt: Optional[Hand]) -> List[str]:
        """
        Определяет игроков, которые выбыли после текущей раздачи.
        Реализация из оригинального алгоритма экспертов.
        
        Args:
            curr: Текущая раздача
            nxt: Следующая раздача (или None, если это последняя)
            
        Returns:
            Список выбывших игроков
        """
        if nxt is None:
            return []
        return [p for p in curr.seats if p not in nxt.seats]

    def _ko_in_hand(self, hand: Hand, eliminated: List[str], hero: str) -> int:
        """
        Определяет, сколько накаутов совершил hero в данной раздаче.
        Реализация из оригинального алгоритма экспертов.
        
        Args:
            hand: Раздача
            eliminated: Список выбывших игроков
            hero: Имя игрока героя (обычно 'Hero')
            
        Returns:
            Количество накаутов
        """
        if not eliminated:
            return 0
            
        # Сопоставляем выбывшего игрока с банком
        # (наименьший банк, на который распространяется его вклад)
        pot_order = sorted(hand.pots, key=lambda p: len(p.eligible), reverse=False)
        player_pot: Dict[str, Pot] = {}
        
        for pot in pot_order:
            for p in pot.eligible:
                player_pot.setdefault(p, pot)
                
        kos = 0
        for bust in eliminated:
            pot = player_pot.get(bust)
            if pot and hero in pot.winners:
                kos += 1
                
        return kos

    def _chip(self, s: str) -> int:
        """Преобразует строку с числом фишек в целое число."""
        return int(s.replace(',', '')) if s else 0

    def _name(self, s: str) -> str:
        """Очищает имя игрока от лишних пробелов."""
        return s.strip()

    def get_knockouts_from_multiple_files(self, file_paths: List[str]) -> List[Dict]:
        """
        Анализирует несколько файлов истории рук и возвращает список всех накаутов.
        
        Args:
            file_paths: Список путей к файлам
            
        Returns:
            Список накаутов
        """
        all_knockouts = []
        
        for file_path in file_paths:
            try:
                result = self.parse_file(file_path)
                all_knockouts.extend(result.get('knockouts', []))
            except Exception as e:
                print(f"Ошибка при парсинге файла {file_path}: {e}")
                
        return all_knockouts


# Пример использования
if __name__ == "__main__":
    parser = HandHistoryParser()
    
    # Проверка аргументов командной строки
    import sys
    if len(sys.argv) < 2:
        print("Использование: python hand_history.py [путь к файлу истории рук]")
        sys.exit(1)
        
    # Анализ файла
    file_path = sys.argv[1]
    try:
        result = parser.parse_file(file_path)
        print(f"Турнир ID: {result['tournament_id']}")
        print(f"Количество раздач: {result['hands_count']}")
        print(f"Количество накаутов: {len(result['knockouts'])}")
        
        for knockout in result['knockouts']:
            if knockout.get('multi_knockout'):
                print(f"Hand #{knockout['hand_id']}: Hero выбил игрока {knockout['knocked_out_player']} "
                      f"в дележке с другими игроками (банк: {knockout['pot_size']})")
            else:
                print(f"Hand #{knockout['hand_id']}: Hero выбил игрока {knockout['knocked_out_player']} "
                      f"(банк: {knockout['pot_size']})")
    except Exception as e:
        print(f"Ошибка при анализе файла: {e}")