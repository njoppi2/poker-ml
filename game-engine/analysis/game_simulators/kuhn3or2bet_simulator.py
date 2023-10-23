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
        self.node_map_pA = {}
        self.node_map_pB = {}
        self.log_file = None
        self.file_nameA = 'kuhn3bet_mccfr'
        self.file_nameB = 'kuhn3bet_cfr'
        self.create_nodes_from_json()

    def create_nodes_from_json(self):
        current_directory = os.path.dirname(os.path.abspath(__file__))
        blueprints_directory_pA = os.path.join(current_directory, f'../blueprints/{self.file_nameA}_{"with3bet" if use_3bet else "2bet"}.json')
        blueprints_directory_pB = os.path.join(current_directory, f'../blueprints/{self.file_nameB}_{"with3bet" if use_3bet else "2bet"}.json')

        with open(blueprints_directory_pA, 'r') as f:
            dict_map_pA = json.load(f)

        with open(blueprints_directory_pB, 'r') as f:
            dict_map_pB = json.load(f)

        for key, value in dict_map_pA.items():
            self.node_map_pA[key] = self.Node(key, value)

        for key, value in dict_map_pB.items():
            self.node_map_pB[key] = self.Node(key, value)

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
        def __init__(self, info_set, node_blueprint):

            self.num_actions = len(node_blueprint)
            if self.num_actions > 0:  # Ensure that there are elements to remove
                self.actions = list(Actions)[:self.num_actions]
            else:
                raise Exception("Invalid number of actions for node: " + info_set)

            if self.num_actions != len(self.actions):
                raise Exception("Invalid number of actions for node: " + info_set)
            self.info_set = info_set
            # The regret and strategies of a node refer to the last action taken to reach the node
            self.regret_sum = [0.0] * self.num_actions
            self.strategy = node_blueprint
            self.strategy_sum = [0.0] * self.num_actions

        def get_strategy(self, player):
            """Turn sum of regrets into a probability distribution for actions."""
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
        

    def train(self, iterations):
        cards = [1, 2, 3]#, 4, 5, 6, 7, 8, 9]
        sum_of_rewards = 0

        # p0 and p1 store, respectively, the probability of the player 0 and player 1 reaching the current node,
        # from its "parent" node
        p0 = 1
        p1 = 1

        avg_game_value = {
            'A': 0,
            'B': 0
        }

        for p in ["A", "B"]:
            sum_of_rewards = 0
            player_name = self.file_nameA if p == 'A' else self.file_nameB
            print("Player " + player_name + " is starting.")
            for i in range(iterations):
                random.shuffle(cards)
                sum_of_rewards += self.simulate_play(cards, "", p)

                # if i % 1000 == 0:
                #    self.print_average_strategy(sum_of_rewards, iterations)

            avg_game_value[p] = sum_of_rewards / iterations
            print(f"Average game value for p0: {avg_game_value[p]}")
            
        final_avg_game_value = {
            'A': avg_game_value['A'] - avg_game_value['B'],
            'B': avg_game_value['B'] - avg_game_value['A']
        }

        print(f"\nFinal average game value for {self.file_nameA}: {final_avg_game_value['A']}")
        print(f"Final average game value for {self.file_nameB}: {final_avg_game_value['B']}")

    def get_node(self, info_set, possible_actions=None, player=None, starting_player=None):
        """Returns a node for the given information set. Creates the node if it doesn't exist."""

        first_player_node = self.node_map_pA if starting_player == 'A' else self.node_map_pB
        second_player_node = self.node_map_pB if starting_player == 'A' else self.node_map_pA
        
        if player == 0:
            return first_player_node[info_set]
        else:
            return second_player_node[info_set]


    def play(self, cards, history, action, starting_player=None):
        action_char = action_symbol[action.value]
        next_history = history + action_char
        node_action_utility = 0
        # node_action_utility receives a negative values because we are alternating between players,
        # and in the Kuhn Poker game, the reward for a player is the opposite of the other player's reward
        node_action_utility = -self.simulate_play(cards, next_history, starting_player)

        return node_action_utility


    def simulate_play(self, cards, history, starting_player=None):
        # On the first iteration, the history is empty, so the first player starts
        plays = len(history)
        player = plays % 2
        opponent = 1 - player

        possible_actions, rewards = self.get_possible_actions(history, cards, player, opponent)

        if possible_actions is None:
            return rewards

        info_set = str(cards[player]) + history
        node = self.get_node(info_set, possible_actions, player, starting_player)

        strategy = node.get_strategy(player)

        other_actions = list(possible_actions)  # Get a list of actions in the order of the enum
        chosen_action = node.get_action(strategy)
        other_actions.remove(Actions(chosen_action))  # Remove the first action from the list

        # Play chosen action according to the strategy
        node_chosen_action_utility = self.play(cards, history, chosen_action, starting_player)

        return node_chosen_action_utility

if __name__ == "__main__":
    iterations = 10000
    trainer = KuhnTrainer()
    trainer.log(f'../analysis/logs/{current_file_name}.log')
    trainer.train(iterations)
