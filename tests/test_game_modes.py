import unittest

from game_engine.common_types import ChipMode
from game_engine.config import build_game_config
from game_engine.game import Game


class GameModeTests(unittest.TestCase):
    def build_game(self, chip_mode: ChipMode) -> Game:
        config = build_game_config(
            num_ai_players=0,
            num_human_players=2,
            chip_mode=chip_mode,
        )
        return Game(None, "Leduc", config)

    def test_persistent_match_keeps_round_results_in_stack_sizes(self) -> None:
        game = self.build_game(ChipMode.PERSISTENT_MATCH)
        winner, loser = game.players.initial_players

        winner.set_chips(1300)
        loser.set_chips(1100)
        game.finalize_round_balances()

        self.assertEqual(winner.chips, 1300)
        self.assertEqual(loser.chips, 1100)
        self.assertEqual(winner.chip_balance, 100)
        self.assertEqual(loser.chip_balance, -100)

    def test_reset_mode_restores_initial_stacks_after_round(self) -> None:
        game = self.build_game(ChipMode.RESET_EACH_ROUND)
        winner, loser = game.players.initial_players

        winner.set_chips(1400)
        loser.set_chips(1000)
        game.finalize_round_balances()

        self.assertEqual(winner.chips, game.initial_chips)
        self.assertEqual(loser.chips, game.initial_chips)
        self.assertEqual(winner.chip_balance, 200)
        self.assertEqual(loser.chip_balance, -200)

    def test_reset_mode_uses_round_limit_for_completion(self) -> None:
        game = self.build_game(ChipMode.RESET_EACH_ROUND)
        game.round_num = game.max_rounds or 0
        self.assertTrue(game.is_finished())


if __name__ == "__main__":
    unittest.main()
