import random
import collections
import logging
from enum import Enum
import os
from functions import color_print, create_file
import time
import json

current_file_with_extension = os.path.basename(__file__)
current_file_name = os.path.splitext(current_file_with_extension)[0]

random.seed(42)
use_3bet = True

if use_3bet:
    class Actions(Enum):
        PASS = 0
        BET2 = 1
        BET1 = 2
    action_symbol = ['p', 'B', 'b']
else:
    class Actions(Enum):
        PASS = 0
        BET1 = 1
    action_symbol = ['p','b']

class KuhnTrainer:

    def __init__(self):
        self.node_map = {}
        self.log_file = None

    def log(self, log_file):
        log_dir = os.path.dirname(log_file)
        if log_dir != '' and not os.path.exists(log_dir):
            os.makedirs(log_dir)  # If the directory doesn't exist, create it

        if not os.path.exists(log_file):
            open(log_file, 'w').close()  # If it doesn't exist, create the file

        self.log_file = log_file
        log_format = 'Iteration: %(index)s\nAverage game value: %(avg_game_value)s\n%(result_dict)s\n'
        formatter = logging.Formatter(log_format)

        with open(log_file, 'w') as file:
            file_handler = logging.FileHandler(log_file, mode='w')
            file_handler.setFormatter(formatter)

            self.logger = logging.getLogger('')
            self.logger.setLevel(logging.DEBUG)
            self.logger.addHandler(file_handler)
    
    class Node:
        def __init__(self, info_set, actions=Actions):

            self.actions = actions
            self.num_actions = len(actions)
            self.info_set = info_set
            # The regret and strategies of a node refer to the last action taken to reach the node
            self.regret_sum = [0.0] * self.num_actions
            self.strategy = [0.0] * self.num_actions
            self.strategy_sum = [0.0] * self.num_actions

        def get_strategy(self, realization_weight):
            """Turn sum of regrets into a probability distribution for actions."""
            normalizing_sum = sum(max(regret, 0) for regret in self.regret_sum)
            for action in self.actions:
                if normalizing_sum > 0:
                    self.strategy[action.value] = max(self.regret_sum[action.value], 0) / normalizing_sum
                else:
                    self.strategy[action.value] = 1.0 / self.num_actions
                self.strategy_sum[action.value] += realization_weight * self.strategy[action.value]
            return self.strategy

        def get_average_strategy(self):
            avg_strategy = [0.0] * self.num_actions
            normalizing_sum = sum(self.strategy_sum)
            for action in self.actions:
                if normalizing_sum > 0:
                    avg_strategy[action.value] = self.strategy_sum[action.value] / normalizing_sum
                else:
                    avg_strategy[action.value] = 1.0 / self.num_actions
            return avg_strategy

        def __str__(self):
            min_width_info_set = f"{self.info_set:<10}"  # Ensuring minimum 10 characters for self.info_set
            return f"{min_width_info_set}: {self.get_average_strategy()}"
        
        def color_print(self):
            avg_strategy = self.get_average_strategy()
            formatted_avg_strategy = ""
            for action_strategy in avg_strategy:
                formatted_avg_strategy += color_print(action_strategy)
            min_width_info_set = f"{self.info_set:<10}"  # Ensuring minimum 10 characters for self.info_set
            return f"{min_width_info_set}: {formatted_avg_strategy}"
        
        def __lt__(self, other):
            return self.info_set < other.info_set

    def get_possible_actions(self, history, cards, player, opponent):
        """Returns the reward if it's a terminal node, or the possible actions if it's not."""
        is_player_card_higher = cards[player] > cards[opponent]
        
        if len(history) == 0:
            return Actions, None
        elif len(history) >= 2:
            if history[-2:] == "pp":
                return None, 1 if is_player_card_higher else -1
            elif history[-2:] == "bp" or history[-2:] == "Bp":
                return None, 1
            elif history[-2:] == "bb":
                return None, 2 if is_player_card_higher else -2
            elif history[-2:] == "BB" :
                return None, 3 if is_player_card_higher else -3
            elif history[-3:] == "bBb":
                return None, 3 if is_player_card_higher else -3
            
        if history[-1] == 'B':
            possible_actions = list(Actions)
            possible_actions.remove(Actions(Actions.BET1))  # Remove the first action from the list
            return possible_actions, None
        else:
            return Actions, None

        return Actions, None
        # raise Exception("Action or reward not found for history: " + history)

    def print_average_strategy(self, sum_of_rewards, iterations):
        print(f"Average game value: {sum_of_rewards / iterations}")
        columns = ""
        for action in Actions:
            columns += f"{action} "
        print(f"Columns   : {columns}")
        for n in sorted(self.node_map.values()):
            print(n.color_print())

    def train(self, iterations):
        cards = [1, 2, 3]#, 4, 5, 6, 7, 8, 9]
        util = 0

        start_time = time.time()
        for i in range(iterations):
            random.shuffle(cards)
            util += self.cfr(cards, "", 1, 1)
            
            dict_str = ""
            for n in self.node_map.values():
                dict_str += str(n) + "\n"
            sample_iteration = {
                'index': i,
                'avg_game_value': util / (i + 1),
                'result_dict': dict_str  # Assuming self.node_map contains the result dictionary
            }

            if i < 10:
                self.logger.info('', extra=sample_iteration)

            # if i % 1000 == 0:
            #    self.print_average_strategy(util, iterations)

        self.print_average_strategy(util, iterations)
        end_time = time.time()
        print(f"Average game value: {util / iterations}")
        for n in sorted(self.node_map.values()):
            print(n.color_print())

        elapsed_time = end_time - start_time
        print(f"cfr took {elapsed_time} seconds to run.")

        final_strategy_path = f'../analysis/blueprints/{current_file_name}_{"with3bet" if use_3bet else "2bet"}.json'
        create_file(final_strategy_path)

        node_dict = {}
        for n in sorted(self.node_map.values()):
            node_dict[n.info_set] = n.get_average_strategy()

        with open(final_strategy_path, 'w') as file:
            json.dump(node_dict, file, indent=4, sort_keys=True)


    def get_node(self, info_set, possible_actions=Actions):
        """Returns a node for the given information set. Creates the node if it doesn't exist."""
        return self.node_map.setdefault(info_set, self.Node(info_set, possible_actions))


    def cfr(self, cards, history, p0, p1):
        plays = len(history)
        player = plays % 2
        opponent = 1 - player

        possible_actions, rewards = self.get_possible_actions(history, cards, player, opponent)

        if possible_actions is None:
            return rewards

        info_set = str(cards[player]) + history
        node = self.get_node(info_set, possible_actions)

        strategy = node.get_strategy(p0 if player == 0 else p1)
        node_actions_utilities = [0.0] * len(possible_actions)
        node_util = 0

        for action in possible_actions:
            action_char = action_symbol[action.value]
            next_history = history + action_char
            if player == 0:
                node_actions_utilities[action.value] = -self.cfr(cards, next_history, p0 * strategy[action.value], p1) #aqui implementa a recursao, percorrendo os nodos e calculando a utilidade esperada
            else:
                node_actions_utilities[action.value] = -self.cfr(cards, next_history, p0, p1 * strategy[action.value])
            node_util += strategy[action.value] * node_actions_utilities[action.value]

        for action in possible_actions:
            regret = node_actions_utilities[action.value] - node_util
            node.regret_sum[action.value] += (p1 if player == 0 else p0) * regret

        return node_util

if __name__ == "__main__":
    iterations = 100000
    trainer = KuhnTrainer()
    trainer.log(f'../analysis/logs/{current_file_name}.log')
    trainer.train(iterations)
