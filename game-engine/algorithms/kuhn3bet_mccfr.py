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
    """
       The AI's wil play a version of Kuhn Poker with 3 possible actions: pass, bet 1 and bet 2. 
       Each player has 2 coins, if someone does BET2, they're all-in.
       Possible final histories: 
        pp, pbp, pbb, pbBp, pbBb, pBp, pBb, pBB,
        bp,       bb,  bBp,  bBb,
        Bp,                                 BB 
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
        cards = [1, 2, 3]#, 4, 5, 6, 7, 8, 9]
        sum_of_rewards = 0

        # p0 and p1 store, respectively, the probability of the player 0 and player 1 reaching the current node,
        # from its "parent" node
        p0 = 1
        p1 = 1

        start_time = time.time()
        for i in range(iterations):
            random.shuffle(cards)
            sum_of_rewards += self.mccfr(cards, "", p0, p1)
            
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
        print(f"mccfr took {elapsed_time} seconds to run.")

        final_strategy_path = f'../analysis/blueprints/{current_file_name}_{"with3bet" if use_3bet else "2bet"}.json'
        create_file(final_strategy_path)

        node_dict = {}
        for n in sorted(self.node_map.values()):
            node_dict[n.info_set] = n.get_average_strategy()

        with open(final_strategy_path, 'w') as file:
            json.dump(node_dict, file, indent=4, sort_keys=True)



    def get_node(self, info_set, possible_actions=None):
        """Returns a node for the given information set. Creates the node if it doesn't exist."""
        return self.node_map.setdefault(info_set, self.Node(info_set, possible_actions))


    def play(self, cards, history, p0, p1, strategy, player, action, alternative_play=None):
        action_char = action_symbol[action.value]
        next_history = history + action_char
        node_action_utility = 0
        # node_action_utility receives a negative values because we are alternating between players,
        # and in the Kuhn Poker game, the reward for a player is the opposite of the other player's reward
        if player == 0:
            node_action_utility = -self.mccfr(cards, next_history, p0 * strategy[action.value], p1, alternative_play)
        else:
            node_action_utility = -self.mccfr(cards, next_history, p0, p1 * strategy[action.value], alternative_play)

        return node_action_utility


    def mccfr(self, cards, history, p0, p1, alternative_play=None):
        # On the first iteration, the history is empty, so the first player starts
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

        other_actions = list(possible_actions)  # Get a list of actions in the order of the enum
        chosen_action = node.get_action(strategy)
        other_actions.remove(Actions(chosen_action))  # Remove the first action from the list

        # Play chosen action according to the strategy
        node_chosen_action_utility = self.play(cards, history, p0, p1, strategy, player, chosen_action, alternative_play)
        node_actions_utilities[chosen_action.value] = node_chosen_action_utility

        # Play for other actions
        if alternative_play is None or alternative_play == player:
            for action in other_actions:
                # passar um parametro para mccfr dizendo que se é jogada alternativa, e de quê jogador, se for do jogador 1, ai não tem for na jogada do jogador 0
                node_action_utility = self.play(cards, history, p0, p1, strategy, player, action, alternative_play=player)
                node_actions_utilities[action.value] = node_action_utility

        for action in possible_actions:
            regret = node_actions_utilities[action.value] - node_chosen_action_utility
            node.regret_sum[action.value] += (p1 if player == 0 else p0) * regret

        return node_chosen_action_utility

if __name__ == "__main__":
    iterations = 100000
    trainer = KuhnTrainer()
    trainer.log(f'../analysis/logs/{current_file_name}.log')
    trainer.train(iterations)
