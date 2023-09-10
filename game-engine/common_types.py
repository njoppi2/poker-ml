from enum import Enum
from typing import List, Literal, Tuple
from card import Card
import json

PlayerGroups = Literal["all", "non_broke", "can_bet_in_current_turn", "active_in_hand", "all_in"]

class Phases(Enum):
    PRE_FLOP = "PRE_FLOP"
    FLOP = "FLOP"
    TURN = "TURN"
    RIVER = "RIVER"

class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, Card):
            return {
                "value": str(obj.value),
                "suit": str(obj.suit)
            }
        return super().default(obj)
