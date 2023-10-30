
import os
import logging
import inspect
from enum import Enum
import pickle
import json
import random
import string

CHIPS, TURN_BET_VALUE, ROUND_BET_VALUE, PLAYED_CURRENT_PHASE = range(4)

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

class Card(Enum):
    Q = 1
    K = 2
    A = 3

    def __str__(self):
        return self.name
    
    def __lt__(self, other):
        return self.value < other.value


def get_possible_actions(history, cards, player, opponent, players, phase, all_actions):
    """Returns the reward if it's a terminal node, or the possible actions if it's not."""
    def filter_actions(bet, my_chips):
        return [action for action in all_actions if action['value'] == 0 or (action['value'] >= bet and action['value'] <= my_chips)]
    
    def half(value):
        return value // 2
    min_bet_to_continue = players[opponent][ROUND_BET_VALUE] - players[player][ROUND_BET_VALUE]
    
    def result_multiplier():
        if cards[player] == cards[2]:
            return 1
        elif cards[opponent] == cards[2]:
            return -1
        elif cards[player] > cards[opponent]:
            return 1
        elif cards[player] < cards[opponent]:
            return -1
        else:
            # cards[player] == cards[opponent]
            return 0
        
    if min_bet_to_continue < 0:
        # The opponent folded
        my_bet_total = players[player][ROUND_BET_VALUE]
        opponent_bet_total = players[opponent][ROUND_BET_VALUE]
        total_bet = my_bet_total + opponent_bet_total + min_bet_to_continue
        return None, half(total_bet), False
    
    if not players[player][PLAYED_CURRENT_PHASE] and min_bet_to_continue == 0:
        possible_actions = filter_actions(0, players[player][CHIPS])
        return possible_actions, None, False
    
    if players[player][PLAYED_CURRENT_PHASE] and min_bet_to_continue == 0:
        if phase == 'preflop':
            # if player 0 would end pre-flop, then the second player would start the flop, which is not what we want
            if player == 1:
                possible_actions = filter_actions(0, 0)
                return possible_actions, None, False
            possible_actions = filter_actions(min_bet_to_continue, players[player][CHIPS])
            assert players[player][ROUND_BET_VALUE] == players[opponent][ROUND_BET_VALUE]
            return possible_actions, None, True
        else:
            # Showdown
            my_bet_total = players[player][ROUND_BET_VALUE]
            opponent_bet_total = players[opponent][ROUND_BET_VALUE]
            total_bet = my_bet_total + opponent_bet_total
            assert my_bet_total == opponent_bet_total
            return None, half(total_bet * result_multiplier()), False
        
    if min_bet_to_continue > 0:
        possible_actions = filter_actions(min_bet_to_continue, players[player][CHIPS])
        return possible_actions, None, False
    
    raise Exception("Action or reward not found for history: " + history)


def set_bet_value(player, players, action_value, next_phase_started):
    opponent = 1 - player
    new_players = list(players)
    current_player = list(players[player])
    opponent_player = list(players[opponent])
    
    current_player[CHIPS] -= action_value
    current_player[TURN_BET_VALUE] = action_value
    current_player[ROUND_BET_VALUE] += action_value
    current_player[PLAYED_CURRENT_PHASE] = True
    if next_phase_started:
        opponent_player[PLAYED_CURRENT_PHASE] = False

    new_players[player] = tuple(current_player)
    new_players[opponent] = tuple(opponent_player)
    assert current_player[CHIPS] >= 0
    return tuple(new_players)

def create_json_from_pickle(pickle_file_path):
    with open(pickle_file_path, 'rb') as pickle_file:
        node_dict = pickle.load(pickle_file)

    json_file_path = pickle_file_path.replace('.pkl', '.json')

    with open(json_file_path, 'w') as json_file:
        json.dump(node_dict, json_file, indent=4, sort_keys=True)


if __name__ == "__main__":
    create_json_from_pickle('../analysis/blueprints/leduc-vof-mccfr-6cards-EP0_1-iter100000.pkl')