"""Compile the historical equal-ante, integer-bet Leduc variant once.

This deliberately uses the research rules, not the websocket game. In particular,
bets are cumulative across streets and a forced '-' action aligns the flop actor.
It is not OpenSpiel's standard limit Leduc. Utilities are net ante units (one BB
for the historical 1/1 blinds); card suits are irrelevant.
"""
from collections import Counter
from dataclasses import dataclass
from itertools import permutations

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


def showdown(deal: tuple[int, int, int]) -> int:
    a, b, board = deal
    strength_a = (a == board, a)
    strength_b = (b == board, b)
    return (strength_a > strength_b) - (strength_a < strength_b)


class LeducGame:
    def __deepcopy__(self, memo):
        # Compiled game data is read-only; OpenSpiel clones states frequently.
        return self

    def __init__(self, chips: int = 12):
        if isinstance(chips, bool) or not isinstance(chips, int) or not 2 <= chips <= 12:
            raise ValueError("chips must be an integer from 2 to 12 (exact evaluation is bounded)")
        self.chips = chips
        # Enumerate physical cards, then merge indistinguishable rank deals.
        counts = Counter(tuple(card // 2 for card in cards) for cards in permutations(range(6), 3))
        self.deals = tuple(sorted(counts))
        self.chance = tuple(counts[deal] / 120 for deal in self.deals)
        self.nodes: list[PublicNode] = []
        self.infosets: list[InfoSet] = []
        self.info_by_key: dict[str, int] = {}
        self.max_depth = 0
        self._actions = [{"name": "k", "value": 0}] + [
            {"name": f"r{i}", "value": i} for i in range(2, chips + 1)
        ]
        initial = (chips - 1, 1, 1, False)
        self._build("", (initial, initial), "preflop", 0, 0)

    def _build(self, history, players, phase, actor, depth):
        self.max_depth = max(depth, self.max_depth)
        index = len(self.nodes)
        self.nodes.append(PublicNode(-1))
        actions, reward, next_phase = get_possible_actions(
            history, [Card.Q, Card.K, Card.A], actor, 1 - actor,
            players, phase, self._actions, 1, self.chips, False,
        )
        if actions is None:
            if players[actor][2] > players[1 - actor][2]:
                # The preceding actor folded; unmatched chips are returned.
                payoffs = (float(reward if actor == 0 else -reward),) * len(self.deals)
            else:
                payoffs = tuple(float(players[0][2] * showdown(deal)) for deal in self.deals)
            self.nodes[index] = PublicNode(-1, payoffs=payoffs)
            return index

        phase = "flop" if next_phase else phase
        history += "/" if next_phase else ""
        action_codes = tuple(a["value"] for a in actions)
        info_ids = []
        for deal in self.deals:
            key = history + ":|" + "QKA"[deal[actor]]
            if phase == "flop":
                key += "/" + "QKA"[deal[2]]
            if key not in self.info_by_key:
                self.info_by_key[key] = len(self.infosets)
                self.infosets.append(InfoSet(key, actor, action_codes))
            info_ids.append(self.info_by_key[key])
        children = []
        for action in actions:
            updated, label = set_bet_value(actor, players, action["value"], next_phase, False, actions)
            children.append(self._build(history + label, updated, phase, 1 - actor, depth + 1))
        self.nodes[index] = PublicNode(actor, tuple(children), tuple(info_ids))
        return index

    def uniform_policy(self):
        return [[1.0 / len(info.actions)] * len(info.actions) for info in self.infosets]
