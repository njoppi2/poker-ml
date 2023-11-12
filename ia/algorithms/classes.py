import random
from functions import color_print
from enum import Enum

class Card(Enum):
    Q = 1
    K = 2
    A = 3

    def __str__(self):
        return self.name
    
    def __lt__(self, other):
        return self.value < other.value


class HistoryNode:
    def __init__(self, name, history):
        self.name = name

        self.next_histories = {}
        self.info_sets = {}
        self.full_history = history + name


class InfoSetNode:
    """ A node is an information set, which is the cards of the player and the history of the game."""
    def __init__(self, cards, full_history, actions, strategy):

        self.actions = list(actions)
        self.actions_names = {}
        self.num_actions = len(actions)
        self.info_set = cards
        self.full_history = full_history
        # The regret and strategies of a node refer to the last action taken to reach the node
        self.regret_sum = [0.0] * self.num_actions
        self.strategy = [0.0] * self.num_actions if strategy is None else strategy
        self.strategy_sum = [0.0] * self.num_actions
        self.times_regret_sum_updated = 0
        self.times_strategy_sum_updated = 0
        self.times_action_got_positive_reward = [0] * self.num_actions
        self.times_got_strategy_without_0_rw = 0
        self.times_got_strategy_without_0_strat = 0

    def get_strategy(self, realization_weight, is_exploring_phase, is_current_model_fixed, min_reality_weight, decrese_weight_of_initial_strategies, info_set):
        """Turn sum of regrets into a probability distribution for actions."""
        linear_strategy = False
        if not is_current_model_fixed:
            # r = random.random()
            # test_bad_actions = r < 0.05
            normalizing_sum = sum(max(regret, 0) for regret in self.regret_sum)
            for i in range(len(self.actions)):
                if normalizing_sum > 0:
                    self.strategy[i] = max(self.regret_sum[i], 0) / normalizing_sum
                else:
                    self.strategy[i] = 1.0 / self.num_actions
                    linear_strategy = decrese_weight_of_initial_strategies
                if realization_weight != 0:
                    self.times_got_strategy_without_0_rw += 1
                if self.strategy[i] != 0:
                    self.times_got_strategy_without_0_strat += 1
                
                strategy_factor = min_reality_weight if linear_strategy else self.strategy[i]
                strategy_sum_increment = max(realization_weight, min_reality_weight) * strategy_factor
                self.strategy_sum[i] += strategy_sum_increment 
                self.times_strategy_sum_updated += bool(strategy_sum_increment)
        return self.strategy
    
    def get_action(self, strategy):
        """Returns an action based on the strategy."""
        r = random.random()
        cumulative_probability = 0
        
        for i in range(len(self.actions)):
            cumulative_probability += strategy[i]
            if r < cumulative_probability:
                return self.actions[i]
        
        raise Exception("No action taken for r: " + str(r) + " and cumulativeProbability: " + str(cumulative_probability) + " and strategy: " + str(strategy))

    def get_average_strategy(self):
        avg_strategy = [0.0] * self.num_actions
        normalizing_sum = sum(self.strategy_sum)
        for i in range(len(self.actions)):
            if normalizing_sum > 0:
                avg_strategy[i] = self.strategy_sum[i] / normalizing_sum
            else:
                avg_strategy[i] = 1.0 / self.num_actions
        return avg_strategy

    def __str__(self):
        min_width_info_set = f"{self.info_set:<10}"  # Ensuring minimum 10 characters for self.info_set
        return f"{min_width_info_set}: {self.get_average_strategy()}"
    
    def color_print_node(self, total_actions):
        avg_strategy = self.get_average_strategy()
        formatted_avg_strategy = ""
        last_action_index = 0
        filled_columns = 0
        column_length = " "*13
        action_existence = [item in self.actions for item in total_actions]
        for i in range(len(action_existence)):
            action_exists = action_existence[i]
            if action_exists:
                formatted_avg_strategy += color_print(avg_strategy[last_action_index])
                last_action_index += 1
            else:
                formatted_avg_strategy += column_length

        min_width_info_set = f"{self.info_set:<20}"  # Ensuring minimum 10 characters for self.info_set
        return f"{min_width_info_set}: {formatted_avg_strategy} {self.times_regret_sum_updated}  {self.times_strategy_sum_updated}  {self.times_got_strategy_without_0_rw}  {self.times_got_strategy_without_0_strat}"
    
    def __lt__(self, other):
        return self.info_set < other.info_set
    
