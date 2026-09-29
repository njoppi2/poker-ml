"""Compile the research Leduc variant with one or two public-card streets.

This deliberately uses the research rules, not the websocket game. In particular,
bets are cumulative across streets and a forced '-' action aligns the flop actor.
It is not OpenSpiel's standard limit Leduc. Utilities are net ante units (one BB
for the historical 1/1 blinds); card suits are irrelevant. ``public_cards=1``
preserves the original game; ``public_cards=2`` reveals a turn card and adds a
third betting phase.
"""
from collections import Counter
from dataclasses import dataclass
from itertools import combinations, permutations

from game_engine.ia.algorithms.classes import Card
from game_engine.ia.algorithms.functions import get_possible_actions, set_bet_value


@dataclass(frozen=True)
class InfoSet:
    key: str
    player: int
    actions: tuple[int, ...]


@dataclass(frozen=True)
class PublicNode:
    player: int
    children: tuple[int, ...] = ()
    infos: tuple[int, ...] = ()  # Information-set id for each hidden deal.
    payoffs: tuple[float, ...] = ()  # Terminal utility for player zero.
    action_kinds: tuple[str, ...] = ()  # Distinguish calls from raises of the same numeric size.


def _hand_strength(private: int, board: tuple[int, ...]) -> tuple[tuple[int, int], ...]:
    """Rank a Leduc hand by matching ranks, then rank kickers."""
    counts = Counter((private, *board))
    return tuple(sorted(((count, rank) for rank, count in counts.items()), reverse=True))


def showdown(deal: tuple[int, ...]) -> int:
    """Compare two private cards with one or more public cards.

    A pair beats a high-card hand; ties are broken by pair rank and then
    remaining ranks. With one public card this preserves the original rules.
    """
    if len(deal) < 3:
        raise ValueError("a showdown deal needs two private cards and a public card")
    strength_a = _hand_strength(deal[0], tuple(deal[2:]))
    strength_b = _hand_strength(deal[1], tuple(deal[2:]))
    return (strength_a > strength_b) - (strength_a < strength_b)


class LeducGame:
    def __deepcopy__(self, memo):
        # Compiled game data is read-only; OpenSpiel clones states frequently.
        return self

    def __init__(self, chips: int = 12, bet_sizes: tuple[int, ...] | None = None,
                 public_cards: int = 1, ranks: int = 3):
        if isinstance(chips, bool) or not isinstance(chips, int) or not 2 <= chips <= 14:
            raise ValueError("chips must be an integer from 2 to 14 (exact evaluation is bounded)")
        if bet_sizes is None:
            bet_sizes = tuple(range(2, chips + 1))
        if (not isinstance(bet_sizes, tuple) or not bet_sizes or chips not in bet_sizes or
                any(isinstance(bet, bool) or not isinstance(bet, int) or not 2 <= bet <= chips
                    for bet in bet_sizes) or tuple(sorted(set(bet_sizes))) != bet_sizes):
            raise ValueError("bet_sizes must be sorted unique legal bets including all-in")
        self.chips = chips
        self.bet_sizes = bet_sizes
        if isinstance(ranks, bool) or not isinstance(ranks, int) or not 3 <= ranks <= 13:
            raise ValueError("ranks must be an integer from 3 to 13")
        self.ranks = ranks
        self.suits = 0
        self.rank_symbols = "23456789TJQKA"[-ranks:]
        if (isinstance(public_cards, bool) or not isinstance(public_cards, int)
                or public_cards not in (1, 2)):
            raise ValueError("public_cards must be 1 or 2")
        self.public_cards = public_cards
        self.phases = ("preflop", "flop") if public_cards == 1 else ("preflop", "flop", "turn")
        # Enumerate physical cards, then merge indistinguishable rank deals.
        deal_size = 2 + public_cards
        counts = Counter(tuple(card // 2 for card in cards)
                         for cards in permutations(range(2 * ranks), deal_size))
        self.deals = tuple(sorted(counts))
        self.chance = tuple(counts[deal] / sum(counts.values()) for deal in self.deals)
        self.nodes: list[PublicNode] = []
        self.infosets: list[InfoSet] = []
        self.info_by_key: dict[str, int] = {}
        self.max_depth = 0
        self._actions = [{"name": "k", "value": 0}] + [
            {"name": f"r{i}", "value": i} for i in bet_sizes
        ]
        initial = (chips - 1, 1, 1, False)
        self._build("", (initial, initial), self.phases[0], 0, 0)

    def _build(self, history, players, phase, actor, depth):
        self.max_depth = max(depth, self.max_depth)
        index = len(self.nodes)
        self.nodes.append(PublicNode(-1))
        actions, reward, next_phase = get_possible_actions(
            history, [Card.Q, Card.K, Card.A], actor, 1 - actor,
            players, phase, self._actions, 1, self.chips, False,
            final_phase=self.phases[-1],
        )
        if actions is None:
            if players[actor][2] > players[1 - actor][2]:
                # The preceding actor folded; unmatched chips are returned.
                payoffs = (float(reward if actor == 0 else -reward),) * len(self.deals)
            else:
                payoffs = tuple(float(players[0][2] * showdown(deal)) for deal in self.deals)
            self.nodes[index] = PublicNode(-1, payoffs=payoffs)
            return index

        if next_phase:
            phase = self.phases[self.phases.index(phase) + 1]
        history += "/" if next_phase else ""
        action_codes = tuple(a["value"] for a in actions)
        info_ids = []
        for deal in self.deals:
            key = history + ":|" + self.rank_symbols[deal[actor]]
            revealed_cards = self.phases.index(phase)
            if revealed_cards:
                key += "/" + "".join(self.rank_symbols[rank]
                                       for rank in deal[2:2 + revealed_cards])
            if key not in self.info_by_key:
                self.info_by_key[key] = len(self.infosets)
                self.infosets.append(InfoSet(key, actor, action_codes))
            info_ids.append(self.info_by_key[key])
        children = []
        action_kinds = []
        for action in actions:
            updated, label = set_bet_value(actor, players, action["value"], next_phase, False, actions)
            # Historical history labels use 'k' for both check and fold.
            # Classify from the pre-action commitments instead.
            value = action["value"]
            if len(actions) == 1:
                kind = "-"
            elif value == 0:
                kind = "f" if players[actor][2] < players[1 - actor][2] else "k"
            else:
                kind = "c" if value == players[1 - actor][2] else "r"
            action_kinds.append(kind)
            children.append(self._build(history + label, updated, phase, 1 - actor, depth + 1))
        self.nodes[index] = PublicNode(actor, tuple(children), tuple(info_ids), action_kinds=tuple(action_kinds))
        return index

    def uniform_policy(self):
        return [[1.0 / len(info.actions)] * len(info.actions) for info in self.infosets]


class MiniHoldemGame:
    """Exact tiny Hold'em-style game: two private cards and a three-card flop.

    The deck has six ranks (9 through A) and two suits. The flop is dealt as
    one public event and there are preflop and flop betting phases. Two suits
    are enough to make flushes possible while keeping the six-rank game's
    166,320 unordered physical deals enumerable for exact evaluation.
    """

    suits = 2
    public_cards = 3
    suit_symbols = "cd"
    phases = ("preflop", "flop")

    def __deepcopy__(self, memo):
        return self

    def __init__(self, chips: int = 2, bet_sizes: tuple[int, ...] | None = None,
                 ranks: int = 6):
        if isinstance(chips, bool) or not isinstance(chips, int) or not 2 <= chips <= 14:
            raise ValueError("chips must be an integer from 2 to 14")
        if bet_sizes is None:
            bet_sizes = tuple(range(2, chips + 1))
        if (not isinstance(bet_sizes, tuple) or not bet_sizes or chips not in bet_sizes or
                any(isinstance(bet, bool) or not isinstance(bet, int) or not 2 <= bet <= chips
                    for bet in bet_sizes) or tuple(sorted(set(bet_sizes))) != bet_sizes):
            raise ValueError("bet_sizes must be sorted unique legal bets including all-in")
        self.chips, self.bet_sizes = chips, bet_sizes
        if isinstance(ranks, bool) or not isinstance(ranks, int) or ranks not in (5, 6):
            raise ValueError("MiniHoldemGame supports five or six ranks for exact enumeration")
        self.ranks = ranks
        self.rank_symbols = "23456789TJQKA"[-ranks:]
        deck = range(self.ranks * self.suits)
        deals = []
        for hand0 in combinations(deck, 2):
            after0 = [card for card in deck if card not in hand0]
            for hand1 in combinations(after0, 2):
                after1 = [card for card in after0 if card not in hand1]
                for board in combinations(after1, 3):
                    deals.append((*hand0, *hand1, *board))
        self.deals = tuple(deals)
        self.chance = (1.0 / len(self.deals),) * len(self.deals)
        self.nodes: list[PublicNode] = []
        self.infosets: list[InfoSet] = []
        self.info_by_key: dict[str, int] = {}
        self.max_depth = 0
        self._actions = [{"name": "k", "value": 0}] + [
            {"name": f"r{bet}", "value": bet} for bet in bet_sizes
        ]
        initial = (chips - 1, 1, 1, False)
        self._build("", (initial, initial), "preflop", 0, 0)

    def _card_label(self, card: int) -> str:
        return self.rank_symbols[card // self.suits] + self.suit_symbols[card % self.suits]

    @staticmethod
    def _five_card_strength(cards: tuple[int, ...]) -> tuple[int, ...]:
        ranks = [card // 2 for card in cards]
        suits = [card % 2 for card in cards]
        groups = sorted(((ranks.count(rank), rank) for rank in set(ranks)), reverse=True)
        distinct = sorted(set(ranks))
        straight_high = distinct[-1] if len(distinct) == 5 and distinct[-1] - distinct[0] == 4 else None
        flush = len(set(suits)) == 1
        if flush and straight_high is not None:
            return (8, straight_high)
        if groups[0][0] == 4:
            return (7, groups[0][1], groups[1][1])
        if groups[0][0] == 3 and groups[1][0] == 2:
            return (6, groups[0][1], groups[1][1])
        descending = tuple(sorted(ranks, reverse=True))
        if flush:
            return (5, *descending)
        if straight_high is not None:
            return (4, straight_high)
        if groups[0][0] == 3:
            return (3, groups[0][1], *(rank for rank in descending if rank != groups[0][1]))
        pairs = sorted((rank for count, rank in groups if count == 2), reverse=True)
        if len(pairs) == 2:
            kicker = next(rank for rank in descending if rank not in pairs)
            return (2, *pairs, kicker)
        if len(pairs) == 1:
            return (1, pairs[0], *(rank for rank in descending if rank != pairs[0]))
        return (0, *descending)

    def _showdown(self, deal: tuple[int, ...]) -> int:
        board = tuple(deal[4:7])
        hand0, hand1 = (*deal[0:2], *board), (*deal[2:4], *board)
        strength0, strength1 = self._five_card_strength(hand0), self._five_card_strength(hand1)
        return (strength0 > strength1) - (strength0 < strength1)

    def _build(self, history, players, phase, actor, depth):
        self.max_depth = max(depth, self.max_depth)
        index = len(self.nodes)
        self.nodes.append(PublicNode(-1))
        actions, reward, next_phase = get_possible_actions(
            history, [Card.Q, Card.K, Card.A], actor, 1 - actor,
            players, phase, self._actions, 1, self.chips, False,
            final_phase="flop",
        )
        if actions is None:
            if players[actor][2] > players[1 - actor][2]:
                payoffs = (float(reward if actor == 0 else -reward),) * len(self.deals)
            else:
                payoffs = tuple(float(players[0][2] * self._showdown(deal)) for deal in self.deals)
            self.nodes[index] = PublicNode(-1, payoffs=payoffs)
            return index

        if next_phase:
            phase = "flop"
        history += "/" if next_phase else ""
        action_codes = tuple(action["value"] for action in actions)
        info_ids = []
        for deal in self.deals:
            hand_offset = 0 if actor == 0 else 2
            private = "".join(self._card_label(card) for card in deal[hand_offset:hand_offset + 2])
            key = history + ":|" + private
            if phase == "flop":
                key += "/" + "".join(self._card_label(card) for card in deal[4:7])
            if key not in self.info_by_key:
                self.info_by_key[key] = len(self.infosets)
                self.infosets.append(InfoSet(key, actor, action_codes))
            info_ids.append(self.info_by_key[key])

        children, action_kinds = [], []
        for action in actions:
            updated, label = set_bet_value(actor, players, action["value"], next_phase, False, actions)
            value = action["value"]
            if len(actions) == 1:
                kind = "-"
            elif value == 0:
                kind = "f" if players[actor][2] < players[1 - actor][2] else "k"
            else:
                kind = "c" if value == players[1 - actor][2] else "r"
            action_kinds.append(kind)
            children.append(self._build(history + label, updated, phase, 1 - actor, depth + 1))
        self.nodes[index] = PublicNode(actor, tuple(children), tuple(info_ids),
                                       action_kinds=tuple(action_kinds))
        return index

    def uniform_policy(self):
        return [[1.0 / len(info.actions)] * len(info.actions) for info in self.infosets]
