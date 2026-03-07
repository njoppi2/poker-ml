import os
import unittest
from pathlib import Path
from unittest.mock import patch

from game_engine.common_types import ChipMode
from game_engine.config import (
    DEFAULT_RESET_ROUND_LIMIT,
    DEFAULT_RUNTIME_MODEL_PATH,
    load_server_config,
    resolve_chip_mode,
    resolve_model_path,
)


class ConfigTests(unittest.TestCase):
    def test_resolve_chip_mode_falls_back_to_default(self) -> None:
        self.assertEqual(resolve_chip_mode("unknown"), ChipMode.PERSISTENT_MATCH)

    def test_resolve_model_path_uses_runtime_default(self) -> None:
        self.assertEqual(resolve_model_path(), DEFAULT_RUNTIME_MODEL_PATH)

    def test_load_server_config_uses_reset_defaults(self) -> None:
        with patch.dict(
            os.environ,
            {
                "POKER_ML_CHIP_MODE": ChipMode.RESET_EACH_ROUND.value,
                "POKER_ML_MODEL_PATH": str(Path("/tmp/model.pkl")),
                "POKER_ML_RANDOM_SEED": "123",
            },
            clear=False,
        ):
            config = load_server_config()

        self.assertEqual(config.game_config.chip_mode, ChipMode.RESET_EACH_ROUND)
        self.assertEqual(config.game_config.max_rounds, DEFAULT_RESET_ROUND_LIMIT)
        self.assertEqual(config.game_config.model_path, Path("/tmp/model.pkl"))
        self.assertEqual(config.game_config.random_seed, 123)


if __name__ == "__main__":
    unittest.main()
