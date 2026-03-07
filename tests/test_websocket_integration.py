import asyncio
import json
import socket
import unittest
from contextlib import suppress
from unittest.mock import patch

import websockets

from game_engine.common_types import ChipMode
from game_engine.config import ServerConfig, build_game_config
from game_engine.protocol import build_start_game_message
from game_engine.server import run_server


class _AlwaysCallPolicy:
    def __init__(self, *, model_path, rng):
        self.model_path = model_path
        self.rng = rng

    def decide_next_action(self, infoset: str) -> str:
        return "c"


def _get_open_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class WebsocketIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.policy_patch = patch("game_engine.game.NashBlueprintPolicy", _AlwaysCallPolicy)
        self.policy_patch.start()

    async def asyncTearDown(self) -> None:
        self.policy_patch.stop()

    async def _wait_until_server_starts(self, websocket_url: str) -> None:
        for _ in range(50):
            try:
                async with websockets.connect(websocket_url):
                    return
            except OSError:
                await asyncio.sleep(0.05)

        self.fail("websocket server did not start in time")

    async def _run_session(self, game_type: str, chip_mode: ChipMode) -> dict[str, object]:
        initial_chips = 100 if game_type == "Leduc" else 20
        max_rounds = 1 if chip_mode == ChipMode.RESET_EACH_ROUND else None
        port = _get_open_port()
        server_config = ServerConfig(
            host="127.0.0.1",
            port=port,
            game_config=build_game_config(
                num_ai_players=2,
                num_human_players=0,
                chip_mode=chip_mode,
                initial_chips=initial_chips,
                max_rounds=max_rounds,
            ),
        )
        server_task = asyncio.create_task(run_server(server_config))
        messages = []
        websocket_url = f"ws://127.0.0.1:{port}"

        try:
            await self._wait_until_server_starts(websocket_url)

            async with websockets.connect(websocket_url) as websocket:
                await websocket.send(build_start_game_message(game_type, chip_mode))

                for _ in range(30):
                    payload = json.loads(await asyncio.wait_for(websocket.recv(), timeout=5))
                    messages.append(payload)
                    if payload["game_over"]:
                        break
        finally:
            server_task.cancel()
            with suppress(asyncio.CancelledError):
                await server_task

        self.assertTrue(messages)
        return messages[-1]

    async def test_server_supports_all_start_modes(self) -> None:
        scenarios = [
            ("Leduc", ChipMode.PERSISTENT_MATCH),
            ("Leduc", ChipMode.RESET_EACH_ROUND),
            ("Texas Hold'em", ChipMode.PERSISTENT_MATCH),
            ("Texas Hold'em", ChipMode.RESET_EACH_ROUND),
        ]

        for game_type, chip_mode in scenarios:
            with self.subTest(game_type=game_type, chip_mode=chip_mode.value):
                final_payload = await self._run_session(game_type, chip_mode)
                self.assertEqual(final_payload["chip_mode"], chip_mode.value)
                self.assertEqual(final_payload["game_type"], game_type)
                self.assertTrue(final_payload["game_over"])
                self.assertIn("winner_name", final_payload)


if __name__ == "__main__":
    unittest.main()
