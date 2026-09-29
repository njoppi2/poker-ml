"""Checks for the isolated full-tree CFR experiments."""
import shutil
import unittest
import random

from game_engine.training.evaluate import evaluate
from game_engine.training.experimental_cfr import FullTraversalCFR, NativeFullTraversalCFR
from game_engine.training.game import LeducGame, MiniHoldemGame
from game_engine.training.solver import normalize


def independent_one_sweep(game, regrets, updating):
    """Small, deliberately separate reference for one exact CFR player sweep."""
    strategies = [normalize([max(0.0, x) for x in row]) for row in regrets]
    deltas = [[0.0] * len(info.actions) for info in game.infosets]

    def rec(node_id, deal, own, other):
        node = game.nodes[node_id]
        if node.player < 0:
            return node.payoffs[deal] * (1 if updating == 0 else -1)
        info, sigma = node.infos[deal], strategies[node.infos[deal]]
        if node.player == updating:
            children = [rec(child, deal, own * sigma[a], other) for a, child in enumerate(node.children)]
            value = sum(p * v for p, v in zip(sigma, children))
            for a, value_a in enumerate(children):
                deltas[info][a] += game.chance[deal] * other * (value_a - value)
            return value
        return sum(p * rec(child, deal, own, other * p) for p, child in zip(sigma, node.children))

    for deal in range(len(game.deals)):
        rec(0, deal, 1.0, 1.0)
    return [[old + delta for old, delta in zip(row, changes)] for row, changes in zip(regrets, deltas)]


class FullTraversalCFRTests(unittest.TestCase):
    def test_vanilla_sweep_matches_independent_counterfactual_reference(self):
        game = LeducGame(2)
        solver = FullTraversalCFR(game)
        # Non-uniform rows exercise regret matching as well as information-set aggregation.
        for i, row in enumerate(solver.regrets):
            solver.regrets[i] = [float((i + 2) * (a + 1) * (-1 if a == 0 else 1)) for a in range(len(row))]
        expected = independent_one_sweep(game, [row[:] for row in solver.regrets], 0)
        solver._sweep(0)
        for actual, wanted in zip(solver.regrets, expected):
            for got, expected_value in zip(actual, wanted):
                self.assertAlmostEqual(got, expected_value, places=12)

    def test_cfr_plus_keeps_only_nonnegative_cumulative_regrets(self):
        solver = FullTraversalCFR(LeducGame(2), "cfr_plus")
        for _ in range(5):
            solver.iteration()
        self.assertTrue(all(value >= 0 for row in solver.regrets for value in row))

    def test_cfr_plus_uses_iteration_number_for_linear_average_weight(self):
        solver = FullTraversalCFR(LeducGame(2), "cfr_plus")
        self.assertEqual(solver._average_weight(), 1)
        solver.iterations = 7
        self.assertEqual(solver._average_weight(), 8)

    def test_dcfr_discount_has_analytic_factors_and_skips_iteration_zero(self):
        solver = FullTraversalCFR(LeducGame(2), "dcfr")
        solver.regrets[0][:2] = [8.0, -6.0]
        solver.strategy_sums[0][:2] = [10.0, 10.0]
        solver._discount()
        self.assertEqual(solver.regrets[0][:2], [8.0, -6.0])
        self.assertEqual(solver.strategy_sums[0][:2], [10.0, 10.0])
        solver.iterations = 4
        solver._discount()
        positive = 4 ** 1.5 / (4 ** 1.5 + 1)
        average = (4 / 5) ** 2
        self.assertAlmostEqual(solver.regrets[0][0], 8 * positive)
        self.assertAlmostEqual(solver.regrets[0][1], -3.0)
        self.assertAlmostEqual(solver.strategy_sums[0][0], 10 * average)

    def test_counterfactual_deltas_match_independent_value_finite_differences(self):
        """Check signs, deal aggregation, and the distinct averaging reach.

        This evaluator intentionally does not use the training traversal.  A
        constrained policy perturbation at I has derivative
        pi_i(I) * (delta(I, action_0) - delta(I, action_1)).
        """
        game, rng = LeducGame(3), random.Random(913)
        policy = []
        for info in game.infosets:
            row = [rng.random() + .2 for _ in info.actions]
            total = sum(row)
            policy.append([value / total for value in row])

        def profile_value(rows):
            def descend(index, deal):
                node = game.nodes[index]
                if node.player < 0:
                    return node.payoffs[deal]
                return sum(rows[node.infos[deal]][action] * descend(child, deal)
                           for action, child in enumerate(node.children))
            return sum(probability * descend(0, deal) for deal, probability in enumerate(game.chance))

        def own_reach_and_chance(info_id, player):
            weighted_reach, chance_mass = 0.0, 0.0
            def descend(index, deal, own_reach):
                nonlocal weighted_reach, chance_mass
                node = game.nodes[index]
                if node.player < 0:
                    return
                info = node.infos[deal]
                if node.player == player and info == info_id:
                    weighted_reach += game.chance[deal] * own_reach
                    chance_mass += game.chance[deal]
                    return
                for action, child in enumerate(node.children):
                    descend(child, deal, own_reach * (policy[info][action] if node.player == player else 1.0))
            for deal in range(len(game.deals)):
                descend(0, deal, 1.0)
            return weighted_reach / chance_mass, chance_mass

        for player in (0, 1):
            solver = FullTraversalCFR(game)
            solver.regrets = [row[:] for row in policy]  # exact regret-matching profile
            previous_regrets = [row[:] for row in solver.regrets]
            previous_sums = [row[:] for row in solver.strategy_sums]
            solver._sweep(player)
            deltas = [[value - old for value, old in zip(row, old_row)]
                      for row, old_row in zip(solver.regrets, previous_regrets)]
            candidates = [i for i, info in enumerate(game.infosets)
                          if info.player == player and len(info.actions) > 1]
            for info_id in (candidates[0], candidates[len(candidates) // 2], candidates[-1]):
                epsilon = 1e-7
                plus, minus = [row[:] for row in policy], [row[:] for row in policy]
                plus[info_id][0] += epsilon; plus[info_id][1] -= epsilon
                minus[info_id][0] -= epsilon; minus[info_id][1] += epsilon
                numeric = (1 if player == 0 else -1) * (profile_value(plus) - profile_value(minus)) / (2 * epsilon)
                own_reach, chance_mass = own_reach_and_chance(info_id, player)
                analytic = own_reach * (deltas[info_id][0] - deltas[info_id][1])
                self.assertAlmostEqual(numeric, analytic, places=8)
                increment = [value - old for value, old in zip(solver.strategy_sums[info_id], previous_sums[info_id])]
                expected = [chance_mass * own_reach * probability for probability in policy[info_id]]
                for actual, wanted in zip(increment, expected):
                    self.assertAlmostEqual(actual, wanted, places=12)

    def test_variants_improve_over_uniform_on_small_compiled_game(self):
        game = LeducGame(2)
        initial = evaluate(game, game.uniform_policy())["exploitability"]
        for variant in ("vanilla", "cfr_plus", "dcfr"):
            with self.subTest(variant=variant):
                solver = FullTraversalCFR(game, variant)
                solver.advance(100)
                self.assertLess(evaluate(game, solver.average_policy())["exploitability"], initial)

    @unittest.skipUnless(shutil.which("cargo"), "cargo is required for native kernel parity")
    def test_native_kernel_matches_python_for_multiple_variants(self):
        game = LeducGame(2)
        for variant in ("vanilla", "cfr_plus", "dcfr"):
            with self.subTest(variant=variant):
                python = FullTraversalCFR(game, variant)
                native = NativeFullTraversalCFR(game, variant)
                try:
                    python.advance(4)
                    native.advance(4)
                    self.assertEqual(native.iterations, python.iterations)
                    self.assertEqual(native.node_visits, python.node_visits)
                    for left, right in zip(native.regrets, python.regrets):
                        for a, b in zip(left, right):
                            self.assertAlmostEqual(a, b, places=11)
                    for left, right in zip(native.strategy_sums, python.strategy_sums):
                        for a, b in zip(left, right):
                            self.assertAlmostEqual(a, b, places=11)
                finally:
                    native.close()

    @unittest.skipUnless(shutil.which("cargo"), "cargo is required for native kernel parity")
    def test_native_kernel_matches_python_with_second_public_card(self):
        game = LeducGame(3, public_cards=2, ranks=5)
        python = FullTraversalCFR(game, "dcfr")
        native = NativeFullTraversalCFR(game, "dcfr")
        try:
            python.advance(5)
            native.advance(5)
            self.assertEqual(native.iterations, python.iterations)
            self.assertEqual(native.node_visits, python.node_visits)
            for left, right in zip(native.regrets, python.regrets):
                for a, b in zip(left, right):
                    self.assertAlmostEqual(a, b, places=11)
            for left, right in zip(native.strategy_sums, python.strategy_sums):
                for a, b in zip(left, right):
                    self.assertAlmostEqual(a, b, places=11)
        finally:
            native.close()

    @unittest.skipUnless(shutil.which("cargo"), "cargo is required for native kernel parity")
    def test_native_kernel_matches_python_on_two_private_card_game(self):
        game = MiniHoldemGame(2, ranks=5)
        python = FullTraversalCFR(game, "dcfr")
        native = NativeFullTraversalCFR(game, "dcfr")
        try:
            python.advance(3)
            native.advance(3)
            self.assertEqual(native.node_visits, python.node_visits)
            for left, right in zip(native.regrets, python.regrets):
                for a, b in zip(left, right):
                    self.assertAlmostEqual(a, b, places=11)
        finally:
            native.close()


if __name__ == "__main__":
    unittest.main()
