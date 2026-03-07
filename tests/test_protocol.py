import unittest

from game_engine.common_types import ChipMode
from game_engine.protocol import build_start_game_message, parse_start_request


class ProtocolTests(unittest.TestCase):
    def test_parse_start_request_reads_json_message(self) -> None:
        request = parse_start_request(
            build_start_game_message("Leduc", ChipMode.RESET_EACH_ROUND)
        )

        self.assertIsNotNone(request)
        self.assertEqual(request.game_type, "Leduc")
        self.assertEqual(request.chip_mode, ChipMode.RESET_EACH_ROUND)

    def test_parse_start_request_preserves_default_chip_mode_for_legacy_message(self) -> None:
        request = parse_start_request(
            "start-game-Texas Hold'em",
            default_chip_mode=ChipMode.RESET_EACH_ROUND,
        )

        self.assertIsNotNone(request)
        self.assertEqual(request.game_type, "Texas Hold'em")
        self.assertEqual(request.chip_mode, ChipMode.RESET_EACH_ROUND)

    def test_parse_start_request_rejects_unknown_payload(self) -> None:
        self.assertIsNone(parse_start_request('{"type":"ping"}'))


if __name__ == "__main__":
    unittest.main()
