import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
GAME_ENGINE_DIR = ROOT / "game_engine"
if str(GAME_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(GAME_ENGINE_DIR))

import random_control  # noqa: E402


class RandomControlTests(unittest.TestCase):
    def test_same_seed_produces_same_shuffle(self) -> None:
        values = [1, 2, 3, 4, 5, 6, 7]
        shuffled_a = random_control.shuffled(values, seed=42)
        shuffled_b = random_control.shuffled(values, seed=42)
        self.assertEqual(shuffled_a, shuffled_b)

    def test_different_seeds_produce_different_shuffle(self) -> None:
        values = [1, 2, 3, 4, 5, 6, 7]
        shuffled_a = random_control.shuffled(values, seed=7)
        shuffled_b = random_control.shuffled(values, seed=21)
        self.assertNotEqual(shuffled_a, shuffled_b)

    def test_seed_is_loaded_from_environment(self) -> None:
        with patch.dict(os.environ, {"POKER_ML_RANDOM_SEED": "123"}, clear=False):
            self.assertEqual(random_control.resolve_random_seed(), 123)


if __name__ == "__main__":
    unittest.main()
