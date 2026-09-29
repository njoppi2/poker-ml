"""Action abstraction transfer checks on the exact small game."""
import math
import shutil
import unittest

from game_engine.training.action_curriculum import _mapped_action, lift_policy, split_action_mass, transfer_dcfr
from game_engine.training.evaluate import evaluate
from game_engine.training.experimental_cfr import NativeFullTraversalCFR
from game_engine.training.game import LeducGame


class ActionCurriculumTests(unittest.TestCase):
    def test_split_partitions_parent_bet_probability(self):
        source = (0, 4)
        target = (0, 2, 3, 4)
        result = split_action_mass(source, [0.4, 0.6], target, 4)
        for actual, expected in zip(result, (0.4, 0.2, 0.2, 0.2)):
            self.assertAlmostEqual(actual, expected)
        self.assertAlmostEqual(sum(result), 1.0)

    def test_lift_covers_shared_history_and_exposes_fallback(self):
        source, target = LeducGame(4, (4,)), LeducGame(4)
        policy = source.uniform_policy()
        for info, row in zip(source.infosets, policy):
            if len(row) > 1:
                row[:] = [0.4, 0.6]
        lifted, coverage = lift_policy(source, target, policy)
        self.assertEqual(coverage["total_infosets"], len(target.infosets))
        self.assertGreater(coverage["covered_infosets"], 0)
        self.assertGreater(coverage["fallback_infosets"], 0)
        for info in target.nodes[0].infos:
            for actual, expected in zip(lifted[info], (0.4, 0.2, 0.2, 0.2)):
                self.assertAlmostEqual(actual, expected)
        self.assertTrue(math.isfinite(evaluate(target, lifted)["exploitability"]))

    def test_lift_keeps_a_raise_separate_from_a_call_of_the_same_size(self):
        source, target = LeducGame(6, (3, 6)), LeducGame(6)
        # After check/bet 2, the fine action 3 is a raise. After check/bet 3,
        # coarse action 3 is a call. Its mass must go to fine call 2 instead.
        source_info = source.info_by_key["kr300:|Q"]
        target_info = target.info_by_key["kr200:|Q"]
        source_node = next(node for node in source.nodes
                           if node.player >= 0 and source.infosets[node.infos[0]].key == "kr300:|Q")
        self.assertEqual(source_node.action_kinds, ("f", "c", "r"))
        policy = source.uniform_policy()
        policy[source_info] = [0.1, 0.8, 0.1]
        self.assertEqual(_mapped_action(3, "r", (0, 3, 6), ("f", "c", "r"), 6), 6)
        lifted, coverage = lift_policy(source, target, policy)
        self.assertGreater(coverage["covered_infosets"], 0)
        for actual, expected in zip(lifted[target_info], (0.1, 0.8, 0.025, 0.025, 0.025, 0.025)):
            self.assertAlmostEqual(actual, expected)

    def test_role_without_legal_coarse_equivalent_is_not_silently_relabelled(self):
        with self.assertRaises(ValueError):
            split_action_mass((0, 3), [0.5, 0.5], (0, 2, 3), 6,
                              source_kinds=("f", "c"), target_kinds=("f", "c", "r"))

    def test_unrepresented_coarse_raise_stays_with_fine_raises(self):
        row = split_action_mass((0, 3, 6, 8), [0.1, 0.2, 0.3, 0.4], (0, 4, 9), 10,
                                source_kinds=("f", "c", "r", "r"),
                                target_kinds=("f", "c", "r"))
        for actual, expected in zip(row, (0.1, 0.2, 0.7)):
            self.assertAlmostEqual(actual, expected)

    @unittest.skipUnless(shutil.which("cargo"), "Rust toolchain is required")
    def test_dcfr_transfer_starts_from_lifted_average_without_copying_regrets(self):
        source, target = LeducGame(4, (2, 4)), LeducGame(4)
        coarse = NativeFullTraversalCFR(source, "dcfr")
        expanded = None
        try:
            coarse.advance(20)
            expected, _ = lift_policy(source, target, coarse.average_policy())
            expanded, coverage = transfer_dcfr(source, target, coarse)
            self.assertGreater(coverage["covered_infosets"], 0)
            self.assertEqual(expanded.iterations, 0)
            for predicted, actual in zip(expected, expanded.average_policy()):
                for left, right in zip(predicted, actual):
                    self.assertAlmostEqual(left, right, places=12)
            self.assertTrue(all(0 <= regret <= 0.001 for row in expanded.regrets for regret in row))
            expanded.advance(2)
            self.assertTrue(math.isfinite(evaluate(target, expanded.average_policy())["exploitability"]))
        finally:
            coarse.close()
            if expanded is not None:
                expanded.close()

    def test_rejects_invalid_betting_menus(self):
        for bets in ((2, 4), (4, 2), (3, 3, 4), (1, 4), (True, 4), ()):
            with self.subTest(bets=bets), self.assertRaises(ValueError):
                LeducGame(5, bets)

    @unittest.skipUnless(shutil.which("cargo"), "Rust toolchain is required")
    def test_full_fourteen_chip_menu_runs_in_native_dcfr(self):
        game = LeducGame(14)
        self.assertEqual(game.bet_sizes, tuple(range(2, 15)))
        self.assertEqual(game.infosets[game.nodes[0].infos[0]].actions, (0, *range(2, 15)))
        solver = NativeFullTraversalCFR(game, "dcfr")
        try:
            solver.advance(1)
            self.assertEqual(solver.iterations, 1)
            self.assertEqual(len(solver.average_policy()), len(game.infosets))
        finally:
            solver.close()


if __name__ == "__main__":
    unittest.main()
