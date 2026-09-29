"""Sampled CFR for a configurable Hold'em-style research game.

Unlike ``MiniHoldemGame``, this game deals a complete five-card board (flop,
turn, river) and does not enumerate all chance outcomes into every tree node.
Each iteration samples one physical deal, which makes the memory cost depend on
the public betting tree rather than on millions of private-card/board tuples.
"""
from __future__ import annotations

import argparse
import json
import random
import time
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from game_engine.ia.algorithms.classes import Card
from game_engine.ia.algorithms.functions import get_possible_actions, set_bet_value

from .evaluate import evaluate
from .game import InfoSet, PublicNode
from .solver import normalize


@dataclass(frozen=True)
class SampledNode:
    player: int
    children: tuple[int, ...] = ()
    actions: tuple[int, ...] = ()
    history: str = ""
    phase: str = ""
    terminal: str = ""
    terminal_payoff: float = 0.0
    pot: float = 0.0
    action_kinds: tuple[str, ...] = ()


class SampledHoldemGame:
    """Two private cards, flop/turn/river, and a configurable research deck.

    The default 12-card deck has enough cards for two hole cards per player
    and a five-card board. The board is revealed 3+1+1 across betting streets.
    Rank/suit counts can grow to a standard 52-card deck without enumerating
    the resulting chance space.
    """

    ranks = 6
    suits = 2
    rank_symbols = "9TJQKA"
    suit_symbols = "cd"
    phases = ("preflop", "flop", "turn", "river")
    public_cards = 5

    def __init__(self, chips: int = 4, bet_sizes: tuple[int, ...] = (2, 4),
                 ranks: int = 6, suits: int = 2):
        if isinstance(chips, bool) or not isinstance(chips, int) or not 2 <= chips <= 14:
            raise ValueError("chips must be an integer from 2 to 14")
        if isinstance(ranks, bool) or not isinstance(ranks, int) or not 5 <= ranks <= 13:
            raise ValueError("ranks must be an integer from 5 to 13")
        if isinstance(suits, bool) or not isinstance(suits, int) or suits not in (2, 4):
            raise ValueError("suits must be 2 or 4")
        if (not isinstance(bet_sizes, tuple) or not bet_sizes or chips not in bet_sizes
                or any(isinstance(bet, bool) or not isinstance(bet, int) or not 2 <= bet <= chips
                       for bet in bet_sizes)
                or tuple(sorted(set(bet_sizes))) != bet_sizes):
            raise ValueError("bet_sizes must be sorted unique legal bets including all-in")
        self.chips, self.bet_sizes = chips, bet_sizes
        self.ranks, self.suits = ranks, suits
        self.rank_symbols = "23456789TJQKA"[-ranks:]
        self.suit_symbols = "cdhs"[:suits]
        self._actions = [{"name": "k", "value": 0}] + [
            {"name": f"r{bet}", "value": bet} for bet in bet_sizes
        ]
        self.nodes: list[SampledNode] = []
        initial = (chips - 1, 1, 1, False)
        self._build("", (initial, initial), self.phases[0], 0)
        self.nodes = tuple(self.nodes)
        self.deals = ()
        self.chance = ()
        self.infosets: list[InfoSet] = []
        self.info_by_key: dict[str, int] = {}
        self.info_action_kinds: list[tuple[str, ...]] = []

    def _build(self, history, players, phase, actor):
        index = len(self.nodes)
        self.nodes.append(SampledNode(-1))
        actions, reward, next_phase = get_possible_actions(
            history, [Card.Q, Card.K, Card.A], actor, 1 - actor,
            players, phase, self._actions, 1, self.chips, False,
            final_phase=self.phases[-1],
        )
        if actions is None:
            if players[actor][2] > players[1 - actor][2]:
                payoff = float(reward if actor == 0 else -reward)
                self.nodes[index] = SampledNode(-1, terminal="fold", terminal_payoff=payoff)
            else:
                self.nodes[index] = SampledNode(-1, terminal="showdown", pot=float(players[0][2]))
            return index
        if next_phase:
            phase = self.phases[self.phases.index(phase) + 1]
        history += "/" if next_phase else ""
        children = []
        labels = []
        for action in actions:
            updated, label = set_bet_value(actor, players, action["value"], next_phase, False, actions)
            children.append(self._build(history + label, updated, phase, 1 - actor))
            labels.append(label)
        kinds = tuple("raise" if label.startswith("r") else label for label in labels)
        self.nodes[index] = SampledNode(actor, tuple(children),
                                        tuple(action["value"] for action in actions),
                                        history, phase, action_kinds=kinds)
        return index

    def sample_deal(self, rng: random.Random) -> tuple[int, ...]:
        """Sample a physical deal uniformly, canonicalizing unordered cards."""
        cards = rng.sample(range(self.ranks * self.suits), 9)
        hand0 = tuple(sorted(cards[:2]))
        hand1 = tuple(sorted(cards[2:4]))
        flop = tuple(sorted(cards[4:7]))
        return (*hand0, *hand1, *flop, cards[7], cards[8])

    def _card_label(self, card: int) -> str:
        return self.rank_symbols[card // self.suits] + self.suit_symbols[card % self.suits]

    def info_key(self, node: SampledNode, deal: tuple[int, ...]) -> str:
        hole_start = 0 if node.player == 0 else 2
        private = "".join(self._card_label(card) for card in deal[hole_start:hole_start + 2])
        visible = {"preflop": 0, "flop": 3, "turn": 4, "river": 5}[node.phase]
        board = "".join(self._card_label(card) for card in deal[4:4 + visible])
        return node.history + ":|" + private + ("/" + board if visible else "")

    def get_or_add_infoset(self, node: SampledNode, deal: tuple[int, ...]) -> int:
        key = self.info_key(node, deal)
        info = self.info_by_key.get(key)
        if info is None:
            info = len(self.infosets)
            self.info_by_key[key] = info
            self.infosets.append(InfoSet(key, node.player, node.actions))
            self.info_action_kinds.append(node.action_kinds)
        return info

    def _five_card_strength(self, cards: tuple[int, ...]) -> tuple[int, ...]:
        ranks = [card // self.suits for card in cards]
        suits = [card % self.suits for card in cards]
        groups = sorted(((ranks.count(rank), rank) for rank in set(ranks)), reverse=True)
        distinct = sorted(set(ranks))
        straight_high = None
        if len(distinct) == 5:
            if distinct[-1] - distinct[0] == 4:
                straight_high = distinct[-1]
            elif distinct == [0, 1, 2, 3, self.ranks - 1]:
                straight_high = 3  # ace-low wheel (A-2-3-4-5)
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

    def showdown(self, deal: tuple[int, ...]) -> int:
        board = tuple(deal[4:9])
        hand0, hand1 = (*deal[0:2], *board), (*deal[2:4], *board)
        best0 = max(self._five_card_strength(hand) for hand in combinations(hand0, 5))
        best1 = max(self._five_card_strength(hand) for hand in combinations(hand1, 5))
        return (best0 > best1) - (best0 < best1)

    def evaluation_view(self, deals: tuple[tuple[int, ...], ...]):
        """Materialize only a fixed sample for the existing exact evaluator."""
        infosets, info_by_key, nodes = [], {}, []
        outcomes = tuple(self.showdown(deal) for deal in deals)
        for node in self.nodes:
            if node.player < 0:
                if node.terminal == "fold":
                    payoffs = (node.terminal_payoff,) * len(deals)
                else:
                    payoffs = tuple(float(node.pot * outcome) for outcome in outcomes)
                nodes.append(PublicNode(-1, payoffs=payoffs))
                continue
            info_ids = []
            for deal in deals:
                key = self.info_key(node, deal)
                info = info_by_key.get(key)
                if info is None:
                    info = len(infosets)
                    info_by_key[key] = info
                    infosets.append(InfoSet(key, node.player, node.actions))
                info_ids.append(info)
            nodes.append(PublicNode(node.player, node.children, tuple(info_ids)))
        return SampledEvaluationView(
            tuple(deals), (1.0 / len(deals),) * len(deals), tuple(nodes), tuple(infosets)
        )


@dataclass(frozen=True)
class SampledEvaluationView:
    deals: tuple[tuple[int, ...], ...]
    chance: tuple[float, ...]
    nodes: tuple[PublicNode, ...]
    infosets: tuple[InfoSet, ...]


class ExternalSamplingHoldemCFR:
    """Chance- and opponent-sampled CFR with a lazy information-set table."""

    def __init__(self, game: SampledHoldemGame, seed: int = 42):
        self.game = game
        self.rng = random.Random(seed)
        self.seed = seed
        self.iterations = 0
        self.node_visits = 0
        self.regrets: list[list[float]] = []
        self.strategy_sums: list[list[float]] = []
        self.seed_policies: dict[str, list[float]] = {}
        self.seed_iterations = 5.0
        self.seed_regret_scale = 0.001

    def _ensure_info(self, node, deal):
        info = self.game.get_or_add_infoset(node, deal)
        while len(self.regrets) <= info:
            index = len(self.regrets)
            info_set = self.game.infosets[index]
            prior = self.seed_policies.get(info_set.key)
            if prior is None:
                self.regrets.append([0.0] * len(info_set.actions))
                self.strategy_sums.append([0.0] * len(info_set.actions))
            else:
                self.regrets.append([self.seed_regret_scale * p for p in prior])
                self.strategy_sums.append([self.seed_iterations * p for p in prior])
        return info

    def _strategy(self, info):
        return normalize([max(0.0, value) for value in self.regrets[info]])

    def _sweep(self, updating, deal, outcome):
        pending = defaultdict(lambda: None)
        strategies = {}

        def get_strategy(info):
            if info not in strategies:
                strategies[info] = self._strategy(info)
            return strategies[info]

        def visit(index, own_reach):
            self.node_visits += 1
            node = self.game.nodes[index]
            if node.player < 0:
                payoff = node.terminal_payoff if node.terminal == "fold" else node.pot * outcome
                return payoff if updating == 0 else -payoff
            info = self._ensure_info(node, deal)
            strategy = get_strategy(info)
            if node.player == updating:
                sums = self.strategy_sums[info]
                for action, probability in enumerate(strategy):
                    sums[action] += own_reach * probability
                values = [visit(child, own_reach * strategy[action])
                          for action, child in enumerate(node.children)]
                value = sum(probability * child_value
                            for probability, child_value in zip(strategy, values))
                row = pending[info]
                if row is None:
                    row = pending[info] = [0.0] * len(values)
                for action, child_value in enumerate(values):
                    row[action] += child_value - value
                return value
            action = self.rng.choices(range(len(strategy)), weights=strategy, k=1)[0]
            return visit(node.children[action], own_reach)

        visit(0, 1.0)
        for info, deltas in pending.items():
            for action, delta in enumerate(deltas):
                self.regrets[info][action] += delta

    def iteration(self):
        deal = self.game.sample_deal(self.rng)
        outcome = self.game.showdown(deal)
        self._sweep(0, deal, outcome)
        self._sweep(1, deal, outcome)
        self.iterations += 1

    def advance(self, iterations: int):
        if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations < 0:
            raise ValueError("iterations must be a nonnegative integer")
        for _ in range(iterations):
            self.iteration()

    def policy_by_key(self):
        return {info.key: normalize(row) for info, row in zip(self.game.infosets, self.strategy_sums)}

    def state_dict(self):
        return {
            "algorithm": "external-sampling-holdem-cfr",
            "chips": self.game.chips,
            "bet_sizes": self.game.bet_sizes,
            "iterations": self.iterations,
            "node_visits": self.node_visits,
            "regrets": self.regrets,
            "strategy_sums": self.strategy_sums,
            "infosets": [info.key for info in self.game.infosets],
            "rng_state": self.rng.getstate(),
        }


def evaluate_sampled(solver: ExternalSamplingHoldemCFR, *, samples=512, seed=2026):
    if samples < 1:
        raise ValueError("samples must be positive")
    rng = random.Random(seed)
    deals = tuple(solver.game.sample_deal(rng) for _ in range(samples))
    view = solver.game.evaluation_view(deals)
    learned = solver.policy_by_key()
    policy = [learned.get(info.key, normalize([1.0] * len(info.actions)))
              for info in view.infosets]
    result = evaluate(view, policy)
    return {**result, "evaluation_samples": samples, "evaluation_seed": seed}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Sampled CFR on a turn/river mini Hold'em game.")
    parser.add_argument("--chips", type=int, default=4)
    parser.add_argument("--bet-sizes", type=int, nargs="+", default=(2, 4))
    parser.add_argument("--ranks", type=int, default=6)
    parser.add_argument("--suits", type=int, choices=(2, 4), default=2)
    parser.add_argument("--iterations", type=int, default=10000)
    parser.add_argument("--eval-every", type=int, default=1000)
    parser.add_argument("--eval-samples", type=int, default=512)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists() or args.iterations < 0 or args.eval_every <= 0:
        parser.error("output must be new; iterations nonnegative; eval-every positive")
    game = SampledHoldemGame(args.chips, tuple(args.bet_sizes), args.ranks, args.suits)
    solver = ExternalSamplingHoldemCFR(game, args.seed)
    args.output.mkdir(parents=True)
    rows = []
    targets = list(range(0, args.iterations + 1, args.eval_every))
    if not targets or targets[-1] != args.iterations:
        targets.append(args.iterations)
    train_seconds = 0.0
    for target in targets:
        train_started = time.perf_counter()
        solver.advance(target - solver.iterations)
        train_seconds += time.perf_counter() - train_started
        metrics = evaluate_sampled(solver, samples=args.eval_samples, seed=2026)
        row = {"iteration": solver.iterations, "train_seconds": train_seconds, **metrics}
        rows.append(row)
        with (args.output / "metrics.jsonl").open("a") as handle:
            handle.write(json.dumps(row, allow_nan=False) + "\n")
    summary = {"game": "sampled-holdem", "chips": game.chips, "bet_sizes": game.bet_sizes,
               "ranks": game.ranks, "suits": game.suits, "public_cards": game.public_cards,
               "public_nodes": len(game.nodes), "iterations": solver.iterations,
               "sampled_infosets": len(game.infosets), "results": rows,
               "note": "exploitability is an estimate on the fixed sampled deal set"}
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(json.dumps(rows[-1], sort_keys=True))


if __name__ == "__main__":
    main()
