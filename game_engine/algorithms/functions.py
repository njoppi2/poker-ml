
import os
import logging
import inspect
from enum import Enum


def color_print(value):
    r, g, b = (255, 255, 255)
    if 0 <= value <= 1:
        color_map = [
            (255, 0, 0),     # 0
            (255, 50, 0),    # 0.1
            (255, 100, 0),   # 0.2
            (255, 150, 0),   # 0.3
            (255, 200, 0),   # 0.4
            (150, 255, 0),   # 0.5
            (10, 255, 0),   # 0.6
            (0, 255, 50),   # 0.7
            (0, 255, 150),   # 0.8
            (0, 255, 255),    # 0.9
            (0, 205, 255)      # 1
        ]

        interval = int((value) * (len(color_map) - 1))
        r, g, b = color_map[interval]

    # ANSI escape sequence for color formatting
    return f"\033[38;2;{r};{g};{b}m{value:.10f}\033[0m "


def create_file(log_file):
    log_dir = os.path.dirname(log_file)
    if log_dir != '' and not os.path.exists(log_dir):
        os.makedirs(log_dir)  # If the directory doesn't exist, create it

    if not os.path.exists(log_file):

        open(log_file, 'w').close()  # If it doesn't exist, create the file

def float_to_custom_string(num):
    str_num = str(num).replace('.', '_')  # Replacing decimal point with underscore
    return str_num

class Card(Enum):
    Q = 1
    K = 2
    A = 3

    def __str__(self):
        return self.name
    
    def __lt__(self, other):
        return self.value < other.value

class Player:
    def __init__(self, player_id: int):
        self.id = player_id
        self.chips = 0
        self.turn_bet_value: int = 1
        self.phase_bet_value: int = 1
        self.round_bet_value: int = 1
        self.round_bet_aux: int = 0
        self.played_current_phase = False

    def reset(self, chips: int):
        self.chips = chips
        self.turn_bet_value = 1
        self.phase_bet_value = 1
        self.round_bet_value = 1
        self.round_bet_aux = 0
        self.played_current_phase = False