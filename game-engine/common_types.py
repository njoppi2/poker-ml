from enum import Enum
from typing import List, Literal, Tuple

PlayerGroups = Literal["all", "non_broke", "can_bet_in_current_turn", "can_win_round"]

class Phases(Enum):
    PRE_FLOP = "PRE_FLOP"
    FLOP = "FLOP"
    TURN = "TURN"
    RIVER = "RIVER"
