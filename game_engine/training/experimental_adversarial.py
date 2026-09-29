"""Exact, small-game adversarial-training experiments.

Two modes are deliberately kept separate:

``ed`` is tabular Exploitability Descent (ED): at every iteration it computes
an exact best response to each seat, evaluates exact *counterfactual* action
values against those responses, and updates each behavioural-policy row with
an L2/simplex projected ascent step.  Both players are updated from the same
pre-update policy.  This is the tabular ED(q^c, projected-simplex) recipe,
not MCCFR with an opponent substituted into its samples.

``league`` is a practical, intentionally heuristic variant.  It periodically
adds fresh exact exploiters of the deployed policy to a bounded frozen pool,
then interleaves whole self-play hands and whole frozen opponents.  It shares
the exact counterfactual evaluator with ED, but pool refresh/eviction and the
mixture schedule have no inherited CFR or ED convergence guarantee.

The module only targets the compiled research Leduc game.  It is useful for
checking an adversarial-training idea cheaply and reproducibly, not for
claiming a scalable no-limit-poker result.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import struct
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .evaluate import evaluate, expected_value, validate_policy
from .game import LeducGame


Policy = list[list[float]]
_ADVERSARIAL_CRATE = Path(__file__).with_name("adversarial_kernel")
_ADVERSARIAL_BINARY = _ADVERSARIAL_CRATE / "target" / "release" / "leduc-adversarial-kernel"
_ADVERSARIAL_BUILT = False


def build_adversarial_kernel() -> Path:
    """Build and return the separate native ED, league, and CFR-BR kernel."""
    global _ADVERSARIAL_BUILT
    if _ADVERSARIAL_BUILT and _ADVERSARIAL_BINARY.exists():
        return _ADVERSARIAL_BINARY
    cargo = shutil.which("cargo")
    if not cargo:
        raise RuntimeError("native adversarial training requires cargo")
    subprocess.run([cargo, "build", "--release", "--manifest-path",
                    str(_ADVERSARIAL_CRATE / "Cargo.toml")], check=True)
    if not _ADVERSARIAL_BINARY.exists():
        raise RuntimeError("cargo did not create the adversarial kernel")
    _ADVERSARIAL_BUILT = True
    return _ADVERSARIAL_BINARY


def _copy_policy(policy: Policy) -> Policy:
    return [list(row) for row in policy]


def normalize(values: Iterable[float]) -> list[float]:
    values = list(values)
    total = sum(values)
    return [value / total for value in values] if total > 0 else [1.0 / len(values)] * len(values)


def project_simplex(values: Iterable[float]) -> list[float]:
    """Euclidean projection of ``values`` onto the probability simplex."""
    values = list(values)
    if not values:
        raise ValueError("cannot project an empty action row")
    ordered = sorted(values, reverse=True)
    cumulative = 0.0
    rho = 0
    for index, value in enumerate(ordered, 1):
        cumulative += value
        if value - (cumulative - 1.0) / index > 0.0:
            rho = index
    theta = (sum(ordered[:rho]) - 1.0) / rho
    return [max(value - theta, 0.0) for value in values]


def best_response(game: LeducGame, policy: Policy, responder: int) -> dict:
    """Return an exact information-set best response and its action scores.

    ``action_values[info]`` is the unnormalised counterfactual score used to
    select an action: it includes chance and the other player's reach, while
    omitting the responder's own reach.  Consequently each choice is made
    once per information set, never once per hidden deal.
    """
    validate_policy(game, policy)
    if responder not in (0, 1):
        raise ValueError("responder must be 0 or 1")
    reaches: list[tuple[float, ...] | None] = [None] * len(game.nodes)
    reaches[0] = game.chance
    for index, node in enumerate(game.nodes):
        if node.player < 0:
            continue
        reach = reaches[index]
        assert reach is not None
        for action, child in enumerate(node.children):
            reaches[child] = (reach if node.player == responder else
                               tuple(r * policy[info][action]
                                     for r, info in zip(reach, node.infos)))

    values: list[tuple[float, ...] | None] = [None] * len(game.nodes)
    action_values: list[list[float] | None] = [None] * len(game.infosets)
    chosen_actions: list[int | None] = [None] * len(game.infosets)
    sign = 1.0 if responder == 0 else -1.0
    for index in range(len(game.nodes) - 1, -1, -1):
        node = game.nodes[index]
        if node.player < 0:
            values[index] = tuple(sign * value for value in node.payoffs)
        elif node.player == responder:
            scores = {info: [0.0] * len(node.children) for info in node.infos}
            reach = reaches[index]
            assert reach is not None
            for action, child in enumerate(node.children):
                child_values = values[child]
                assert child_values is not None
                for info, probability, value in zip(node.infos, reach, child_values):
                    scores[info][action] += probability * value
            choices = {info: max(range(len(row)), key=row.__getitem__)
                       for info, row in scores.items()}
            for info, row in scores.items():
                action_values[info] = row
                chosen_actions[info] = choices[info]
            values[index] = tuple(values[node.children[choices[info]]][deal]  # type: ignore[index]
                                  for deal, info in enumerate(node.infos))
        else:
            values[index] = tuple(
                sum(policy[info][action] * values[child][deal]  # type: ignore[index]
                    for action, child in enumerate(node.children))
                for deal, info in enumerate(node.infos))
        for child in node.children:
            values[child] = None
    root_values = values[0]
    assert root_values is not None
    response = _copy_policy(policy)
    for info, choice in enumerate(chosen_actions):
        if choice is not None:
            response[info] = [float(action == choice)
                              for action in range(len(response[info]))]
    return {"value": sum(p * value for p, value in zip(game.chance, root_values)),
            "policy": response, "chosen_actions": chosen_actions,
            "action_values": action_values}


def counterfactual_action_values(game: LeducGame, policy: Policy, player: int) -> list[list[float] | None]:
    """Exact q^c values for ``player`` under a complete joint policy.

    At an information set I, q^c(I,a) sums terminal values over chance and the
    other player's reach only.  This is the reach weighting required by the
    tabular imperfect-information ED update (and differs from an ordinary
    sampled self-play return).
    """
    validate_policy(game, policy)
    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")
    reaches: list[tuple[float, ...] | None] = [None] * len(game.nodes)
    reaches[0] = game.chance
    for index, node in enumerate(game.nodes):
        if node.player < 0:
            continue
        reach = reaches[index]
        assert reach is not None
        for action, child in enumerate(node.children):
            reaches[child] = (reach if node.player == player else
                               tuple(r * policy[info][action]
                                     for r, info in zip(reach, node.infos)))

    values: list[tuple[float, ...] | None] = [None] * len(game.nodes)
    result: list[list[float] | None] = [None] * len(game.infosets)
    sign = 1.0 if player == 0 else -1.0
    for index in range(len(game.nodes) - 1, -1, -1):
        node = game.nodes[index]
        if node.player < 0:
            values[index] = tuple(sign * value for value in node.payoffs)
        else:
            values[index] = tuple(
                sum(policy[info][action] * values[child][deal]  # type: ignore[index]
                    for action, child in enumerate(node.children))
                for deal, info in enumerate(node.infos))
            if node.player == player:
                scores = {info: [0.0] * len(node.children) for info in node.infos}
                reach = reaches[index]
                assert reach is not None
                for action, child in enumerate(node.children):
                    child_values = values[child]
                    assert child_values is not None
                    for info, probability, value in zip(node.infos, reach, child_values):
                        scores[info][action] += probability * value
                for info, row in scores.items():
                    result[info] = row
        for child in node.children:
            values[child] = None
    return result


def joint_policy(game: LeducGame, seat0: Policy, seat1: Policy) -> Policy:
    return [list(seat0[index] if info.player == 0 else seat1[index])
            for index, info in enumerate(game.infosets)]


def regret_matching(regrets: list[float]) -> list[float]:
    return normalize([max(0.0, value) for value in regrets])


def own_reach_weights(game: LeducGame, policy: Policy, player: int) -> list[float]:
    """Chance-weighted realization reach of player's information sets."""
    reaches: list[tuple[float, ...] | None] = [None] * len(game.nodes)
    reaches[0] = game.chance
    weights = [0.0] * len(game.infosets)
    for index, node in enumerate(game.nodes):
        if node.player < 0:
            continue
        reach = reaches[index]
        assert reach is not None
        if node.player == player:
            for info, probability in zip(node.infos, reach):
                weights[info] += probability
        for action, child in enumerate(node.children):
            reaches[child] = (tuple(probability * policy[info][action]
                                    for probability, info in zip(reach, node.infos))
                               if node.player == player else reach)
    return weights


@dataclass
class CFRBestResponse:
    """Exact tabular CFR-BR baseline, with independent simultaneous seat updates.

    The current regret-matched policies face fresh exact best responses.  Regret
    increments use counterfactual action values; exported policy is the
    chance-weighted own-realization average, not the last iterate.
    """
    game: LeducGame
    initial_policy: Policy | None = None
    iterations: int = 0

    def __post_init__(self):
        initial = _copy_policy(self.initial_policy) if self.initial_policy is not None else None
        if initial is not None:
            validate_policy(self.game, initial)
        # Preserve a warm start as the initial current policy by choosing
        # regrets whose positive parts reproduce every nonzero row.
        self.regrets = ([list(row) for row in initial] if initial is not None else
                        [[0.0] * len(info.actions) for info in self.game.infosets])
        self.strategy_sums = [[0.0] * len(info.actions) for info in self.game.infosets]

    def current_policy(self) -> Policy:
        return [regret_matching(row) for row in self.regrets]

    def iteration(self) -> dict:
        before = self.current_policy()
        br0 = best_response(self.game, before, 0)
        br1 = best_response(self.game, before, 1)
        q0 = counterfactual_action_values(self.game, joint_policy(self.game, before, br1["policy"]), 0)
        q1 = counterfactual_action_values(self.game, joint_policy(self.game, br0["policy"], before), 1)
        # Simultaneous regrets and correctly weighted behavioural averaging.
        for player, q in ((0, q0), (1, q1)):
            reaches = own_reach_weights(self.game, before, player)
            for index, info in enumerate(self.game.infosets):
                if info.player != player:
                    continue
                action_values = q[index]
                assert action_values is not None
                value = sum(p * v for p, v in zip(before[index], action_values))
                for action, action_value in enumerate(action_values):
                    self.regrets[index][action] += action_value - value
                    self.strategy_sums[index][action] += reaches[index] * before[index][action]
        self.iterations += 1
        return {"iteration": self.iterations, "best_response_p0": br0["value"],
                "best_response_p1": br1["value"]}

    def advance(self, count: int) -> None:
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("advance count must be a nonnegative integer")
        for _ in range(count):
            self.iteration()

    def average_policy(self) -> Policy:
        return [normalize(row) for row in self.strategy_sums]


@dataclass
class TabularED:
    """Synchronous exact TabularED(q^c, L2 projection) for tiny games."""
    game: LeducGame
    step_size: float = 0.5
    initial_policy: Policy | None = None
    policy: Policy | None = None
    iterations: int = 0

    def __post_init__(self):
        if not math.isfinite(self.step_size) or self.step_size <= 0:
            raise ValueError("step_size must be finite and positive")
        if self.initial_policy is not None and self.policy is not None:
            raise ValueError("pass either initial_policy or policy, not both")
        self.policy = _copy_policy(self.initial_policy or self.policy or self.game.uniform_policy())
        validate_policy(self.game, self.policy)

    def iteration(self) -> dict:
        assert self.policy is not None
        before = self.policy
        br0 = best_response(self.game, before, 0)
        br1 = best_response(self.game, before, 1)
        # Player 0 ascends against P1's BR; player 1 ascends against P0's BR.
        q0 = counterfactual_action_values(self.game, joint_policy(self.game, before, br1["policy"]), 0)
        q1 = counterfactual_action_values(self.game, joint_policy(self.game, br0["policy"], before), 1)
        alpha = self.step_size / math.sqrt(self.iterations + 1)
        updated = _copy_policy(before)
        for index, info in enumerate(self.game.infosets):
            scores = q0[index] if info.player == 0 else q1[index]
            assert scores is not None
            updated[index] = project_simplex(p + alpha * score for p, score in zip(before[index], scores))
        self.policy = updated
        self.iterations += 1
        return {"iteration": self.iterations, "step_size": alpha,
                "best_response_p0": br0["value"], "best_response_p1": br1["value"]}

    def advance(self, count: int) -> None:
        if count < 0:
            raise ValueError("advance count must be nonnegative")
        for _ in range(count):
            self.iteration()

    def average_policy(self) -> Policy:
        """Solver-compatible name: ED deploys its current, not averaged, policy."""
        assert self.policy is not None
        return _copy_policy(self.policy)

    current_policy = average_policy


@dataclass
class HeuristicLeague:
    """Fresh-BR, retained-opponent experiment; intentionally no convergence claim."""
    game: LeducGame
    step_size: float = 0.5
    refresh_every: int = 10
    max_snapshots: int = 8
    self_play_weight: float = 0.5
    initial_policy: Policy | None = None
    policy: Policy | None = None
    iterations: int = 0
    snapshots: list[tuple[Policy, Policy]] = field(default_factory=list)

    def __post_init__(self):
        if (not math.isfinite(self.step_size) or self.step_size <= 0 or
                self.refresh_every < 1 or self.max_snapshots < 1 or
                not math.isfinite(self.self_play_weight) or not 0 <= self.self_play_weight <= 1):
            raise ValueError("invalid league schedule")
        if self.initial_policy is not None and self.policy is not None:
            raise ValueError("pass either initial_policy or policy, not both")
        self.policy = _copy_policy(self.initial_policy or self.policy or self.game.uniform_policy())
        validate_policy(self.game, self.policy)

    def _refresh(self) -> None:
        assert self.policy is not None
        # A pair stores P0's and P1's fresh exploiters of this deployed policy.
        self.snapshots.append((best_response(self.game, self.policy, 0)["policy"],
                               best_response(self.game, self.policy, 1)["policy"]))
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots.pop(0)

    def _opponent_for_update(self, opponent: int) -> Policy:
        """Choose one complete policy, preserving across-hand correlations.

        A behavioural row-wise mixture would let the sampled source change at
        every decision, which is not the same game as alternating opponents.
        This deterministic weighted schedule emits self play in a fraction
        approaching ``self_play_weight`` and rotates retained whole policies
        on the remaining updates.
        """
        assert self.policy is not None
        before = math.floor(self.iterations * self.self_play_weight)
        after = math.floor((self.iterations + 1) * self.self_play_weight)
        if after > before:
            return self.policy
        pool_turn = self.iterations - before
        return self.snapshots[pool_turn % len(self.snapshots)][opponent]

    def iteration(self) -> dict:
        assert self.policy is not None
        if not self.snapshots or self.iterations % self.refresh_every == 0:
            self._refresh()
        before = self.policy
        # Both updates use the same deployed policy and one whole frozen/self
        # opponent; no row-wise mixture breaks opponent-action correlation.
        against_p1 = self._opponent_for_update(1)
        against_p0 = self._opponent_for_update(0)
        q0 = counterfactual_action_values(self.game, joint_policy(self.game, before, against_p1), 0)
        q1 = counterfactual_action_values(self.game, joint_policy(self.game, against_p0, before), 1)
        alpha = self.step_size / math.sqrt(self.iterations + 1)
        updated = _copy_policy(before)
        for index, info in enumerate(self.game.infosets):
            scores = q0[index] if info.player == 0 else q1[index]
            assert scores is not None
            updated[index] = project_simplex(p + alpha * score for p, score in zip(before[index], scores))
        self.policy = updated
        self.iterations += 1
        return {"iteration": self.iterations, "step_size": alpha,
                "retained_exploiter_pairs": len(self.snapshots)}

    def advance(self, count: int) -> None:
        if count < 0:
            raise ValueError("advance count must be nonnegative")
        for _ in range(count):
            self.iteration()

    def average_policy(self) -> Policy:
        """Solver-compatible name: returns the current deployed policy."""
        assert self.policy is not None
        return _copy_policy(self.policy)

    current_policy = average_policy


class _NativeAdversarial:
    """Shared binary protocol wrapper for the independent Rust implementation."""
    _mode = 0

    def __init__(self, game: LeducGame, step_size: float = 0.5, initial_policy: Policy | None = None,
                 refresh_every: int = 10, max_snapshots: int = 8, self_play_weight: float = 0.5,
                 exploiter_step_multiplier: float = 1.0):
        if (not math.isfinite(step_size) or step_size <= 0 or refresh_every < 1 or max_snapshots < 1 or
                not math.isfinite(self_play_weight) or not 0 <= self_play_weight <= 1 or
                not math.isfinite(exploiter_step_multiplier) or exploiter_step_multiplier <= 0):
            raise ValueError("invalid native adversarial configuration")
        self.game, self.step_size = game, step_size
        self.refresh_every, self.max_snapshots = refresh_every, max_snapshots
        self.self_play_weight, self.iterations = self_play_weight, 0
        self.exploiter_step_multiplier = exploiter_step_multiplier
        self.policy = _copy_policy(initial_policy or game.uniform_policy())
        validate_policy(game, self.policy)
        self.snapshots: list[tuple[Policy, Policy]] = []
        self.binary = build_adversarial_kernel()
        self._scratch = tempfile.TemporaryDirectory(prefix="leduc-adversarial-")
        self._input = Path(self._scratch.name) / "input.bin"
        self._output = Path(self._scratch.name) / "output.bin"

    def _flat(self, policy: Policy) -> list[float]:
        return [value for row in policy for value in row]

    def _rows(self, values: tuple[float, ...] | list[float]) -> Policy:
        position, result = 0, []
        for info in self.game.infosets:
            end = position + len(info.actions)
            result.append(list(values[position:end]))
            position = end
        return result

    def _write(self, count: int) -> None:
        children, child_offsets = [], [0]
        for node in self.game.nodes:
            children.extend(node.children)
            child_offsets.append(len(children))
        action_offsets = [0]
        for info in self.game.infosets:
            action_offsets.append(action_offsets[-1] + len(info.actions))
        payload = bytearray(b"LDADV002")
        payload.extend(struct.pack("<9QdQQdd", self._mode, count, len(self.game.nodes), len(self.game.deals),
                                   len(self.game.infosets), len(children), action_offsets[-1], self.iterations,
                                   len(self.snapshots), self.step_size, self.refresh_every,
                                   self.max_snapshots, self.self_play_weight,
                                   self.exploiter_step_multiplier))
        payload.extend(struct.pack(f"<{len(self.game.nodes)}b", *(node.player for node in self.game.nodes)))
        payload.extend(struct.pack(f"<{len(child_offsets)}Q", *child_offsets))
        payload.extend(struct.pack(f"<{len(children)}I", *children))
        info_ids = [info for node in self.game.nodes
                    for info in (node.infos if node.infos else (0,) * len(self.game.deals))]
        payoffs = [payoff for node in self.game.nodes
                   for payoff in (node.payoffs if node.payoffs else (0.0,) * len(self.game.deals))]
        payload.extend(struct.pack(f"<{len(info_ids)}I", *info_ids))
        payload.extend(struct.pack(f"<{len(payoffs)}d", *payoffs))
        payload.extend(struct.pack(f"<{len(self.game.chance)}d", *self.game.chance))
        payload.extend(struct.pack(f"<{len(action_offsets)}Q", *action_offsets))
        payload.extend(struct.pack(f"<{action_offsets[-1]}d", *self._flat(self.policy)))
        for first, second in self.snapshots:
            payload.extend(struct.pack(f"<{action_offsets[-1]}d", *self._flat(first)))
            payload.extend(struct.pack(f"<{action_offsets[-1]}d", *self._flat(second)))
        self._input.write_bytes(payload)

    def _read(self) -> None:
        data, offset = self._output.read_bytes(), 0
        def take(size: int) -> bytes:
            nonlocal offset
            result = data[offset:offset + size]
            if len(result) != size:
                raise ValueError("truncated adversarial kernel output")
            offset += size
            return result
        if take(8) != b"LDADVOUT":
            raise ValueError("invalid adversarial kernel output")
        self.iterations, snapshot_count = struct.unpack("<QQ", take(16))
        self._last_kernel_seconds = struct.unpack("<d", take(8))[0]
        count = sum(len(info.actions) for info in self.game.infosets)
        self.policy = self._rows(struct.unpack(f"<{count}d", take(count * 8)))
        self.snapshots = []
        for _ in range(snapshot_count):
            self.snapshots.append((self._rows(struct.unpack(f"<{count}d", take(count * 8))),
                                   self._rows(struct.unpack(f"<{count}d", take(count * 8)))))
        if offset != len(data):
            raise ValueError("unexpected adversarial kernel trailing bytes")
        validate_policy(self.game, self.policy)

    def advance(self, count: int) -> None:
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("advance count must be a nonnegative integer")
        if count:
            self._write(count)
            subprocess.run([str(self.binary), str(self._input), str(self._output)], check=True,
                           stdout=subprocess.DEVNULL)
            self._read()

    def iteration(self) -> None:
        self.advance(1)

    def average_policy(self) -> Policy:
        return _copy_policy(self.policy)

    current_policy = average_policy

    def close(self) -> None:
        self._scratch.cleanup()


class NativeTabularED(_NativeAdversarial):
    """Native parity implementation of :class:`TabularED`."""
    _mode = 0
    name = "native-ed"


class NativeHeuristicLeague(_NativeAdversarial):
    """Native parity implementation of whole-opponent :class:`HeuristicLeague`."""
    _mode = 1
    name = "native-league"


class NativeBatchedSingleExploiter(_NativeAdversarial):
    """One refreshed exploiter plus self-play scores in every policy update."""
    _mode = 3
    name = "native-batched-single-exploiter"

    def __init__(self, game: LeducGame, step_size: float = 0.5, initial_policy: Policy | None = None,
                 refresh_every: int = 10, self_play_weight: float = 0.25):
        super().__init__(game, step_size, initial_policy, refresh_every,
                         max_snapshots=1, self_play_weight=self_play_weight)


class NativeCounterExploiterBatch(_NativeAdversarial):
    """Average fresh responses to provisional ED policies from one base policy."""
    _mode = 5
    name = "native-counter-exploiter-batch"

    def __init__(self, game: LeducGame, step_size: float = 0.5, initial_policy: Policy | None = None,
                 responses: int = 2, self_play_weight: float = 0.0,
                 response_growth: float = 1.0):
        if isinstance(responses, bool) or not isinstance(responses, int):
            raise ValueError("responses must be a positive integer")
        super().__init__(game, step_size, initial_policy, max_snapshots=responses,
                         self_play_weight=self_play_weight,
                         exploiter_step_multiplier=response_growth)


class NativeCoTrainingSingleExploiter(_NativeAdversarial):
    """One exploiter learns alongside the policy, with optional exact refreshes."""
    _mode = 4
    name = "native-co-training-single-exploiter"

    def __init__(self, game: LeducGame, step_size: float = 0.5, initial_policy: Policy | None = None,
                 refresh_every: int = 100_000, self_play_weight: float = 0.25,
                 exploiter_step_multiplier: float = 10.0):
        super().__init__(game, step_size, initial_policy, refresh_every,
                         max_snapshots=1, self_play_weight=self_play_weight,
                         exploiter_step_multiplier=exploiter_step_multiplier)


class NativeCFRBestResponse(_NativeAdversarial):
    """Native exact CFR-BR; warm starts are intentionally unsupported."""
    _mode = 2
    name = "native-cfr-br"

    def __init__(self, game: LeducGame, initial_policy: Policy | None = None):
        if initial_policy is not None:
            raise ValueError("NativeCFRBestResponse does not support initial_policy")
        super().__init__(game)
        self.regrets = [[0.0] * len(info.actions) for info in game.infosets]
        self.strategy_sums = [[0.0] * len(info.actions) for info in game.infosets]

    def _write(self, count: int) -> None:
        super()._write(count)
        actions = sum(len(info.actions) for info in self.game.infosets)
        with self._input.open("ab") as handle:
            handle.write(struct.pack(f"<{actions}d", *self._flat(self.regrets)))
            handle.write(struct.pack(f"<{actions}d", *self._flat(self.strategy_sums)))

    def _read(self) -> None:
        data = self._output.read_bytes()
        if data[:8] != b"LDADVOUT":
            raise ValueError("invalid adversarial kernel output")
        self.iterations, snapshots = struct.unpack_from("<QQ", data, 8)
        if snapshots:
            raise ValueError("CFR-BR kernel returned snapshots")
        self._last_kernel_seconds = struct.unpack_from("<d", data, 24)[0]
        count, offset = sum(len(info.actions) for info in self.game.infosets), 32
        offset += count * 8  # current regret-matched policy; recomputed below
        self.regrets = self._rows(struct.unpack_from(f"<{count}d", data, offset)); offset += count * 8
        self.strategy_sums = self._rows(struct.unpack_from(f"<{count}d", data, offset)); offset += count * 8
        if offset != len(data):
            raise ValueError("unexpected CFR-BR kernel trailing bytes")
        self.policy = [regret_matching(row) for row in self.regrets]

    def current_policy(self) -> Policy:
        return [regret_matching(row) for row in self.regrets]

    def average_policy(self) -> Policy:
        return [normalize(row) for row in self.strategy_sums]


def run(algorithm: str, chips: int = 4, iterations: int = 1_000, step_size: float = 0.5,
        refresh_every: int = 10, max_snapshots: int = 8, self_play_weight: float = 0.5,
        eval_every: int = 100, time_budget_s: float | None = None,
        initial_policy: Policy | None = None) -> tuple[Policy, list[dict]]:
    """Run a budgeted experiment; metrics always evaluate the deployed policy exactly."""
    if iterations < 0 or eval_every < 1 or time_budget_s is not None and time_budget_s <= 0:
        raise ValueError("invalid run budget")
    game = LeducGame(chips)
    trainer = (TabularED(game, step_size, initial_policy) if algorithm == "ed" else
               HeuristicLeague(game, step_size, refresh_every, max_snapshots, self_play_weight, initial_policy)
               if algorithm == "league" else None)
    if trainer is None:
        raise ValueError("algorithm must be 'ed' or 'league'")
    started = time.perf_counter()
    metrics = []
    def record():
        values = evaluate(game, trainer.policy)  # type: ignore[arg-type]
        metrics.append({"iteration": trainer.iterations, "elapsed_s": time.perf_counter() - started,
                        "algorithm": algorithm, **values,
                        "retained_exploiter_pairs": len(getattr(trainer, "snapshots", ()))})
    record()
    while trainer.iterations < iterations:
        if time_budget_s is not None and time.perf_counter() - started >= time_budget_s:
            break
        trainer.iteration()
        if trainer.iterations % eval_every == 0:
            record()
    if metrics[-1]["iteration"] != trainer.iterations:
        record()
    return trainer.policy, metrics  # type: ignore[return-value]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="exact Leduc adversarial-training experiments")
    parser.add_argument("--algorithm", choices=("ed", "league"), default="ed")
    parser.add_argument("--chips", type=int, default=4)
    parser.add_argument("--iterations", type=int, default=1_000)
    parser.add_argument("--time-budget-s", type=float)
    parser.add_argument("--step-size", type=float, default=0.5)
    parser.add_argument("--refresh-every", type=int, default=10)
    parser.add_argument("--max-snapshots", type=int, default=8)
    parser.add_argument("--self-play-weight", type=float, default=0.5)
    parser.add_argument("--eval-every", type=int, default=100)
    parser.add_argument("--initial-policy", type=Path,
                        help="trusted benchmark-format policy.pkl used to warm-start the deployed policy")
    parser.add_argument("--missing", choices=("call", "uniform"), default="call",
                        help="completion for absent information sets in --initial-policy")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    initial_policy = None
    if args.initial_policy:
        # Reuse the benchmark's strict action/schema validation without making
        # this experimental module a dependency of the production trainer.
        from .benchmark import load_blueprint
        initial_policy, _ = load_blueprint(LeducGame(args.chips), args.initial_policy, args.missing)
    policy, metrics = run(args.algorithm, args.chips, args.iterations, args.step_size,
                          args.refresh_every, args.max_snapshots, args.self_play_weight,
                          args.eval_every, args.time_budget_s, initial_policy)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "metrics.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in metrics))
    (args.output / "policy.json").write_text(json.dumps(policy))
    (args.output / "summary.json").write_text(json.dumps(metrics[-1], indent=2, sort_keys=True) + "\n")
    print(json.dumps(metrics[-1], sort_keys=True))


if __name__ == "__main__":
    main()
