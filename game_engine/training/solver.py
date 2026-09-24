"""Two-player external-sampling MCCFR and the historical trainer adapter.

External sampling follows Lanctot et al. (2009): enumerate the updating player's
actions, sample chance and the opponent, update regrets with action value minus
policy-weighted value. No extra opponent-reach multiplier after sampling. Average
strategies at opponent nodes (the two-player simple-average estimator).
"""
import random

from .game import LeducGame


def normalize(values):
    total = sum(values)
    return [value / total for value in values] if total > 0 else [1.0 / len(values)] * len(values)


class ExternalSampling:
    name = "external"

    def __init__(self, game: LeducGame, seed=42):
        self.game = game
        self.rng = random.Random(seed)
        self.iterations = 0
        self.node_visits = 0
        self.regrets = [[0.0] * len(info.actions) for info in game.infosets]
        self.strategy_sums = [[0.0] * len(info.actions) for info in game.infosets]
        self.visited = set()

    def iteration(self):
        for player in (0, 1):
            deal = self.rng.choices(range(len(self.game.deals)), self.game.chance)[0]
            self._traverse(0, deal, player)
        self.iterations += 1

    def _traverse(self, index, deal, updating):
        self.node_visits += 1
        node = self.game.nodes[index]
        if node.player < 0:
            return node.payoffs[deal] * (1 if updating == 0 else -1)
        info = node.infos[deal]
        self.visited.add(info)
        regrets = self.regrets[info]
        strategy = normalize([max(0.0, regret) for regret in regrets])
        if node.player != updating:
            action = self.rng.choices(range(len(strategy)), strategy)[0]
            value = self._traverse(node.children[action], deal, updating)
            average = self.strategy_sums[info]
            for i, probability in enumerate(strategy):
                average[i] += probability
            return value
        values = [self._traverse(child, deal, updating) for child in node.children]
        value = sum(p * v for p, v in zip(strategy, values))
        for i, action_value in enumerate(values):
            regrets[i] += action_value - value
        return value

    def average_policy(self):
        return [normalize(row) for row in self.strategy_sums]

    def state_dict(self):
        return {"algorithm": self.name, "chips": self.game.chips, "iterations": self.iterations,
                "rng_state": self.rng.getstate(), "regrets": self.regrets,
                "strategy_sums": self.strategy_sums, "visited": self.visited,
                "node_visits": self.node_visits}


class LegacySampling:
    """Run historical update semantics without per-iteration logging or file writes."""
    name = "legacy"

    def __init__(self, game: LeducGame, seed=42):
        from game_engine.ia.algorithms.mod_leduc import ModLeducTrainer, Card
        class CountingTrainer(ModLeducTrainer):
            visits = 0
            def nash_equilibrium_algorithm(self, *args):
                self.visits += 1
                return super().nash_equilibrium_algorithm(*args)
        self.game = game
        self.rng = random.Random(seed)
        self.iterations = 0
        self.trainer = CountingTrainer(
            0, "mccfr", [Card.Q, Card.Q, Card.K, Card.K, Card.A, Card.A],
            0.0, "cfr", list("pbB3456789quv"), 0.0, False,
            game.chips, 1, 1, False, autorun=False,
        )
        self.total_regret = 0.0

    @property
    def node_visits(self):
        return self.trainer.visits

    @property
    def visited(self):
        return self.trainer.node_history_map

    def iteration(self):
        from game_engine.ia.algorithms import mod_leduc
        # Historical code uses module-global random and diagnostics. Preserve the
        # caller's state; benchmark seeds and runs must remain independent.
        caller_rng, caller_regret = random.getstate(), mod_leduc.total_regret_sum
        try:
            random.setstate(self.rng.getstate())
            mod_leduc.total_regret_sum = self.total_regret
            random.shuffle(self.trainer.cards)
            initial = (self.game.chips - 1, 1, 1, False)
            self.trainer.nash_equilibrium_algorithm(
                self.trainer.cards, "", 1, 1, (initial, initial), "preflop",
                False, 1, None, self.trainer.node_history_map, self.trainer.node_history_map,
            )
            self.rng.setstate(random.getstate())
            self.total_regret = mod_leduc.total_regret_sum
            self.iterations += 1
        finally:
            random.setstate(caller_rng)
            mod_leduc.total_regret_sum = caller_regret

    def average_policy(self):
        policy = []
        for info in self.game.infosets:
            node = self.trainer.node_history_map.get(info.key)
            if node is None:
                policy.append([1.0 / len(info.actions)] * len(info.actions))
            else:
                if tuple(a["value"] for a in node.actions) != info.actions:
                    raise ValueError(f"historical action mismatch at {info.key}")
                policy.append(node.get_average_strategy())
        return policy

    def state_dict(self):
        return {"algorithm": self.name, "chips": self.game.chips, "iterations": self.iterations,
                "rng_state": self.rng.getstate(), "cards": self.trainer.cards,
                "nodes": self.trainer.node_history_map, "total_regret": self.total_regret,
                "node_visits": self.node_visits}


def restore(game, state):
    if state["chips"] != game.chips:
        raise ValueError("checkpoint chips do not match game")
    algorithm = state["algorithm"]
    if algorithm not in {"external", "legacy"}:
        raise ValueError("unknown checkpoint algorithm")
    solver = ExternalSampling(game) if algorithm == "external" else LegacySampling(game)
    solver.iterations = state["iterations"]
    solver.rng.setstate(state["rng_state"])
    if algorithm == "external":
        solver.regrets = state["regrets"]
        solver.strategy_sums = state["strategy_sums"]
        solver.visited = state["visited"]
        solver.node_visits = state["node_visits"]
    else:
        solver.trainer.cards = state["cards"]
        solver.trainer.node_history_map.update(state["nodes"])
        solver.total_regret = state["total_regret"]
        solver.trainer.visits = state["node_visits"]
    return solver
