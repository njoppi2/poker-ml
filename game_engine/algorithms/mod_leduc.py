import random
import collections
import logging
from enum import Enum
import os
from functions import color_print, create_file, float_to_custom_string, Card, Player
import time
import json
import multiprocessing

random.seed(42)

CHIPS, TURN_BET_VALUE, ROUND_BET_VALUE, PLAYED_CURRENT_PHASE = range(4)
num_processes = multiprocessing.cpu_count()
pool = multiprocessing.Pool(processes=num_processes)  # Create a Pool of worker processes
current_file_with_extension = os.path.basename(__file__)
current_file_name = os.path.splitext(current_file_with_extension)[0]

iterations = 1000
use_3bet = True
algorithm = 'mccfr'
cards = [Card.Q, Card.Q, Card.K, Card.K, Card.A, Card.A]
# cards = [1, 1, 2, 2, 3, 3]
exploring_phase = 0.0


if use_3bet:
    # class Actions(Enum):
    #     PASS = 0
    #     BET4 = 1
    #     BET3 = 2
    #     BET2 = 3
    #     BET1 = 4
    # action_symbol = ['p', '4', '3', '2', '1']

    class Actions(Enum):
        PASS = 0
        BET1 = 1
        BET2 = 2
    action_symbol = ['p', 'b', 'B']
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
        2+5 pot: p122p, p14p, p23p, p5p, 122p, 14p, 23p, 5p
        2+6 pot: p1221, p123p, p132, p15p, p231, p24p, p33, p6p, 1221, 123p, 132, 15p, 231, 24p, 33, 6p
        2+7 pot: p1222p, p124p, p133p, p141, p16p, ....
        2+8 pot: ......
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

            self.actions = list(actions)
            self.num_actions = len(actions)
            self.info_set = info_set
            # The regret and strategies of a node refer to the last action taken to reach the node
            self.regret_sum = [0.0] * self.num_actions
            self.strategy = [0.0] * self.num_actions
            self.strategy_sum = [0.0] * self.num_actions

        def get_strategy(self, realization_weight):
            """Turn sum of regrets into a probability distribution for actions."""
            normalizing_sum = sum(max(regret, 0) for regret in self.regret_sum)
            for i in range(len(self.actions)):
                if normalizing_sum > 0:
                    self.strategy[i] = max(self.regret_sum[i], 0) / normalizing_sum
                else:
                    self.strategy[i] = 1.0 / self.num_actions
                self.strategy_sum[i] += realization_weight * self.strategy[i]
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
        
        def color_print(self):
            avg_strategy = self.get_average_strategy()
            formatted_avg_strategy = ""
            last_action_index = 0
            for i in range(self.num_actions):
                for _ in range(self.actions[i].value - last_action_index):
                    formatted_avg_strategy += " "*13
                formatted_avg_strategy += color_print(avg_strategy[i])
                last_action_index += 1
            min_width_info_set = f"{self.info_set:<10}"  # Ensuring minimum 10 characters for self.info_set
            return f"{min_width_info_set}: {formatted_avg_strategy}"
        
        def __lt__(self, other):
            return self.info_set < other.info_set


    def get_possible_actions(self, history, cards, player, opponent, players, phase):
        """Returns the reward if it's a terminal node, or the possible actions if it's not."""
        def filter_actions(bet, my_chips):
            return [action for action in Actions if action.value == 0 or (action.value >= bet and action.value <= my_chips)]
        
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
        chips = 2
        turn_bet_value = 1
        round_bet_value = 1
        played_current_phase = False
        algorithm_function = self.cfr if algorithm == 'cfr' else self.mccfr

        start_time = time.time()
        for i in range(iterations):
            random.shuffle(cards)
            initial_player = (chips, turn_bet_value, round_bet_value, played_current_phase)
            players = (initial_player, initial_player)
            is_exploring_phase = i < exploring_phase * iterations
            sum_of_rewards += algorithm_function(cards, "", p0, p1, players, 'preflop',is_exploring_phase)
            
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
        final_strategy_path = f'../analysis/blueprints/leduc-{json_name}'
        create_file(final_strategy_path)

        node_dict = {}
        for n in sorted(self.node_map.values()):
            node_dict[n.info_set] = n.get_average_strategy()

        with open(final_strategy_path, 'w') as file:
            json.dump(node_dict, file, indent=4, sort_keys=True)


    def get_node(self, info_set, possible_actions=None):
        """Returns a node for the given information set. Creates the node if it doesn't exist."""
        return self.node_map.setdefault(info_set, self.Node(info_set, possible_actions))
    
    def set_bet_value(self, player, players, action):
        new_players = list(players)
        current_player = list(players[player])
        current_player[CHIPS] -= action.value
        current_player[TURN_BET_VALUE] = action.value
        current_player[ROUND_BET_VALUE] += action.value
        current_player[PLAYED_CURRENT_PHASE] = True
        assert current_player[CHIPS] >= 0

        new_players[player] = tuple(current_player)
        return tuple(new_players)

    def play_mccfr(self, cards, history, p0, p1, players, phase, strategy, player, action, action_index, is_exploring_phase, alternative_play=None):
        action_char = action_symbol[action.value]
        next_history = history + action_char
        node_action_utility = 0
        # node_action_utility receives a negative values because we are alternating between players,
        # and in the Leduc Poker game, the reward for a player is the opposite of the other player's reward
        if player == 0:
            node_action_utility = -self.mccfr(cards, next_history, p0 * strategy[action_index], p1, players, phase, is_exploring_phase, alternative_play)
        else:
            node_action_utility = -self.mccfr(cards, next_history, p0, p1 * strategy[action_index], players, phase, is_exploring_phase, alternative_play)

        return node_action_utility

    def play_cfr(self, cards, history, p0, p1, players, phase, strategy, player, action, action_index, is_exploring_phase):
        action_char = action_symbol[action.value]
        next_history = history + action_char
        if player == 0:
            return -self.cfr(cards, next_history, p0 * strategy[action_index], p1, players, phase, is_exploring_phase)
        else:
            return -self.cfr(cards, next_history, p0, p1 * strategy[action_index], players, phase, is_exploring_phase)

    def mccfr(self, cards, history, p0, p1, players, phase, is_exploring_phase, alternative_play=None):
        # On the first iteration, the history is empty, so the first player starts
        plays = len(history)
        player = plays % 2
        opponent = 1 - player
        possible_actions, rewards, next_phase = self.get_possible_actions(history, cards, player, opponent, players, phase)
        updated_phase = 'flop' if next_phase else phase

        if possible_actions is None:
            return rewards

        public_card = cards[2] if phase == 'flop' else ""
        info_set = str(cards[player]) + str(public_card) + history
        node = self.get_node(info_set, possible_actions)

        if is_exploring_phase:
            strategy = [1.0 / len(possible_actions)] * len(possible_actions)
        else:
            strategy = node.get_strategy(p0 if player == 0 else p1) 
        node_actions_utilities = [0.0] * len(possible_actions)

        other_actions = list(possible_actions)  # Get a list of actions in the order of the enum
        chosen_action = node.get_action(strategy)
        other_actions.remove(Actions(chosen_action))  # Remove the first action from the list
        action_index = node.actions.index(chosen_action)

        updated_players = self.set_bet_value(player, players, chosen_action)

        # Play chosen action according to the strategy
        node_chosen_action_utility = self.play_mccfr(cards, history, p0, p1, updated_players, updated_phase, strategy, player, chosen_action, action_index, is_exploring_phase, alternative_play)
        node_actions_utilities[action_index] = node_chosen_action_utility

        # Play for other actions
        if alternative_play is None or alternative_play == player:
            for action in other_actions:
                action_index = node.actions.index(action)
                # passar um parametro para mccfr dizendo que se é jogada alternativa, e de quê jogador, se for do jogador 1, ai não tem for na jogada do jogador 0
                updated_players = self.set_bet_value(player, players, action)
                node_action_utility = self.play_mccfr(cards, history, p0, p1, updated_players, updated_phase, strategy, player, action, action_index, is_exploring_phase, alternative_play=player)
                node_actions_utilities[action_index] = node_action_utility

            # if len(info_set) > 1 and info_set[0] == info_set[1]:
            #     print('j')
            for action in possible_actions:
                action_index = node.actions.index(action)
                regret = node_actions_utilities[action_index] - node_chosen_action_utility
                node.regret_sum[action_index] += (p1 if player == 0 else p0) * regret

        return node_chosen_action_utility
    

    def cfr(self, cards, history, p0, p1, players, phase, is_exploring_phase):
        plays = len(history)
        player = plays % 2
        opponent = 1 - player

        possible_actions, rewards, next_phase = self.get_possible_actions(history, cards, player, opponent, players, phase)
        updated_phase = 'flop' if next_phase else phase

        if possible_actions is None:
            return rewards

        public_card = cards[2] if phase == 'flop' else ""
        info_set = str(cards[player]) + str(public_card) + history
        node = self.get_node(info_set, possible_actions)

        if is_exploring_phase:
            strategy = [1.0 / len(possible_actions)] * len(possible_actions)
        else:
            strategy = node.get_strategy(p0 if player == 0 else p1) 

        node_actions_utilities = [0.0] * len(possible_actions)
        node_util = 0

        for action in possible_actions:
            action_index = node.actions.index(action)
            updated_players = self.set_bet_value(player, players, action)
            node_action_utility = self.play_cfr(cards, history, p0, p1, updated_players, updated_phase, strategy, player, action, action_index, is_exploring_phase)
            node_actions_utilities[action_index] = node_action_utility
            node_util += strategy[action_index] * node_action_utility

        for action in possible_actions:
            action_index = node.actions.index(action)
            regret = node_actions_utilities[action_index] - node_util
            node.regret_sum[action_index] += (p1 if player == 0 else p0) * regret

        return node_util


if __name__ == "__main__":
    trainer = ModLeducTrainer()
    trainer.log(f'../analysis/logs/{current_file_name}_{algorithm}.log')
    trainer.train(iterations)
