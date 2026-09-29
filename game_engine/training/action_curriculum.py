"""Experimental transfer from a smaller betting menu into a larger one.

The target game keeps the same cards, payoffs, and chip stack. Only the legal
bet-size menu changes. A coarse bet's policy mass is partitioned among the
fine bets that round to it; no regret or probability is duplicated.
"""
from __future__ import annotations

from .evaluate import validate_policy
from .experimental_adversarial import own_reach_weights
from .experimental_cfr import NativeFullTraversalCFR
from .game import LeducGame


def _nearest_bet(value: int, choices: tuple[int, ...], all_in: int) -> int:
    if value == all_in and all_in in choices:
        return all_in
    non_all_in = tuple(choice for choice in choices if choice not in (0, all_in))
    candidates = non_all_in or tuple(choice for choice in choices if choice != 0)
    return min(candidates, key=lambda choice: (abs(choice - value), choice))


def _mapped_action(action: int, kind: str, source_actions: tuple[int, ...],
                   source_kinds: tuple[str, ...], all_in: int) -> int | None:
    # The same number can mean a raise in the fine game and a call in the
    # coarse game. Match the action's role before choosing a nearby size.
    candidates = tuple(value for value, source_kind in zip(source_actions, source_kinds)
                       if source_kind == kind)
    if not candidates:
        return None
    if action == 0:
        return candidates[0]
    return _nearest_bet(action, candidates, all_in)


def split_action_mass(source_actions: tuple[int, ...], source_row: list[float],
                      target_actions: tuple[int, ...], all_in: int,
                      *, source_kinds: tuple[str, ...] | None = None,
                      target_kinds: tuple[str, ...] | None = None) -> list[float]:
    """Project a behavioral row while conserving each represented action's mass."""
    if len(source_actions) != len(source_row) or 0 not in source_actions or 0 not in target_actions:
        raise ValueError("invalid source or target action row")
    if len(target_actions) == 1:
        return [1.0]
    if (source_kinds is None) != (target_kinds is None):
        raise ValueError("action kinds must be supplied for both games")
    if source_kinds is None:
        source_kinds = tuple("pass" if action == 0 else "bet" for action in source_actions)
        target_kinds = tuple("pass" if action == 0 else "bet" for action in target_actions)
    if len(source_kinds) != len(source_actions) or len(target_kinds) != len(target_actions):
        raise ValueError("action kinds do not match action rows")
    buckets: dict[int, list[int]] = {action: [] for action in source_actions}
    for index, (action, kind) in enumerate(zip(target_actions, target_kinds)):
        mapped = _mapped_action(action, kind, source_actions, source_kinds, all_in)
        if mapped is None:
            raise ValueError("fine action has no coarse action of the same kind")
        buckets[mapped].append(index)
    result = [0.0] * len(target_actions)
    for action, probability, kind in zip(source_actions, source_row, source_kinds):
        destinations = buckets[action]
        if not destinations:
            # A coarse raise size can become illegal after a finer history.
            # Keep its mass within raises rather than discard it or turn it
            # into a call.
            compatible = tuple(value for value, target_kind in zip(target_actions, target_kinds)
                               if target_kind == kind)
            if not compatible:
                raise ValueError("coarse action has no fine action of the same kind")
            target = compatible[0] if action == 0 else _nearest_bet(action, compatible, all_in)
            result[target_actions.index(target)] += probability
            continue
        portion = probability / len(destinations)
        for index in destinations:
            result[index] += portion
    total = sum(result)
    if total <= 0:
        raise ValueError("source policy row has no probability mass")
    return [value / total for value in result]


def lift_policy(source: LeducGame, target: LeducGame, policy: list[list[float]]):
    """Lift a coarse policy, mapping public histories through legal coarse bets.

    An unmappable new history receives a uniform row. The returned count makes
    this loss of coverage visible in experiment reports.
    """
    if source.chips != target.chips or source.deals != target.deals or not set(source.bet_sizes) <= set(target.bet_sizes):
        raise ValueError("games must share cards/chips and have nested betting menus")
    validate_policy(source, policy)
    target_policy = target.uniform_policy()
    covered: set[int] = set()
    mapped_nodes = [-1] * len(target.nodes)
    mapped_nodes[0] = 0
    for index, node in enumerate(target.nodes):
        source_index = mapped_nodes[index]
        if source_index < 0 or node.player < 0:
            continue
        source_node = source.nodes[source_index]
        if source_node.player != node.player:
            continue
        source_actions = source.infosets[source_node.infos[0]].actions
        target_actions = target.infosets[node.infos[0]].actions
        if len(source_actions) == 1 and len(target_actions) > 1:
            continue
        for deal, target_info in enumerate(node.infos):
            source_info = source_node.infos[deal]
            if target_info not in covered:
                try:
                    target_policy[target_info] = split_action_mass(
                        source.infosets[source_info].actions, policy[source_info],
                        target.infosets[target_info].actions, source.chips,
                        source_kinds=source_node.action_kinds, target_kinds=node.action_kinds)
                except ValueError:
                    continue
                covered.add(target_info)
        for action, kind, child in zip(target_actions, node.action_kinds, node.children):
            source_action = _mapped_action(action, kind, source_actions,
                                           source_node.action_kinds, source.chips)
            if source_action is not None:
                mapped_nodes[child] = source_node.children[source_actions.index(source_action)]
    validate_policy(target, target_policy)
    return target_policy, {"covered_infosets": len(covered),
                           "total_infosets": len(target.infosets),
                           "fallback_infosets": len(target.infosets) - len(covered)}


def transfer_dcfr(source: LeducGame, target: LeducGame, source_solver: NativeFullTraversalCFR,
                  *, prior_iterations: float = 5.0, regret_scale: float = 0.001):
    """Start DCFR in the expanded game from a finite policy/average prior.

    The old average is projected into new actions. New regret rows are small
    positive values proportional to that policy, not copies of parent regrets.
    The virtual average count is capped by ``prior_iterations`` so an early
    coarse game cannot freeze adaptation in newly introduced branches.
    """
    if source_solver.variant != "dcfr" or source_solver.game is not source:
        raise ValueError("source_solver must be DCFR on the source game")
    if prior_iterations <= 0 or regret_scale <= 0:
        raise ValueError("warm-start strengths must be positive")
    policy, coverage = lift_policy(source, target, source_solver.average_policy())
    target_solver = NativeFullTraversalCFR(target, "dcfr")
    weights = [own_reach_weights(target, policy, player) for player in (0, 1)]
    for index, (info, row) in enumerate(zip(target.infosets, policy)):
        target_solver.regrets[index] = [regret_scale * probability for probability in row]
        mass = max(1e-12, prior_iterations * weights[info.player][index])
        target_solver.strategy_sums[index] = [mass * probability for probability in row]
    return target_solver, coverage
