from __future__ import annotations

import argparse
import asyncio

from .common_types import ChipMode
from .config import build_game_config, load_server_config, resolve_chip_mode
from .server import run_server, simulate_poker_game


def parse_start_message(message: str) -> str | None:
    from .protocol import parse_start_request

    request = parse_start_request(message)
    return None if request is None else request.game_type


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Poker ML websocket server or a local AI simulation.")
    parser.add_argument("--no-websocket", action="store_true", help="Run a local AI-only simulation.")
    parser.add_argument("--game-type", default="Leduc", choices=["Leduc", "Texas Hold'em"])
    parser.add_argument(
        "--chip-mode",
        default=ChipMode.PERSISTENT_MATCH.value,
        choices=[chip_mode.value for chip_mode in ChipMode],
    )
    parser.add_argument("--random-seed", type=int, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    chip_mode = resolve_chip_mode(args.chip_mode)

    if args.no_websocket:
        game_config = build_game_config(
            num_ai_players=2,
            num_human_players=0,
            chip_mode=chip_mode,
            random_seed=args.random_seed,
        )
        asyncio.run(simulate_poker_game(None, args.game_type, game_config))
        return

    server_config = load_server_config()
    asyncio.run(run_server(server_config))


if __name__ == "__main__":
    main()
