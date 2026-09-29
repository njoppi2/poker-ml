"""Coarse-to-fine bet-size transfer for sampled full-board Hold'em."""
from __future__ import annotations

from .solver import normalize


def _project_row(source_actions, source_kinds, source_row, target_actions, target_kinds):
    """Split each source action's mass across its nearest same-role target actions."""
    if len(source_actions) != len(source_kinds) or len(source_actions) != len(source_row):
        raise ValueError("source actions, roles, and policy must have equal lengths")
    if len(target_actions) != len(target_kinds) or not target_actions:
        raise ValueError("target actions and roles must have equal lengths")
    buckets = [[] for _ in source_actions]
    for target_index, (target_action, target_kind) in enumerate(zip(target_actions, target_kinds)):
        candidates = [i for i, kind in enumerate(source_kinds) if kind == target_kind]
        if not candidates:
            candidates = list(range(len(source_actions)))
        parent = min(candidates, key=lambda i: (abs(source_actions[i] - target_action), i))
        buckets[parent].append(target_index)
    result = [0.0] * len(target_actions)
    for source_index, (probability, bucket) in enumerate(zip(source_row, buckets)):
        if bucket:
            share = probability / len(bucket)
            for index in bucket:
                result[index] += share
        else:
            # Preserve mass if a coarse action's semantic role vanished in the target.
            index = min(range(len(target_actions)),
                        key=lambda i: (abs(target_actions[i] - source_actions[source_index]), i))
            result[index] += probability
    return normalize(result)


def seed_expanded_solver(source, target, *, prior_iterations=5.0, regret_scale=0.001):
    """Project visited source rows into matching target histories, lazily by key.

    Coarse bet histories remain legal in the expanded game, so those information
    sets transfer directly. New histories created by newly added sizes start from
    the target solver's uniform policy when first sampled.
    """
    if source.game.chips != target.game.chips or not set(source.game.bet_sizes) <= set(target.game.bet_sizes):
        raise ValueError("target must preserve chips and contain every source bet size")
    if prior_iterations <= 0 or regret_scale <= 0:
        raise ValueError("prior strength and regret scale must be positive")
    target_nodes = {node.history: node for node in target.game.nodes if node.player >= 0}
    transferred = 0
    for index, info in enumerate(source.game.infosets):
        target_node = target_nodes.get(info.key.split(":|", 1)[0])
        if target_node is None or target_node.player != info.player:
            continue
        row = normalize(source.strategy_sums[index])
        target.seed_policies[info.key] = _project_row(
            info.actions, source.game.info_action_kinds[index], row,
            target_node.actions, target_node.action_kinds,
        )
        transferred += 1
    target.seed_iterations = prior_iterations
    target.seed_regret_scale = regret_scale
    return {"transferred_infosets": transferred,
            "source_visited_infosets": len(source.game.infosets),
            "fallback_infosets": len(source.game.infosets) - transferred}
