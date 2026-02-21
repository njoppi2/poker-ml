import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
GAME_ENGINE_DIR = ROOT / "game_engine"
if str(GAME_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(GAME_ENGINE_DIR))

try:
    import websockets  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    websockets_stub = types.ModuleType("websockets")
    websockets_stub.serve = lambda *args, **kwargs: None
    sys.modules["websockets"] = websockets_stub

import main as websocket_main  # noqa: E402


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
    async def test_handle_client_starts_leduc_game(self) -> None:
        websocket = _FakeWebSocket(["start-game-Leduc"])

        with patch.object(websocket_main, "simulate_poker_game", new=AsyncMock()) as mock_simulate:
            await websocket_main.handle_client(websocket, path="/")
            mock_simulate.assert_awaited_once_with(websocket, "Leduc")

    async def test_handle_client_ignores_unknown_message(self) -> None:
        websocket = _FakeWebSocket(["hello"])

        with patch.object(websocket_main, "simulate_poker_game", new=AsyncMock()) as mock_simulate:
            await websocket_main.handle_client(websocket, path="/")
            mock_simulate.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
