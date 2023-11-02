import random
from functions import color_print
from enum import Enum
from utils import CHIPS, TURN_BET_VALUE, PHASE_BET_VALUE, ROUND_BET_VALUE, PLAYED_CURRENT_PHASE

class Card(Enum):
    Q = 1
    K = 2
    A = 3

    def __str__(self):
        return self.name
    
    def __lt__(self, other):
        return self.value < other.value


class HistoryNode:
    def __init__(self, name, history, phase_divisor, parent_history_node, player, phase):
        self.name = name

        self.next_histories = {}
        self.info_sets = {}
        self.full_history = history + phase_divisor + name
        self.parent_history_node = parent_history_node
        self.player = player
        self.phase = phase

    def get_descendent_histories(self):
        result = []
        for info_set in self.info_sets.values():
            result.append({info_set.info_set + info_set.full_history:info_set})

        for next_history in self.next_histories.values():
            result += next_history.get_descendent_histories()
        return result


class InfoSetNode:
    """ A node is an information set, which is the cards of the player and the history of the game."""
    def __init__(self, cards, full_history, strategy, parent_history_node, player, players, old_phase, all_actions, bb, total_chips, is_bet_relative):

        possible_actions, get_rewards, phase = self.get_possible_actions(full_history, player, players, old_phase, all_actions, bb, total_chips, is_bet_relative)
        public_card = f'/{cards[2]}' if phase == 'flop' else ""
        self.my_cards = str(cards[player]) + str(public_card)
        self.next_phase_started = old_phase != phase

        self.get_rewards = get_rewards
        self.phase = phase

        self.leaf_node = possible_actions is not None
        self.actions = list(possible_actions) if possible_actions is not None else []
        self.actions_names = {}
        self.num_actions = len(self.actions)
        self.info_set = self.my_cards
        self.full_history = full_history
        # The regret and strategies of a node refer to the last action taken to reach the node
        self.regret_sum = [0.0] * self.num_actions
        self.strategy = [0.0] * self.num_actions if strategy is None else strategy
        self.strategy_sum = [0.0] * self.num_actions
        self.parent_history_node = parent_history_node
        self.player = player
        self.times_regret_sum_updated = 0
        self.times_strategy_sum_updated = 0
        self.times_action_got_positive_reward = [0] * self.num_actions
        self.times_got_strategy_without_0_rw = 0
        self.times_got_strategy_without_0_strat = 0


    def get_strategy(self, realization_weight, is_exploring_phase, is_current_model_fixed, min_reality_weight, decrese_weight_of_initial_strategies):
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
    
    def get_possible_actions(self, history, player, players, phase, all_actions, bb, total_chips, is_bet_relative):
        opponent = 1 - player
        """Returns the reward if it's a terminal node, or the possible actions if it's not."""    
        my_previous_bets = players[player][ROUND_BET_VALUE]
        bet_difference_to_continue = players[opponent][ROUND_BET_VALUE] - my_previous_bets

        def is_action_legal(action, relative_bet, bb, my_chips):
            assert relative_bet >= 0
            value = action['value']
            is_pass_or_all_win = value == 0 or value == total_chips

            if my_chips == 0:
                return value == 0
            
            if is_bet_relative:
                return value == 0 or value == relative_bet or value == my_chips or (value >= max(bb, 2*relative_bet) and value <= my_chips)
            else:
                if relative_bet == 0:
                    # return value == 0 or (value >= bb and value <= my_chips)
                    return is_pass_or_all_win or value >= bb + my_previous_bets
                else:
                    total_bet = my_previous_bets + relative_bet
                    assert total_bet >= bb + my_previous_bets
                    # min_reraise = players[player][ROUND_BET_VALUE] + 2*relative_bet
                    # all_win = players[player][CHIPS] + total_bet
                    # return value == 0 or value == relative_bet or (value >= 2*relative_bet and value <= my_chips)
                    return is_pass_or_all_win or value == total_bet or (value >= my_previous_bets + 2*relative_bet)
        
        def filter_actions(relative_bet, my_chips):
            return [action for action in all_actions if is_action_legal(action, relative_bet, bb, my_chips)]

        def half(value):
            return value // 2
        
        def get_no_rewards(cards, player, players):
                pass
        
        def result_multiplier(cards, player):
            opponent = 1 - player
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
            
        if bet_difference_to_continue < 0:
            # The opponent folded
            def get_rewards(cards, player, players):
                my_bet_total = players[player][ROUND_BET_VALUE]
                opponent_bet_total = players[opponent][ROUND_BET_VALUE]
                total_bet = my_bet_total + opponent_bet_total + bet_difference_to_continue
                return half(total_bet)
            return None, get_rewards, phase
        
        if not players[player][PLAYED_CURRENT_PHASE] and bet_difference_to_continue == 0:
            possible_actions = filter_actions(0, players[player][CHIPS])
            return possible_actions, get_no_rewards, phase
        
        if players[player][PLAYED_CURRENT_PHASE] and bet_difference_to_continue == 0:
            if phase == 'preflop':
                # if player 0 would end pre-flop, then the second player would start the flop, which is not what we want
                if player == 1:
                    possible_actions = filter_actions(0, 0)
                    return possible_actions, None, phase
                possible_actions = filter_actions(bet_difference_to_continue, players[player][CHIPS])
                assert players[player][ROUND_BET_VALUE] == players[opponent][ROUND_BET_VALUE]
                return possible_actions, get_no_rewards, 'flop'
            else:
                # Showdown
                def get_rewards(cards, player, players):
                    my_bet_total = players[player][ROUND_BET_VALUE]
                    opponent_bet_total = players[opponent][ROUND_BET_VALUE]
                    total_bet = my_bet_total + opponent_bet_total
                    assert my_bet_total == opponent_bet_total
                    return half(total_bet * result_multiplier(cards, player))
                return None, get_rewards, phase
            
        if bet_difference_to_continue > 0:
            possible_actions = filter_actions(bet_difference_to_continue, players[player][CHIPS])
            return possible_actions, get_no_rewards, phase
        
        raise Exception("Action or reward not found for history: " + history)


    def __str__(self):
        min_width_info_set = f"{self.info_set:<10}"  # Ensuring minimum 10 characters for self.info_set
        return f"{min_width_info_set}: {self.get_average_strategy()}"
    
    def color_print_node(self, total_actions, use_tree_format):
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

        if use_tree_format:
            final_info_set = self.full_history + ':|' + self.info_set
        else:
            final_info_set = self.info_set

        min_width_info_set = f"{final_info_set:<20}"  # Ensuring minimum 10 characters for self.info_set
        return f"{min_width_info_set}: {formatted_avg_strategy} {self.times_regret_sum_updated}  {self.times_strategy_sum_updated}  {self.times_got_strategy_without_0_rw}  {self.times_got_strategy_without_0_strat}"
    
    def __lt__(self, other):
        return self.info_set < other.info_set
    
