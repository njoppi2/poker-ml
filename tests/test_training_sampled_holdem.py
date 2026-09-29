import math
import random
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from game_engine.training.sampled_holdem import (
    ExternalSamplingHoldemCFR,
    SampledHoldemGame,
    evaluate_sampled,
    main,
)


class SampledHoldemTests(unittest.TestCase):
    def test_configurable_larger_rank_and_suit_deck(self):
        game = SampledHoldemGame(6, (4, 6), ranks=8, suits=4)
        deal = game.sample_deal(random.Random(7))
        self.assertEqual(game.ranks, 8)
        self.assertEqual(game.suits, 4)
        self.assertTrue(all(0 <= card < 32 for card in deal))
        self.assertEqual(len(set(deal)), 9)
        self.assertIn("h", game._card_label(2))

    def test_full_deck_and_wheel_straight_strength(self):
        game = SampledHoldemGame(6, (4, 6), ranks=13, suits=4)
        wheel = (12 * 4, 0, 1 * 4 + 1, 2 * 4 + 2, 3 * 4 + 3)
        six_high = (1 * 4, 2 * 4 + 1, 3 * 4 + 2, 4 * 4 + 3, 5 * 4)
        self.assertEqual(game._five_card_strength(wheel), (4, 3))
        self.assertGreater(game._five_card_strength(six_high), game._five_card_strength(wheel))

    def test_later_street_information_reveals_only_public_cards(self):
        game = SampledHoldemGame(4, (2, 4))
        deal_a = (0, 1, 2, 3, 4, 5, 6, 7, 8)
        deal_b = (0, 1, 10, 11, 4, 5, 6, 8, 9)
        root = game.nodes[0]
        flop = next(node for node in game.nodes if node.player >= 0 and node.phase == "flop")
        turn = next(node for node in game.nodes if node.player >= 0 and node.phase == "turn")
        river = next(node for node in game.nodes if node.player >= 0 and node.phase == "river")
        self.assertEqual(game.info_key(root, deal_a), game.info_key(root, deal_b))
        self.assertEqual(game.info_key(flop, deal_a), game.info_key(flop, deal_b))
        self.assertNotEqual(game.info_key(turn, deal_a), game.info_key(turn, deal_b))
        self.assertNotEqual(game.info_key(river, deal_a), game.info_key(river, deal_b))

    def test_sampled_cfr_learns_lazy_rows_and_evaluates_a_fixed_sample(self):
        game = SampledHoldemGame(4, (2, 4))
        solver = ExternalSamplingHoldemCFR(game, seed=7)
        deal = game.sample_deal(random.Random(11))
        self.assertEqual(len(deal), 9)
        self.assertEqual(len(set(deal)), 9)
        solver.advance(200)
        policy = solver.policy_by_key()
        self.assertTrue(policy)
        self.assertTrue(all(math.isclose(sum(row), 1.0) for row in policy.values()))
        result = evaluate_sampled(solver, samples=64, seed=123)
        self.assertEqual(result["evaluation_samples"], 64)
        self.assertTrue(math.isfinite(result["exploitability"]))
        self.assertGreater(solver.node_visits, 0)

    def test_cli_writes_sampled_metrics_and_summary(self):
        with tempfile.TemporaryDirectory(prefix="sampled-holdem-test-") as folder:
            output = Path(folder) / "run"
            with contextlib.redirect_stdout(io.StringIO()):
                main(["--chips", "2", "--bet-sizes", "2", "--iterations", "2",
                      "--eval-every", "1", "--eval-samples", "8", "--output", str(output)])
            self.assertEqual((output / "metrics.jsonl").read_text().count("\n"), 3)
            summary = (output / "summary.json").read_text()
            self.assertIn('"game": "sampled-holdem"', summary)


if __name__ == "__main__":
    unittest.main()
