import random
from typing import List
from enum import Enum
import json


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
    

class Deck():
    def __init__(self):
        self.cards: list[Card] = self.generate_deck_of_cards()
        self.table_cards_shown: list[Card] = []
        self.shuffle()

    def extend_cards(self, cards: list[Card]):
        self.cards.extend(cards)


    def show_n_table_cards(self, n: int):
        cards = self.get_cards(n)
        self.table_cards_shown.extend(cards.cards)
        return self.table_cards_shown

    def generate_deck_of_cards(self):
        cards: list[Card] = [Card(value, suit) for suit in Suit for value in Value]
        return cards

    def shuffle(self):
        random.shuffle(self.cards)

    def get_cards(self, num_cards: int) -> list[Card]:
        cards: list[Card] = []

        for _ in range(num_cards):
            if self.cards:
                cards.append(self.cards.pop())

        return cards

