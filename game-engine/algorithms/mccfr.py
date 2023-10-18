import random
import collections
import logging
from enum import Enum
import os
random.seed(42)
class Actions(Enum):
    PASS = 0
    BET = 1

NUM_ACTIONS = len(Actions)

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
        """ A node is an information set, which is the cards of the player and the history of the game."""
        def __init__(self, info_set):
            self.info_set = info_set
            # The regret and strategies of a node refer to the last action taken to reach the node
            self.regret_sum = [0.0] * NUM_ACTIONS
            self.strategy = [0.0] * NUM_ACTIONS
            self.strategy_sum = [0.0] * NUM_ACTIONS

        def get_strategy(self, realization_weight):
            """Turn sum of regrets into a probability distribution for actions."""
            normalizing_sum = sum(max(regret, 0) for regret in self.regret_sum)
            for action in Actions:
                if normalizing_sum > 0:
                    self.strategy[action.value] = max(self.regret_sum[action.value], 0) / normalizing_sum
                else:
                    self.strategy[action.value] = 1.0 / NUM_ACTIONS
                self.strategy_sum[action.value] += realization_weight * self.strategy[action.value]
            return self.strategy

        def get_action(self, strategy):
            """Returns an action based on the strategy."""
            r = random.random()
            cumulative_probability = 0
            
            for action in Actions:
                cumulative_probability += strategy[action.value]
                if r < cumulative_probability:
                    return action
            
            raise Exception("No action taken for r: " + str(r) + " and cumulativeProbability: " + str(cumulative_probability) + " and strategy: " + str(strategy))

        def get_average_strategy(self):
            avg_strategy = [0.0] * NUM_ACTIONS
            normalizing_sum = sum(self.strategy_sum)
            for action in Actions:
                if normalizing_sum > 0:
                    avg_strategy[action.value] = self.strategy_sum[action.value] / normalizing_sum
                else:
                    avg_strategy[action.value] = 1.0 / NUM_ACTIONS
            return avg_strategy

        def __str__(self):
            return f"{self.info_set}: {self.get_average_strategy()}"
        
        def __lt__(self, other):
            return self.info_set < other.info_set


    def train(self, iterations):
        cards = [1, 2, 3]#, 4, 5, 6, 7, 8, 9]
        sum_of_rewards = 0
        for i in range(iterations):
            random.shuffle(cards)
            sum_of_rewards += self.mccfr(cards, "", 1, 1)
            
            dict = ""
            for n in self.node_map.values():
                dict += str(n) + "\n"
            sample_iteration = {
                'index': i,
                'avg_game_value': sum_of_rewards / (i + 1),
                'result_dict': dict  # Assuming self.nodeMap contains the result dictionary
            }
            self.logger.info('', extra=sample_iteration)
            
        print(f"Average game value: {sum_of_rewards / iterations}")
        for n in sorted(self.node_map.values()):
            print(n)

    def get_node(self, info_set):
        """Returns a node for the given information set. Creates the node if it doesn't exist."""
        return self.node_map.setdefault(info_set, self.Node(info_set))


    def play(self, cards, history, p0, p1, action, node_actions_rewards, player, strategy):
        next_history = history + ('p' if action == Actions.PASS else 'b')
        if player == 0:
            node_actions_rewards[action.value] = -self.mccfr(cards, next_history, p0 * strategy[action.value], p1)
        else:
            node_actions_rewards[action.value] = -self.mccfr(cards, next_history, p0, p1 * strategy[action.value])
        node_reward = 0
        node_reward += strategy[action.value] * node_actions_rewards[action.value]
        return node_reward


    def mccfr(self, cards, history, p0, p1):
        plays = len(history)
        player = plays % 2
        opponent = 1 - player

        if plays > 1:
            terminal_pass = history[-1] == 'p'
            double_bet = history[-2:] == 'bb'
            is_player_card_higher = cards[player] > cards[opponent]

            if terminal_pass:
                if history == "pp":
                    return 1 if is_player_card_higher else -1          #determina a recompensa
                else:
                    return 1
            elif double_bet:
                return 2 if is_player_card_higher else -2              #determina a recompensa

        info_set = str(cards[player]) + history                      #determina o infoset olhando a carta do jogador atual e o histórico
        node = self.get_node(info_set)

        strategy = node.get_strategy(p0 if player == 0 else p1)      #pega a estratégia do nodo, que é um vetor de probabilidades para cada ação.
        node_actions_rewards = [0.0] * NUM_ACTIONS
        node_reward_sum = 0

        other_actions = list(Actions)  # Get a list of actions in the order of the enum
        chosen_action = node.get_action(strategy)
        other_actions.remove(Actions(chosen_action))  # Remove the first action from the list

        self.play(cards, history, p0, p1, chosen_action, node_actions_rewards, player, strategy)

        for action in other_actions:
            self.play(cards, history, p0, p1, action, node_actions_rewards, player, strategy)

        for action in Actions:
            regret = node_actions_rewards[action.value] - node_reward_sum
            node.regret_sum[action.value] += (p1 if player == 0 else p0) * regret

        return node_reward_sum

if __name__ == "__main__":
    iterations = 10000
    trainer = KuhnTrainer()
    trainer.log('../analysis/logs/mccfr.log')
    trainer.train(iterations)
