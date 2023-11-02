
import os
import logging
import inspect
from enum import Enum
import pickle
import json
import random
import string
from utils import CHIPS, TURN_BET_VALUE, PHASE_BET_VALUE, ROUND_BET_VALUE, PLAYED_CURRENT_PHASE

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

def generate_random_string(length):
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for _ in range(length))


def set_bet_value(player, players, action_value, next_phase_started, is_bet_relative, possible_actions):
    opponent = 1 - player
    new_players = list(players)
    current_player = list(players[player])
    opponent_player = list(players[opponent])
    is_filler_play = False
    if len(possible_actions) == 1:
        assert possible_actions[0]['value'] == 0
        is_filler_play = True

    if is_bet_relative:    
        current_player[CHIPS] -= action_value
        current_player[TURN_BET_VALUE] = action_value
        current_player[ROUND_BET_VALUE] += action_value
    else:
        my_round_bet_total = action_value or current_player[ROUND_BET_VALUE]
        current_player[CHIPS] -= my_round_bet_total - current_player[ROUND_BET_VALUE]
        current_player[TURN_BET_VALUE] = my_round_bet_total - current_player[ROUND_BET_VALUE]
        current_player[ROUND_BET_VALUE] = my_round_bet_total

    current_player[PLAYED_CURRENT_PHASE] = True
    if next_phase_started:
        opponent_player[PLAYED_CURRENT_PHASE] = False
    new_players[player] = tuple(current_player)
    new_players[opponent] = tuple(opponent_player)
    assert current_player[CHIPS] >= 0

    is_fold = action_value == 0 and current_player[ROUND_BET_VALUE] < opponent_player[ROUND_BET_VALUE]
    is_check = action_value == 0
    is_call = action_value > 0 and current_player[ROUND_BET_VALUE] == opponent_player[ROUND_BET_VALUE]
    is_raise = action_value > 0 and current_player[ROUND_BET_VALUE] > opponent_player[ROUND_BET_VALUE]

    result = '-' if is_filler_play else 'f' if is_fold else 'k' if is_check else 'c' if is_call else f'r{action_value*100}' if is_raise else None
    return tuple(new_players), result

def create_json_from_pickle(pickle_file_path):
    with open(pickle_file_path, 'rb') as pickle_file:
        node_dict = pickle.load(pickle_file)

    json_file_path = pickle_file_path.replace('.pkl', '.json')

    with open(json_file_path, 'w') as json_file:
        json.dump(node_dict, json_file, indent=4, sort_keys=True)

def get_phase(phase, player, players):
    my_previous_bets = players[player][ROUND_BET_VALUE]
    opponent = 1 - player
    bet_difference_to_continue = players[opponent][ROUND_BET_VALUE] - my_previous_bets
    if players[player][PLAYED_CURRENT_PHASE] and bet_difference_to_continue == 0:
        if phase == 'preflop':
            return 'flop'
    else:
        return phase


if __name__ == "__main__":
    create_json_from_pickle('../analysis/blueprints/OMC-mccfr-6cards-12maxbet-EPcfr0_0-mRW0_0-iter500.pkl')