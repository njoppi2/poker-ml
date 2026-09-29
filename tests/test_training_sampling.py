"""Checks for experimental sampled estimators, separate from production training."""
import shutil
import unittest

from game_engine.training.game import LeducGame
from game_engine.training.solver import ExternalSampling
from game_engine.training.experimental_sampling import SampledVariant


@unittest.skipUnless(shutil.which("cargo"), "Rust toolchain is required")
class SampledVariantTests(unittest.TestCase):
    def test_plain_and_zero_baseline_match_existing_estimator(self):
        game = LeducGame(4)
        for seed in (7, 42, 2718):
            reference = ExternalSampling(game, seed)
            for _ in range(100):
                reference.iteration()
            for mode in ("plain", "vr"):
                solver = SampledVariant(game, seed, mode, baseline_rate=0)
                try:
                    solver.advance(100)
                    self.assertEqual(reference.rng.getstate(), solver.rng.getstate())
                    for left, right in zip(reference.regrets, solver.regrets):
                        for a, b in zip(left, right):
                            # Python 3.12+ uses a compensated sum; Rust preserves
                            # the original Python 3.10 sequential f64 arithmetic.
                            self.assertAlmostEqual(a, b, places=10)
                    for left, right in zip(reference.strategy_sums, solver.strategy_sums):
                        for a, b in zip(left, right):
                            self.assertAlmostEqual(a, b, places=10)
                finally:
                    solver.close()

    def test_linear_weighting_matches_independent_python_discounting(self):
        game = LeducGame(3)
        reference = ExternalSampling(game, 13)
        native = SampledVariant(game, 13, "linear")
        try:
            for t in range(1, 31):
                reference.iteration()
                # Discount after the update: stored table = weighted sum/(t+1).
                for table in (reference.regrets, reference.strategy_sums):
                    for row in table:
                        for a in range(len(row)):
                            row[a] *= t / (t + 1)
            native.advance(30)
            for left, right in zip(reference.regrets, native.regrets):
                for a, b in zip(left, right):
                    self.assertAlmostEqual(a, b / 31, places=10)
            for left, right in zip(reference.average_policy(), native.average_policy()):
                for a, b in zip(left, right):
                    self.assertAlmostEqual(a, b, places=10)
        finally:
            native.close()

    def test_vr_baselines_and_state_survive_batch_boundaries(self):
        game = LeducGame(4)
        for mode in ("vr", "vr-linear"):
            direct = SampledVariant(game, 99, mode)
            segmented = SampledVariant(game, 99, mode)
            try:
                direct.advance(200)
                segmented.advance(70)
                segmented.advance(130)
                self.assertEqual(direct.state_dict(), segmented.state_dict())
                self.assertIsNotNone(direct.state_dict()["baselines"])
            finally:
                direct.close()
                segmented.close()
