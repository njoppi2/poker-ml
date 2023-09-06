import random
from typing import List
from enum import Enum

class Suit(Enum):
    HEARTS = 'Hearts'
    SPADES = 'Spades'
    CLUBS = 'Clubs'
    DIAMONDS = 'Diamonds'

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
    
class Cards:
    def __init__(self):
        self.cards: List[Card] = []
    
    def extend_cards(self, cards: List[Card]):
        self.cards.extend(cards)
    
    def __str__(self):
        table_cards_str = "; ".join(map(str, self.cards))
        return f"{table_cards_str}"
    
    
class Deck(Cards):
    def __init__(self):
        self.deck: Cards = self.generate_deck_of_cards()
        self.table_cards_shown: Cards = []
        self.shuffle()

    def show_n_table_cards(self, n: int):
        cards = self.get_cards(n)
        self.table_cards_shown.extend(cards)
        return self.table_cards_shown

    def generate_deck_of_cards(self):
        deck: Cards = []

        for suit in Suit:
            for value in Value:
                card = Card(value, suit)
                deck.append(card)
        return deck

    def shuffle(self):
        random.shuffle(self.deck)

    def get_cards(self, num_cards: int) -> Cards:
        cards: Cards = []

        for _ in range(num_cards):
            if self.deck:
                cards.append(self.deck.pop())

        return cards

