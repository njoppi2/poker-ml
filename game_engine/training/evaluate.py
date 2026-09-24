"""Exact two-player best responses, respecting hidden information.

At each public history, aggregate counterfactual values across ALL hidden deals
in an information set before maximizing. Maximizing per deal would cheat by
seeing the opponent's private card. Enumerates all 120 physical deals through
24 weighted rank triples; no Monte Carlo evaluation noise.
"""
import math

from .game import LeducGame


def validate_policy(game, policy):
    if len(policy) != len(game.infosets):
        raise ValueError("policy information-set count does not match game")
    for info, row in zip(game.infosets, policy):
        if len(row) != len(info.actions) or any(not math.isfinite(p) or p < 0 for p in row):
            raise ValueError(f"invalid policy probabilities at {info.key}")
        if not math.isclose(sum(row), 1.0, abs_tol=1e-9):
            raise ValueError(f"policy does not sum to one at {info.key}")


def _best_response(game, policy, responder):
    reaches = [None] * len(game.nodes)
    reaches[0] = game.chance
    for index, node in enumerate(game.nodes):
        if node.player < 0:
            continue
        reach = reaches[index]
        for action, child in enumerate(node.children):
            reaches[child] = (
                reach if node.player == responder else
                tuple(r * policy[info][action] for r, info in zip(reach, node.infos))
            )

    values = [None] * len(game.nodes)
    sign = 1 if responder == 0 else -1
    for index in range(len(game.nodes) - 1, -1, -1):
        node = game.nodes[index]
        if node.player < 0:
            values[index] = tuple(sign * value for value in node.payoffs)
        elif node.player == responder:
            scores = {info: [0.0] * len(node.children) for info in node.infos}
            for action, child in enumerate(node.children):
                for info, reach, value in zip(node.infos, reaches[index], values[child]):
                    scores[info][action] += reach * value
            choices = {info: max(range(len(row)), key=row.__getitem__) for info, row in scores.items()}
            values[index] = tuple(values[node.children[choices[info]]][deal] for deal, info in enumerate(node.infos))
        else:
            values[index] = tuple(
                sum(policy[info][action] * values[child][deal] for action, child in enumerate(node.children))
                for deal, info in enumerate(node.infos)
            )
        for child in node.children:
            values[child] = None
    return sum(p * value for p, value in zip(game.chance, values[0]))


def expected_value(game, policy):
    values = [None] * len(game.nodes)
    for index in range(len(game.nodes) - 1, -1, -1):
        node = game.nodes[index]
        if node.player < 0:
            values[index] = node.payoffs
        else:
            values[index] = tuple(
                sum(policy[info][action] * values[child][deal] for action, child in enumerate(node.children))
                for deal, info in enumerate(node.infos)
            )
        for child in node.children:
            values[child] = None
    return sum(p * value for p, value in zip(game.chance, values[0]))


def evaluate(game: LeducGame, policy):
    validate_policy(game, policy)
    br0 = _best_response(game, policy, 0)
    br1 = _best_response(game, policy, 1)
    nash_conv = br0 + br1
    return {
        "value_p0": expected_value(game, policy),
        "best_response_p0": br0,
        "best_response_p1": br1,
        "nash_conv": nash_conv,
        "exploitability": nash_conv / 2,
    }
