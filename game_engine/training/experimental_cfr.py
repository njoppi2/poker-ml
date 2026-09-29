"""Auditable full-tree CFR variants for the compiled modified-Leduc game.

These are deliberately separate from :mod:`solver`: external sampling has a
different estimator and simply clipping its sampled regrets would not implement
CFR+.  A solver iteration here is two chronological player sweeps.  Each sweep
enumerates every weighted rank deal and aggregates values across all histories
of an information set before modifying its regret row.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import tempfile
import time
from array import array
from pathlib import Path

from .evaluate import evaluate
from .game import LeducGame, MiniHoldemGame
from .solver import normalize


_VARIANTS = {"vanilla", "cfr_plus", "dcfr"}
_KERNEL_ROOT = Path(__file__).with_name("cfr_variants_kernel")
_KERNEL = _KERNEL_ROOT / "target" / "release" / "leduc-cfr-variants-kernel"
_KERNEL_BUILT = False


def build_full_cfr_kernel():
    """Build the optional native full-tree kernel (outside measured training)."""
    global _KERNEL_BUILT
    if _KERNEL_BUILT and _KERNEL.exists():
        return _KERNEL
    cargo = shutil.which("cargo")
    if not cargo:
        raise RuntimeError("native full-CFR backend requires cargo")
    subprocess.run([cargo, "build", "--release", "--manifest-path", str(_KERNEL_ROOT / "Cargo.toml")], check=True)
    if not _KERNEL.exists():
        raise RuntimeError("cargo completed but the full-CFR kernel was not created")
    _KERNEL_BUILT = True
    return _KERNEL


def _le_array(typecode, values):
    result = array(typecode, values)
    if __import__("sys").byteorder != "little":
        result.byteswap()
    return result.tobytes()


class FullTraversalCFR:
    """Alternating full-tree CFR, CFR+, or discounted CFR (DCFR).

    The regret update at information set ``I`` is
    ``sum_h chance(h) * pi_-i(h) * (v_i(h,a) - v_i(h))``.  Strategy sums use
    ``sum_h chance(h) * pi_i(h) * sigma_i(I)``.  Keeping these factors explicit
    is important because several rank deals share one information set.
    """

    def __init__(self, game: LeducGame, variant: str = "vanilla", seed: int | None = None):
        if variant not in _VARIANTS:
            raise ValueError(f"unknown CFR variant {variant!r}")
        self.game, self.variant, self.seed = game, variant, seed
        self.name = f"full-{variant.replace('_', '-') }"
        self.iterations = 0
        self.node_visits = 0
        self.regrets = [[0.0] * len(info.actions) for info in game.infosets]
        self.strategy_sums = [[0.0] * len(info.actions) for info in game.infosets]
        self.visited = set()

    def _strategy(self, info: int):
        return normalize([max(0.0, value) for value in self.regrets[info]])

    def _average_weight(self):
        # Linear averaging is part of the usual CFR+ presentation.  Vanilla
        # CFR uses unit weights; DCFR's recurrence discounts its prior sum.
        return self.iterations + 1 if self.variant == "cfr_plus" else 1.0

    def _discount(self):
        """Apply Brown--Sandholm DCFR discounting before this iteration."""
        if self.variant != "dcfr":
            return
        # The recurrence discounts *after* completed iteration t.  Since this
        # method runs before the next sweep, use the completed count and leave
        # iteration zero untouched.
        t = self.iterations
        if t == 0:
            return
        positive = t ** 1.5 / (t ** 1.5 + 1.0)
        negative = 1.0 / 2.0  # beta=0: t^0 / (t^0 + 1)
        average = (t / (t + 1.0)) ** 2.0  # gamma=2
        for regrets in self.regrets:
            for action, regret in enumerate(regrets):
                regrets[action] = regret * (positive if regret > 0.0 else negative)
        for sums in self.strategy_sums:
            for action in range(len(sums)):
                sums[action] *= average

    def _sweep(self, updating: int):
        """Compute one player's complete counterfactual update, then apply it."""
        strategies = [self._strategy(info) for info in range(len(self.game.infosets))]
        deltas = [[0.0] * len(info.actions) for info in self.game.infosets]

        def visit(index: int, deal: int, own_reach: float, opponent_reach: float) -> float:
            self.node_visits += 1
            node = self.game.nodes[index]
            if node.player < 0:
                return node.payoffs[deal] if updating == 0 else -node.payoffs[deal]
            info = node.infos[deal]
            self.visited.add(info)
            strategy = strategies[info]
            if node.player == updating:
                # Own prior reach weights the player's average strategy; it is
                # intentionally absent from the counterfactual regret update.
                chance_own = self._average_weight() * self.game.chance[deal] * own_reach
                for action, probability in enumerate(strategy):
                    self.strategy_sums[info][action] += chance_own * probability
                values = [visit(child, deal, own_reach * strategy[action], opponent_reach)
                          for action, child in enumerate(node.children)]
                value = sum(probability * action_value
                            for probability, action_value in zip(strategy, values))
                weight = self.game.chance[deal] * opponent_reach
                for action, action_value in enumerate(values):
                    deltas[info][action] += weight * (action_value - value)
                return value
            values = [visit(child, deal, own_reach, opponent_reach * strategy[action])
                      for action, child in enumerate(node.children)]
            return sum(probability * action_value
                       for probability, action_value in zip(strategy, values))

        for deal in range(len(self.game.deals)):
            visit(0, deal, 1.0, 1.0)
        for info, row in enumerate(deltas):
            regrets = self.regrets[info]
            for action, value in enumerate(row):
                next_value = regrets[action] + value
                regrets[action] = max(0.0, next_value) if self.variant == "cfr_plus" else next_value

    def iteration(self):
        self._discount()
        # Alternating player sweeps: player one's sweep sees player zero's
        # freshly updated regret-matching policy, as in standard alternating CFR.
        self._sweep(0)
        self._sweep(1)
        self.iterations += 1

    def advance(self, iterations: int):
        if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations < 0:
            raise ValueError("iterations must be a nonnegative integer")
        for _ in range(iterations):
            self.iteration()

    def average_policy(self):
        return [normalize(row) for row in self.strategy_sums]

    def state_dict(self):
        return {"algorithm": self.name, "variant": self.variant, "chips": self.game.chips,
                "bet_sizes": self.game.bet_sizes,
                "public_cards": self.game.public_cards,
                "ranks": self.game.ranks,
                "suits": getattr(self.game, "suits", 0),
                "game_type": type(self.game).__name__,
                "iterations": self.iterations, "regrets": self.regrets,
                "strategy_sums": self.strategy_sums, "visited": self.visited,
                "node_visits": self.node_visits}

    @classmethod
    def from_state(cls, game: LeducGame, state):
        if (state.get("chips") != game.chips
                or tuple(state.get("bet_sizes", range(2, game.chips + 1))) != game.bet_sizes
                or state.get("public_cards", 1) != game.public_cards
                or state.get("ranks", 3) != game.ranks
                or state.get("suits", 0) != getattr(game, "suits", 0)
                or state.get("game_type", "LeducGame") != type(game).__name__):
            raise ValueError("checkpoint game configuration does not match")
        solver = cls(game, state["variant"])
        solver.iterations = state["iterations"]
        solver.regrets = state["regrets"]
        solver.strategy_sums = state["strategy_sums"]
        solver.visited = set(state["visited"])
        solver.node_visits = state["node_visits"]
        return solver


class NativeFullTraversalCFR(FullTraversalCFR):
    """Same state/API as :class:`FullTraversalCFR`, batched in a Rust process.

    The process boundary is included in ``advance`` timing; kernel compilation,
    policy conversion, exact evaluation, and result export are intentionally
    outside it.  Use blocks large enough to amortize state transfer.
    """

    def __init__(self, game, variant="vanilla", seed=None):
        super().__init__(game, variant, seed)
        self.binary = build_full_cfr_kernel()
        self._scratch = tempfile.TemporaryDirectory(prefix="leduc-full-cfr-")
        self._input, self._output = (Path(self._scratch.name) / name for name in ("input.bin", "output.bin"))

    def _write_input(self, iterations):
        children, offsets = [], [0]
        for node in self.game.nodes:
            children.extend(node.children)
            offsets.append(len(children))
        action_offsets = [0]
        for info in self.game.infosets:
            action_offsets.append(action_offsets[-1] + len(info.actions))
        data = bytearray(b"LDCFRT01")
        data.extend(__import__("struct").pack("<8Q", iterations, len(self.game.nodes), len(self.game.deals),
                                               len(self.game.infosets), len(children), action_offsets[-1],
                                               self.iterations, self.node_visits))
        data.append({"vanilla": 0, "cfr_plus": 1, "dcfr": 2}[self.variant])
        data.extend(_le_array("b", (node.player for node in self.game.nodes)))
        data.extend(_le_array("Q", offsets)); data.extend(_le_array("I", children))
        data.extend(_le_array("I", (info for node in self.game.nodes for info in
                                      (node.infos if node.infos else (0,) * len(self.game.deals)))))
        data.extend(_le_array("d", (payoff for node in self.game.nodes for payoff in
                                      (node.payoffs if node.payoffs else (0.0,) * len(self.game.deals)))))
        data.extend(_le_array("d", self.game.chance)); data.extend(_le_array("Q", action_offsets))
        data.extend(_le_array("d", (x for row in self.regrets for x in row)))
        data.extend(_le_array("d", (x for row in self.strategy_sums for x in row)))
        data.extend(bytearray(int(i in self.visited) for i in range(len(self.game.infosets))))
        self._input.write_bytes(data)

    def _read_output(self):
        import struct
        data, offset = memoryview(self._output.read_bytes()), 0
        def take(size):
            nonlocal offset
            part = data[offset:offset + size]
            if len(part) != size:
                raise ValueError("truncated full-CFR kernel output")
            offset += size
            return part
        if bytes(take(8)) != b"LDCFRO01":
            raise ValueError("invalid full-CFR kernel output")
        self.iterations, self.node_visits = struct.unpack("<QQ", take(16))
        n = sum(len(info.actions) for info in self.game.infosets)
        regrets = struct.unpack(f"<{n}d", take(n * 8)); sums = struct.unpack(f"<{n}d", take(n * 8))
        flags = take(len(self.game.infosets))
        if offset != len(data):
            raise ValueError("unexpected full-CFR kernel output")
        self.regrets, self.strategy_sums, pos = [], [], 0
        for info in self.game.infosets:
            end = pos + len(info.actions)
            self.regrets.append(list(regrets[pos:end])); self.strategy_sums.append(list(sums[pos:end])); pos = end
        self.visited = {i for i, value in enumerate(flags) if value}

    def advance(self, iterations):
        if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations < 0:
            raise ValueError("iterations must be a nonnegative integer")
        if iterations:
            self._write_input(iterations)
            subprocess.run([str(self.binary), str(self._input), str(self._output)], check=True, stdout=subprocess.DEVNULL)
            self._read_output()

    def close(self):
        self._scratch.cleanup()


def _write_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def run_blocks(game, solver, *, iterations, block=100, max_seconds=None, output=None):
    """Run bounded blocks and return JSON-safe metrics for comparison harnesses.

    Training time measures only ``advance``; exact evaluation and JSON export
    are separately timed.  ``output`` receives ``metrics.jsonl`` and summary.
    """
    if block <= 0 or iterations < solver.iterations:
        raise ValueError("block must be positive and iterations cannot precede solver state")
    rows, train_seconds = [], 0.0
    deadline = None if max_seconds is None else time.perf_counter() + max_seconds
    while True:
        eval_start = time.perf_counter()
        metrics = evaluate(game, solver.average_policy())
        evaluation_seconds = time.perf_counter() - eval_start
        row = {"algorithm": solver.name, "variant": solver.variant, "iteration": solver.iterations,
               "node_visits": solver.node_visits, "train_seconds": train_seconds,
               "evaluation_seconds": evaluation_seconds, **metrics}
        rows.append(row)
        if output:
            with (output / "metrics.jsonl").open("a") as handle:
                handle.write(json.dumps(row, allow_nan=False) + "\n")
        if solver.iterations >= iterations or (deadline is not None and time.perf_counter() >= deadline):
            break
        count = min(block, iterations - solver.iterations)
        started = time.perf_counter()
        solver.advance(count)
        train_seconds += time.perf_counter() - started
    result = {"algorithm": solver.name, "variant": solver.variant, "final": rows[-1], "rows": rows,
              "timing": "train_seconds excludes exact evaluation and JSON export"}
    if output:
        _write_json(output / "summary.json", result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Experimental full-traversal CFR benchmark.")
    parser.add_argument("--variant", choices=sorted(_VARIANTS), default="vanilla")
    parser.add_argument("--game", choices=("leduc", "mini-holdem"), default="leduc")
    parser.add_argument("--backend", choices=("python", "native"), default="python",
                        help="use the optimized Rust traversal kernel when set to native")
    parser.add_argument("--chips", type=int, default=4)
    parser.add_argument("--public-cards", type=int, choices=(1, 2), default=1,
                        help="number of public cards revealed over the post-preflop streets")
    parser.add_argument("--ranks", type=int, choices=range(3, 14), default=3,
                        help="number of ranks in the two-copy suitless deck")
    parser.add_argument("--bet-sizes", type=int, nargs="+",
                        help="optional sorted bet targets, including the all-in size")
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--block", type=int, default=100)
    parser.add_argument("--max-seconds", type=float)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists() or args.iterations < 0 or args.block <= 0:
        parser.error("output must be new; iterations must be nonnegative; block must be positive")
    args.output.mkdir(parents=True)
    bet_sizes = None if args.bet_sizes is None else tuple(args.bet_sizes)
    if args.game == "mini-holdem":
        if args.public_cards != 1 or args.ranks != 3:
            parser.error("--public-cards and --ranks configure only the leduc game")
        game = MiniHoldemGame(args.chips, bet_sizes)
    else:
        game = LeducGame(args.chips, bet_sizes, public_cards=args.public_cards, ranks=args.ranks)
    solver_type = NativeFullTraversalCFR if args.backend == "native" else FullTraversalCFR
    solver = solver_type(game, args.variant)
    try:
        result = run_blocks(game, solver, iterations=args.iterations,
                            block=args.block, max_seconds=args.max_seconds, output=args.output)
    finally:
        if isinstance(solver, NativeFullTraversalCFR):
            solver.close()
    print(json.dumps(result["final"], sort_keys=True))


if __name__ == "__main__":
    main()
