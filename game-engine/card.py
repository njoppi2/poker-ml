import random
from typing import List
from enum import Enum

class Suit(Enum):
    HEART = 'Heart'
    SPADE = 'Spade'
    CLUB = 'Club'
    DIAMOND = 'Diamond'

    def __str__(self):
        return self.value


class Value(Enum):
    TWO = '2'
    THREE = '3'
    FOUR = '4'
    FIVE = '5'
    SIX = '6'
    SEVEN = '7'
    EIGHT = '8'
    NINE = '9'
    TEN = '10'
    JACK = 'J'
    QUEEN = 'Q'
    KING = 'K'
    ACE = 'A'

    def __str__(self):
        return self.value


class Card:
    def __init__(self, value: Value, suit: Suit):
        self.value = value
        self.suit = suit

    def __str__(self):
        return f"{self.value} of {self.suit}"
    
    
class Deck:
    def __init__(self):
        self.deck: List[Card] = self.generate_deck_of_cards()
        self.shuffle()

    def __str__(self):
        deck_str = "\n".join(map(str, self.deck))
        return f"\n{deck_str}"

    def generate_deck_of_cards(self):
        deck: List[Card] = []

        for suit in Suit:
            for value in Value:
                card = Card(value, suit)
                deck.append(card)
        return deck

    def shuffle(self):
        random.shuffle(self.deck)

    def get_cards(self, num_cards: int) -> List[Card]:
        cards: List[Card] = []

        for _ in range(num_cards):
            if self.deck:
                cards.append(self.deck.pop())

        return cards
