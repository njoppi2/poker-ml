import unittest

from game_engine.training.sampled_curriculum import _project_row, seed_expanded_solver
from game_engine.training.sampled_holdem import ExternalSamplingHoldemCFR, SampledHoldemGame


class SampledCurriculumTests(unittest.TestCase):
    def test_projection_splits_mass_without_duplication(self):
        row = _project_row((0, 4, 8), ("k", "raise", "raise"),
                           (0.2, 0.6, 0.2), (0, 2, 3, 4, 6, 8),
                           ("k", "raise", "raise", "raise", "raise", "raise"))
        self.assertAlmostEqual(sum(row), 1.0)
        self.assertAlmostEqual(row[0], 0.2)
        self.assertAlmostEqual(sum(row[1:5]), 0.6)
        self.assertAlmostEqual(row[5], 0.2)

    def test_coarse_policy_seeds_matching_expanded_histories(self):
        coarse_game = SampledHoldemGame(6, (4, 6))
        coarse = ExternalSamplingHoldemCFR(coarse_game, seed=17)
        coarse.advance(10)
        fine_game = SampledHoldemGame(6, (2, 3, 4, 5, 6))
        fine = ExternalSamplingHoldemCFR(fine_game, seed=19)
        coverage = seed_expanded_solver(coarse, fine)
        self.assertEqual(coverage["transferred_infosets"], coverage["source_visited_infosets"])
        self.assertGreater(len(fine.seed_policies), 0)
        fine.advance(1)
        self.assertEqual(fine.iterations, 1)
        self.assertTrue(all(abs(sum(row) - 1.0) < 1e-12
                            for row in fine.policy_by_key().values()))

    def test_rejects_expansion_that_removes_a_coarse_size(self):
        coarse = ExternalSamplingHoldemCFR(SampledHoldemGame(6, (4, 6)))
        fine = ExternalSamplingHoldemCFR(SampledHoldemGame(6, (2, 6)))
        with self.assertRaises(ValueError):
            seed_expanded_solver(coarse, fine)


if __name__ == "__main__":
    unittest.main()
