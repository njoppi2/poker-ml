from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from treys import Card

from .common_types import ChipMode, serialize_enum
from .config import resolve_chip_mode

SUPPORTED_GAME_TYPES = {"Texas Hold'em", "Leduc"}
LEGACY_START_MESSAGES = {
    "start-game-Texas Hold'em": "Texas Hold'em",
    "start-game-Leduc": "Leduc",
}


@dataclass(frozen=True)
class StartGameRequest:
    game_type: str
    chip_mode: ChipMode = ChipMode.PERSISTENT_MATCH


def build_start_game_message(game_type: str, chip_mode: ChipMode | str) -> str:
    return json.dumps(
        {
            "type": "start-game",
            "gameType": game_type,
            "chipMode": resolve_chip_mode(chip_mode).value,
        }
    )


def parse_start_request(
    message: str,
    *,
    default_chip_mode: ChipMode = ChipMode.PERSISTENT_MATCH,
) -> Optional[StartGameRequest]:
    stripped_message = message.strip()
    if not stripped_message:
        return None

    legacy_game_type = LEGACY_START_MESSAGES.get(stripped_message)
    if legacy_game_type:
        return StartGameRequest(
            game_type=legacy_game_type,
            chip_mode=default_chip_mode,
        )

    try:
        payload = json.loads(stripped_message)
    except json.JSONDecodeError:
        return None

    if payload.get("type") != "start-game":
        return None

    game_type = payload.get("gameType")
    if game_type not in SUPPORTED_GAME_TYPES:
        return None

    return StartGameRequest(
        game_type=game_type,
        chip_mode=resolve_chip_mode(payload.get("chipMode"), default=default_chip_mode),
    )


def serialize_player(player: Any) -> dict[str, Any]:
    return {
        "id": player.id,
        "name": player.name,
        "chips": player.chips,
        "round_start_chips": player.round_start_chips,
        "round_end_chips": player.round_end_chips,
        "cards": [Card.int_to_str(card) for card in player.cards],
        "show_down_hand": player.show_down_hand,
        "turn_bet_value": player.turn_bet_value,
        "phase_bet_value": player.phase_bet_value,
        "round_bet_value": player.round_bet_value,
        "is_robot": player.is_robot,
        "turn_state": serialize_enum(player.turn_state),
        "played_current_phase": player.played_current_phase,
        "chip_balance": player.chip_balance,
        "chips_won_history": player.chips_won_history,
    }


def serialize_players(players: Any) -> dict[str, Any]:
    current_turn_player = (
        "EVERYONE_IN_ALL_IN"
        if players.current_turn_player is None
        else serialize_player(players.current_turn_player)
    )

    return {
        "initial_players": [serialize_player(player) for player in players.initial_players],
        "current_dealer": serialize_player(players.current_dealer),
        "current_turn_player": current_turn_player,
    }


def serialize_game_state(game: Any) -> str:
    return json.dumps(
        {
            "players": serialize_players(game.players),
            "_increase_blind_every": game._increase_blind_every,
            "round_num": game.round_num,
            "table_cards": [Card.int_to_str(card) for card in game.table_cards],
            "phase_name": serialize_enum(game.phase_name),
            "total_pot": game.total_pot,
            "min_turn_value_to_continue": game.min_turn_value_to_continue,
            "min_bet": game.min_bet,
            "chip_mode": game.chip_mode.value,
            "game_type": game.game_type,
            "game_over": game.is_game_over,
            "winner_name": game.winner_name,
        }
    )
