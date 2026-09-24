"""Optional independent checks; CI installs the training-reference extra."""
import importlib.util
import random
import unittest
from unittest.mock import patch

from game_engine.training.evaluate import evaluate
from game_engine.training.game import LeducGame
from game_engine.training.solver import ExternalSampling


@unittest.skipUnless(importlib.util.find_spec('pyspiel'), 'install .[training-reference] for OpenSpiel checks')
class ReferenceTests(unittest.TestCase):
    def test_best_response_matches_openspiel_with_hidden_cards(self):
        from game_engine.training.reference import SpielGame, SpielPolicy
        from open_spiel.python.algorithms import exploitability
        for chips in (2, 4):
            game = LeducGame(chips)
            reference_game = SpielGame(game)
            rng = random.Random(47)
            for seed in range(4):
                rows = game.uniform_policy()
                if seed:
                    for i, row in enumerate(rows):
                        weights = [rng.random() for _ in row]
                        rows[i] = [p / sum(weights) for p in weights]
                reference = exploitability.exploitability(reference_game, SpielPolicy(reference_game, rows))
                self.assertAlmostEqual(evaluate(game, rows)['exploitability'], reference, places=10)

    def test_updates_match_openspiel_on_identical_samples(self):
        import numpy as np
        from game_engine.training.reference import SpielGame
        from open_spiel.python.algorithms import external_sampling_mccfr

        class ZeroInitializedReference(external_sampling_mccfr.ExternalSamplingSolver):
            def _lookup_infostate_info(self, key, count):
                if key not in self._infostates:
                    self._infostates[key] = [np.zeros(count), np.zeros(count)]
                return self._infostates[key]

        for chips in (2, 4):
            game = LeducGame(chips)
            ours = ExternalSampling(game, 42)
            reference = ZeroInitializedReference(SpielGame(game))
            rng = random.Random(42)
            def choose(actions, p):
                return rng.choices(list(actions), list(p))[0]
            with patch.object(external_sampling_mccfr.np.random, 'choice', side_effect=choose):
                for _ in range(20):
                    ours.iteration()
                    reference.iteration()
                    for key, (regrets, average) in reference._infostates.items():
                        info = game.info_by_key[key]
                        np.testing.assert_allclose(ours.regrets[info], regrets, atol=1e-12, rtol=1e-12)
                        np.testing.assert_allclose(ours.strategy_sums[info], average, atol=1e-12, rtol=1e-12)
                    self.assertEqual(ours.rng.getstate(), rng.getstate())


if __name__ == '__main__':
    unittest.main()
