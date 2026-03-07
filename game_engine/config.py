from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .common_types import ChipMode
from .random_control import resolve_random_seed

DEFAULT_INITIAL_CHIPS = 1200
DEFAULT_RESET_ROUND_LIMIT = 10
DEFAULT_RUNTIME_MODEL_NAME = "IOu-mccfr-6cards-11maxbet-EPcfr0_0-mRW0_0-iter100000000.pkl"
DEFAULT_RUNTIME_MODEL_PATH = (
    Path(__file__).resolve().parent / "models" / "runtime" / DEFAULT_RUNTIME_MODEL_NAME
)


@dataclass(frozen=True)
class GameConfig:
    num_ai_players: int = 1
    num_human_players: int = 1
    initial_chips: int = DEFAULT_INITIAL_CHIPS
    increase_blind_every: int = 0
    chip_mode: ChipMode = ChipMode.PERSISTENT_MATCH
    model_path: Path = field(default_factory=lambda: DEFAULT_RUNTIME_MODEL_PATH)
    random_seed: Optional[int] = None
    max_rounds: Optional[int] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_path", Path(self.model_path))


@dataclass(frozen=True)
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 3002
    game_config: GameConfig = field(default_factory=GameConfig)


def resolve_chip_mode(
    raw_value: ChipMode | str | None,
    *,
    default: ChipMode = ChipMode.PERSISTENT_MATCH,
) -> ChipMode:
    if isinstance(raw_value, ChipMode):
        return raw_value
    if raw_value is None:
        return default

    normalized_value = raw_value.strip().lower()
    for chip_mode in ChipMode:
        if chip_mode.value == normalized_value:
            return chip_mode

    return default


def resolve_model_path(raw_value: str | Path | None = None) -> Path:
    if raw_value is None or str(raw_value).strip() == "":
        return DEFAULT_RUNTIME_MODEL_PATH

    return Path(raw_value).expanduser().resolve()


def resolve_max_rounds(raw_value: str | int | None, chip_mode: ChipMode) -> Optional[int]:
    if raw_value is None or raw_value == "":
        if chip_mode == ChipMode.RESET_EACH_ROUND:
            return DEFAULT_RESET_ROUND_LIMIT
        return None

    return int(raw_value)


def build_game_config(
    *,
    num_ai_players: int = 1,
    num_human_players: int = 1,
    initial_chips: int = DEFAULT_INITIAL_CHIPS,
    increase_blind_every: int = 0,
    chip_mode: ChipMode | str | None = None,
    model_path: str | Path | None = None,
    random_seed: Optional[int] = None,
    max_rounds: str | int | None = None,
) -> GameConfig:
    resolved_chip_mode = resolve_chip_mode(chip_mode)

    return GameConfig(
        num_ai_players=num_ai_players,
        num_human_players=num_human_players,
        initial_chips=initial_chips,
        increase_blind_every=increase_blind_every,
        chip_mode=resolved_chip_mode,
        model_path=resolve_model_path(model_path),
        random_seed=random_seed,
        max_rounds=resolve_max_rounds(max_rounds, resolved_chip_mode),
    )


def load_server_config() -> ServerConfig:
    chip_mode = resolve_chip_mode(os.getenv("POKER_ML_CHIP_MODE"))

    game_config = build_game_config(
        num_ai_players=int(os.getenv("POKER_ML_NUM_AI_PLAYERS", "1")),
        num_human_players=int(os.getenv("POKER_ML_NUM_HUMAN_PLAYERS", "1")),
        initial_chips=int(os.getenv("POKER_ML_INITIAL_CHIPS", str(DEFAULT_INITIAL_CHIPS))),
        increase_blind_every=int(os.getenv("POKER_ML_INCREASE_BLIND_EVERY", "0")),
        chip_mode=chip_mode,
        model_path=os.getenv("POKER_ML_MODEL_PATH"),
        random_seed=resolve_random_seed(),
        max_rounds=os.getenv("POKER_ML_MAX_ROUNDS"),
    )

    return ServerConfig(
        host=os.getenv("POKER_ML_WS_HOST", "0.0.0.0"),
        port=int(os.getenv("POKER_ML_WS_PORT", "3002")),
        game_config=game_config,
    )
