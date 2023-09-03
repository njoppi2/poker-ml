from typing import List
from card import Card

class Player:
    def __init__(self, player_id: int, name: str, chips: int, is_human=False):
        self.id = player_id
        self.name = name
        self.chips = chips
        self.round_start_chips = chips
        self.round_end_chips = chips
        self.cards: List[Card] = []
        self.current_round_chips_invested = 0
        self.show_down_hand = {
            "hand": [],
            "descendingSortHand": [],
        }
        self.bet = 0
        self.bet_reconciled = False
        self.folded = False
        self.all_in = False
        self.can_raise = True
        self.stack_investment = 0
        self.robot = not is_human

    def is_broke(self):
        return self.chips <= 0

    def is_not_broke(self):
        return self.chips > 0
    
    def play(self):
        pass

    def __str__(self):
        return f"{self.name} has {self.chips} chips, and has the hand: {', '.join(map(str, self.cards))}"
