import random
import collections
import logging
from enum import Enum
import os
from functions import color_print, create_file, float_to_custom_string
import time
import json
import multiprocessing



random.seed(42)

num_processes = multiprocessing.cpu_count()
pool = multiprocessing.Pool(processes=num_processes)  # Create a Pool of worker processes
current_file_with_extension = os.path.basename(__file__)
current_file_name = os.path.splitext(current_file_with_extension)[0]

iterations = 1000
use_3bet = True
algorithm = 'cfr'
cards = [1, 1, 2, 2, 3, 3]
exploring_phase = 0.0


if use_3bet:
    class Actions(Enum):
        PASS = 0
        BET4 = 1
        BET3 = 2
        BET2 = 3
        BET1 = 4
    action_symbol = ['p', '4', '3', '2', '1']
else:
    class Actions(Enum):
        PASS = 0
        BET1 = 1
    action_symbol = ['p','b']

class ModLeducTrainer:
    """
       The AI's wil play a version of Leduc Poker with 5 possible actions: pass, bet 1, bet 2, bet 3, and bet 4. 
       Each player has 4 coins, if someone does BET4, they're all-in.
       There are 2 rounds, and at the beggining of the second round, a public card is revealed.
       Possible final histories for the round 1: 
        2+0 pot: pp
        2+1 pot: p1p, 1p
        2+2 pot: p11, p2p, 2p
        2+3 pot: p12p, p3p, 12p, 3p
        2+4 pot: p121, p13p, p22, p4p, 121, 13p, 22, 4p
        # 2+5 pot: p122p, p14p, p131, p23p, p5p, 122p, 14p, 131, 23p, 5p
    """
    # How can we handle situations where not all actions are alowed?

    def __init__(self):
        self.node_map = {}
        self.log_file = None

    def log(self, log_file):
        create_file(log_file)
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
        """ A node is an information set, which is the cards of the player and the history of the game."""
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
        
        def get_action(self, strategy):
            """Returns an action based on the strategy."""
            r = random.random()
            cumulative_probability = 0
            
            for action in self.actions:
                cumulative_probability += strategy[action.value]
                if r < cumulative_probability:
                    return action
            
            raise Exception("No action taken for r: " + str(r) + " and cumulativeProbability: " + str(cumulative_probability) + " and strategy: " + str(strategy))

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
        print(f"Parameters: {iterations} iterations, {len(cards)} cards, {algorithm}, {exploring_phase} exploring phase, {use_3bet} 3bet\n")

        sum_of_rewards = 0

        # p0 and p1 store, respectively, the probability of the player 0 and player 1 reaching the current node,
        # from its "parent" node
        p0 = 1
        p1 = 1

        algorithm_function = self.cfr if algorithm == 'cfr' else self.mccfr

        start_time = time.time()
        for i in range(iterations):
            random.shuffle(cards)
            is_exploring_phase = i < exploring_phase * iterations
            sum_of_rewards += algorithm_function(cards, "", p0, p1, is_exploring_phase)
            
            dict_str = ""
            for n in self.node_map.values():
                dict_str += str(n) + "\n"
            sample_iteration = {
                'index': i,
                'avg_game_value': sum_of_rewards / (i + 1),
                'result_dict': dict_str  # Assuming self.node_map contains the result dictionary
            }

            if i < 10:
                self.logger.info('', extra=sample_iteration)

            # if i % 1000 == 0:
            #    self.print_average_strategy(sum_of_rewards, iterations)

        self.print_average_strategy(sum_of_rewards, iterations)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"{algorithm} took {elapsed_time} seconds to run.")
        json_name = f'{"3bet" if use_3bet else "2bet"}-{algorithm}-{len(cards)}cards-EP{float_to_custom_string(exploring_phase)}.json'
        final_strategy_path = f'../analysis/blueprints/kuhn-{json_name}'
        create_file(final_strategy_path)

        node_dict = {}
        for n in sorted(self.node_map.values()):
            node_dict[n.info_set] = n.get_average_strategy()

        with open(final_strategy_path, 'w') as file:
            json.dump(node_dict, file, indent=4, sort_keys=True)


    def get_node(self, info_set, possible_actions=None):
        """Returns a node for the given information set. Creates the node if it doesn't exist."""
        return self.node_map.setdefault(info_set, self.Node(info_set, possible_actions))


    def play_mccfr(self, cards, history, p0, p1, strategy, player, action, is_exploring_phase, alternative_play=None):
        action_char = action_symbol[action.value]
        next_history = history + action_char
        node_action_utility = 0
        # node_action_utility receives a negative values because we are alternating between players,
        # and in the Leduc Poker game, the reward for a player is the opposite of the other player's reward
        if player == 0:
            node_action_utility = -self.mccfr(cards, next_history, p0 * strategy[action.value], p1, is_exploring_phase, alternative_play)
        else:
            node_action_utility = -self.mccfr(cards, next_history, p0, p1 * strategy[action.value], is_exploring_phase, alternative_play)

        return node_action_utility

    def play_cfr(self, cards, history, p0, p1, strategy, player, action, is_exploring_phase):
        action_char = action_symbol[action.value]
        next_history = history + action_char
        if player == 0:
            return -self.cfr(cards, next_history, p0 * strategy[action.value], p1, is_exploring_phase)
        else:
            return -self.cfr(cards, next_history, p0, p1 * strategy[action.value], is_exploring_phase)

    def mccfr(self, cards, history, p0, p1, is_exploring_phase, alternative_play=None):
        # On the first iteration, the history is empty, so the first player starts
        plays = len(history)
        player = plays % 2
        opponent = 1 - player

        possible_actions, rewards = self.get_possible_actions(history, cards, player, opponent)

        if possible_actions is None:
            return rewards

        info_set = str(cards[player]) + history
        node = self.get_node(info_set, possible_actions)

        if is_exploring_phase:
            strategy = [1.0 / len(possible_actions)] * len(possible_actions)
        else:
            strategy = node.get_strategy(p0 if player == 0 else p1) 
        node_actions_utilities = [0.0] * len(possible_actions)

        other_actions = list(possible_actions)  # Get a list of actions in the order of the enum
        chosen_action = node.get_action(strategy)
        other_actions.remove(Actions(chosen_action))  # Remove the first action from the list

        # Play chosen action according to the strategy
        node_chosen_action_utility = self.play_mccfr(cards, history, p0, p1, strategy, player, chosen_action, is_exploring_phase, alternative_play)
        node_actions_utilities[chosen_action.value] = node_chosen_action_utility

        # Play for other actions
        if alternative_play is None or alternative_play == player:
            for action in other_actions:
                # passar um parametro para mccfr dizendo que se é jogada alternativa, e de quê jogador, se for do jogador 1, ai não tem for na jogada do jogador 0
                node_action_utility = self.play_mccfr(cards, history, p0, p1, strategy, player, action, is_exploring_phase, alternative_play=player)
                node_actions_utilities[action.value] = node_action_utility

        for action in possible_actions:
            regret = node_actions_utilities[action.value] - node_chosen_action_utility
            node.regret_sum[action.value] += (p1 if player == 0 else p0) * regret

        return node_chosen_action_utility
    

    def cfr(self, cards, history, p0, p1, is_exploring_phase):
        plays = len(history)
        player = plays % 2
        opponent = 1 - player

        possible_actions, rewards = self.get_possible_actions(history, cards, player, opponent)

        if possible_actions is None:
            return rewards

        info_set = str(cards[player]) + history
        node = self.get_node(info_set, possible_actions)

        if is_exploring_phase:
            strategy = [1.0 / len(possible_actions)] * len(possible_actions)
        else:
            strategy = node.get_strategy(p0 if player == 0 else p1) 

        node_actions_utilities = [0.0] * len(possible_actions)
        node_util = 0

        for action in possible_actions:
            node_action_utility = self.play_cfr(cards, history, p0, p1, strategy, player, action, is_exploring_phase)
            node_actions_utilities[action.value] = node_action_utility
            node_util += strategy[action.value] * node_action_utility

        for action in possible_actions:
            regret = node_actions_utilities[action.value] - node_util
            node.regret_sum[action.value] += (p1 if player == 0 else p0) * regret

        return node_util


if __name__ == "__main__":
    trainer = ModLeducTrainer()
    trainer.log(f'../analysis/logs/{current_file_name}_{algorithm}.log')
    trainer.train(iterations)
