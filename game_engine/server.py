from __future__ import annotations

import asyncio
from dataclasses import replace

import websockets

from .config import GameConfig, ServerConfig, build_game_config, load_server_config
from .game import Game
from .protocol import parse_start_request


async def simulate_poker_game(
    websocket,
    game_type: str,
    config: GameConfig,
) -> None:
    game = Game(
        websocket=websocket,
        game_type=game_type,
        config=config,
    )
    await game.start_game()


async def handle_client(websocket, path=None, *, server_config: ServerConfig | None = None):
    active_server_config = server_config or load_server_config()

    async for message in websocket:
        request = parse_start_request(
            message,
            default_chip_mode=active_server_config.game_config.chip_mode,
        )
        if request is not None:
            base_config = active_server_config.game_config
            session_max_rounds = (
                base_config.max_rounds
                if base_config.chip_mode == request.chip_mode
                else build_game_config(chip_mode=request.chip_mode).max_rounds
            )
            session_config = replace(
                base_config,
                chip_mode=request.chip_mode,
                max_rounds=session_max_rounds,
            )
            await simulate_poker_game(websocket, request.game_type, session_config)
        break


async def run_server(server_config: ServerConfig | None = None) -> None:
    active_server_config = server_config or load_server_config()

    async def websocket_handler(websocket, path=None):
        await handle_client(websocket, path=path, server_config=active_server_config)

    async with websockets.serve(
        websocket_handler,
        active_server_config.host,
        active_server_config.port,
    ):
        await asyncio.Future()
