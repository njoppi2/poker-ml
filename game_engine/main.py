import asyncio
import sys
from pathlib import Path
from typing import Optional

import websockets


def _load_game_class():
    engine_dir = Path(__file__).resolve().parent
    if str(engine_dir) not in sys.path:
        sys.path.insert(0, str(engine_dir))

    from game import Game  # Imported lazily for faster smoke tests.

    return Game


def parse_start_message(message: str) -> Optional[str]:
    game_types = {
        "start-game-Texas Hold'em": "Texas Hold'em",
        "start-game-Leduc": "Leduc",
    }
    return game_types.get(message)


async def simulate_poker_game(websocket, game_type: str, random_seed: Optional[int] = None):
    Game = _load_game_class()
    game = Game(
        websocket=websocket,
        game_type=game_type,
        num_ai_players=1,
        num_human_players=1,
        initial_chips=1200,
        increase_blind_every=0,
        random_seed=random_seed,
    )
    await game.start_game()


async def handle_client(websocket, path):
    async for message in websocket:
        selected_game_type = parse_start_message(message)
        if selected_game_type:
            await simulate_poker_game(websocket, selected_game_type)
        break


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--no-websocket":
        asyncio.run(simulate_poker_game(None, "Leduc"))
    else:
        loop = asyncio.get_event_loop()
        start_server = websockets.serve(handle_client, "0.0.0.0", 3002)
        loop.run_until_complete(start_server)
        loop.run_forever()
