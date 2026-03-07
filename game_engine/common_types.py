from enum import Enum
from typing import Literal

PlayerGroups = Literal["all", "non_broke", "can_bet_in_current_turn", "active_in_hand", "all_in", "human", "not_human"]

class PokerPhases(str, Enum):
    PRE_FLOP = "PRE_FLOP"
    FLOP = "FLOP"
    TURN = "TURN"
    RIVER = "RIVER"

class LeducPhases(str, Enum):
    PRE_FLOP = "PRE_FLOP"
    FLOP = "FLOP"

class ChipMode(str, Enum):
    PERSISTENT_MATCH = "persistent_match"
    RESET_EACH_ROUND = "reset_each_round"


def serialize_enum(value):
    if isinstance(value, Enum):
        return value.value
    return value
