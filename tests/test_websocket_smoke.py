import unittest
from unittest.mock import AsyncMock, patch

from game_engine.common_types import ChipMode
from game_engine.protocol import build_start_game_message
from game_engine import server as websocket_server


class _FakeWebSocket:
    def __init__(self, messages: list[str]):
        self._messages = iter(messages)

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        try:
            return next(self._messages)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class WebsocketSmokeTests(unittest.IsolatedAsyncioTestCase):
    async def test_handle_client_starts_leduc_game_from_legacy_message(self) -> None:
        websocket = _FakeWebSocket(["start-game-Leduc"])

        with patch.object(websocket_server, "simulate_poker_game", new=AsyncMock()) as mock_simulate:
            await websocket_server.handle_client(websocket, path="/")
            args = mock_simulate.await_args.args
            self.assertEqual(args[0], websocket)
            self.assertEqual(args[1], "Leduc")
            self.assertEqual(args[2].chip_mode, ChipMode.PERSISTENT_MATCH)

    async def test_handle_client_starts_requested_chip_mode_from_json_message(self) -> None:
        websocket = _FakeWebSocket(
            [build_start_game_message("Texas Hold'em", ChipMode.RESET_EACH_ROUND)]
        )

        with patch.object(websocket_server, "simulate_poker_game", new=AsyncMock()) as mock_simulate:
            await websocket_server.handle_client(websocket, path="/")
            args = mock_simulate.await_args.args
            self.assertEqual(args[1], "Texas Hold'em")
            self.assertEqual(args[2].chip_mode, ChipMode.RESET_EACH_ROUND)

    async def test_handle_client_ignores_unknown_message(self) -> None:
        websocket = _FakeWebSocket(["hello"])

        with patch.object(websocket_server, "simulate_poker_game", new=AsyncMock()) as mock_simulate:
            await websocket_server.handle_client(websocket, path="/")
            mock_simulate.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
