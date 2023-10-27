import random
import collections
import logging
from enum import Enum
import os
from functions import color_print, create_file, float_to_custom_string, Card, get_possible_actions, set_bet_value, generate_random_string
import time
import pickle
import multiprocessing
import re
from types import MappingProxyType

random.seed(42)

# num_processes = multiprocessing.cpu_count()
# pool = multiprocessing.Pool(processes=num_processes)  # Create a Pool of worker processes
current_file_with_extension = os.path.basename(__file__)
current_file_name = os.path.splitext(current_file_with_extension)[0]

iterations = 1000
use_3bet = True
algorithm = 'mccfr'
cards = [Card.Q, Card.Q, Card.K, Card.K, Card.A, Card.A]
# cards = [1, 1, 2, 2, 3, 3]
exploring_phase = 0.0

""" Be careful when creating a model by playing against fixed strategies, because your model might not have all info_sets """
fixed_strategyA = None
fixed_strategyB = None
# fixed_strategyA = 'leduc-Lma-mccfr-6cards-EP0_1-iter100000'
# fixed_strategyB = 'leduc-ptM-Lma-mccfr-6cards-EP0_1-iter100000'
is_model_fixed = (fixed_strategyA is not None), (fixed_strategyB is not None)
is_there_a_learning_model = not (is_model_fixed[0] and is_model_fixed[1])
model_name = f'{algorithm}-{len(cards)}cards-EP{float_to_custom_string(exploring_phase)}-iter{iterations}'



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
        self.node_mapA = self.node_map
        self.node_mapB = self.node_map
        self.log_file = None
        self.create_nodes_from_pickle(fixed_strategyA, fixed_strategyB)

    def create_nodes_from_pickle(self, fileA, fileB):
        current_directory = os.path.dirname(os.path.abspath(__file__))

        if fileA is not None:
            node_mapA = {}
            blueprints_directory_pA = os.path.join(current_directory, f'../analysis/blueprints/{fileA}.pkl')
            with open(blueprints_directory_pA, 'rb') as f:
                dict_map_pA = pickle.load(f)
            for key, value in dict_map_pA.items():
                action_values, strategy = value
                actions = list(filter(lambda a: a.value in action_values, Actions))
                node_mapA[key] = self.Node(key, actions, strategy)
            self.node_mapA = MappingProxyType(node_mapA)
        if fileB is not None:
            node_mapB = {}
            blueprints_directory_pB = os.path.join(current_directory, f'../analysis/blueprints/{fileB}.pkl')
            with open(blueprints_directory_pB, 'rb') as f:
                dict_map_pB = pickle.load(f)
            for key, value in dict_map_pB.items():
                action_values, strategy = value
                actions = list(filter(lambda a: a.value in action_values, Actions))
                node_mapB[key] = self.Node(key, actions, strategy)
            self.node_mapB = MappingProxyType(node_mapB)

    def log(self, log_file):
        create_file(log_file)
        self.log_file = log_file
        log_format = 'Iteration: %(index)s\nAverage game valueA: %(avg_game_valueA)s\nAverage game valueB: %(avg_game_valueB)s\nAvg regretA: %(avg_regretA)s\nAvg regretB: %(avg_regretB)s\n'
        formatter = logging.Formatter(log_format)

        with open(log_file, 'w') as file:
            file_handler = logging.FileHandler(log_file, mode='w')
            file_handler.setFormatter(formatter)

            self.logger = logging.getLogger('')
            self.logger.setLevel(logging.DEBUG)
            self.logger.addHandler(file_handler)

    class Node:
        """ A node is an information set, which is the cards of the player and the history of the game."""
        def __init__(self, info_set, actions=Actions, strategy=None):

            self.actions = list(actions)
            self.num_actions = len(actions)
            self.info_set = info_set
            # The regret and strategies of a node refer to the last action taken to reach the node
            self.regret_sum = [0.0] * self.num_actions
            self.strategy = [0.0] * self.num_actions if strategy is None else strategy
            self.strategy_sum = [0.0] * self.num_actions
            self.times_regret_sum_updated = 0
            self.times_action_got_positive_reward = [0] * self.num_actions

        def get_strategy(self, realization_weight, is_exploring_phase, is_current_model_fixed):
            """Turn sum of regrets into a probability distribution for actions."""
            if not is_current_model_fixed:
                # r = random.random()
                # test_bad_actions = r < 0.05
                normalizing_sum = sum(max(regret, 0) for regret in self.regret_sum)
                for i in range(len(self.actions)):
                    if normalizing_sum > 0:
                        self.strategy[i] = max(self.regret_sum[i], 0) / normalizing_sum
                    else:
                        self.strategy[i] = 1.0 / self.num_actions
                    if not is_exploring_phase:
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
            filled_columns = 0
            for i in range(self.num_actions):
                for _ in range(self.actions[i].value - last_action_index):
                    formatted_avg_strategy += " "*13
                    filled_columns += 1
                formatted_avg_strategy += color_print(avg_strategy[i])
                filled_columns += 1
                last_action_index += 1
            
            for _ in range(len(Actions) - filled_columns):
                formatted_avg_strategy += " "*13

            min_width_info_set = f"{self.info_set:<10}"  # Ensuring minimum 10 characters for self.info_set
            return f"{min_width_info_set}: {formatted_avg_strategy} {self.times_regret_sum_updated}"
        
        def __lt__(self, other):
            return self.info_set < other.info_set
        
    def print_model(self, sum_of_rewards, iterations):
        columns = ""
        for action in Actions:
            columns += f"{action} "
        print(f"Columns   : {columns}")
        for n in sorted(self.node_map.values()):
            print(n.color_print())
        print(f"Size of model node map = {len(self.node_map)}, should be 249\n")

    def train(self, iterations):
        """If you call the train method multiple times with the same parameters, it won't produce the
        same output models, because the cards list starts shuffled differently usually, and because the seed
        needs to be set again."""
        # cards.sort(key=lambda x: x.value)

        print(f"Parameters: {iterations} iterations, {len(cards)} cards, {algorithm}, {exploring_phase} exploring phase\n")

        sum_of_rewards = [0] * 2
        """ p0 and p1 store, respectively, the probability of the player 0 and player 1 reaching the current node,
        from its "parent" node """
        p0 = 1
        p1 = 1
        chips = 2
        turn_bet_value = 1
        round_bet_value = 1
        played_current_phase = False
        final_avg_game_valueA = 0

        start_time = time.time()
        times_running = 1 if not is_model_fixed[0] and not is_model_fixed[1] else 2
        for p in range(times_running):
            model_A_is_p0 = 1 - p
            if is_model_fixed[0] is not None or is_model_fixed[1] is not None:
                if model_A_is_p0:
                    print(f"Player {fixed_strategyA or 'training model'} is starting.")
                else:
                    print(f"Player {fixed_strategyB or 'training model'} is starting.")

            for i in range(iterations):
                total_iteration = i + p * iterations + 1
                random.shuffle(cards)
                initial_player = (chips, turn_bet_value, round_bet_value, played_current_phase)
                players = (initial_player, initial_player)
                is_exploring_phase = i < exploring_phase * iterations
                iteration_reward = self.nash_equilibrium_algorithm(cards, "", p0, p1, players, 'preflop', is_exploring_phase, model_A_is_p0)
                sum_of_rewards[0] += model_A_is_p0 * (iteration_reward * (not is_exploring_phase))
                sum_of_rewards[1] += (not model_A_is_p0) * (iteration_reward * (not is_exploring_phase))
                
                # avg_regret = 0
                # for n in self.node_mapA.values():
                #     avg_regret += sum(n.regret_sum)
                # for n in self.node_mapB.values():
                #     avg_regret += sum(n.regret_sum)

                # avg_regret /= (len(self.node_mapA.values()) + len(self.node_mapB.values())) * (i+1)
                sample_iteration = {
                    'index': i,
                    'avg_game_valueA': final_avg_game_valueA or sum_of_rewards[0] / max((i + 1) - exploring_phase * iterations, 1),
                    'avg_game_valueB': sum_of_rewards[1] / max((i + 1) - exploring_phase * iterations, 1),
                    'avg_regretA': sum((sum(n.regret_sum) / len(n.regret_sum)) for n in self.node_mapA.values()) / (len(self.node_mapA.values()) * total_iteration),
                    'avg_regretB': sum((sum(n.regret_sum) / len(n.regret_sum)) for n in self.node_mapB.values()) / (len(self.node_mapB.values()) * total_iteration),
                }

                # if i < 10:
                #     self.logger.info('', extra=sample_iteration)
                self.logger.info('', extra=sample_iteration)

            final_avg_game_valueA = sum_of_rewards[0] / (iterations * (1 - exploring_phase))

        # if at least one of the players is not a fixed strategy, print their average strategy

        algorithm_id = generate_random_string(3)
        avg_game_valueA = sum_of_rewards[0] / iterations
        print(f"Average game value for {fixed_strategyA or algorithm_id} as p0: {avg_game_valueA}")
        avg_game_valueB = sum_of_rewards[1] / iterations
        print(f"Average game value for {fixed_strategyB or algorithm_id} as p0: {avg_game_valueB}")
        adversary_id = ''
        if is_there_a_learning_model:
            if is_model_fixed[0]:
                match = re.search(r'-(\w{3})', fixed_strategyA)
                if match:
                    adversary_id = '-' + match.group(1)
            elif is_model_fixed[1]:
                match = re.search(r'-(\w{3})', fixed_strategyB)
                if match:
                    adversary_id = '-' + match.group(1)

            self.print_model(sum_of_rewards, iterations)
            pickle_name = f'{algorithm_id}{adversary_id}-{model_name}.pkl'
            final_strategy_path = f'../analysis/blueprints/leduc-{pickle_name}'
            create_file(final_strategy_path)
            node_dict = {}
            for n in sorted(self.node_map.values()):
                node_dict[n.info_set] = (list(map(lambda a: a.value, n.actions)), n.get_average_strategy())
            with open(final_strategy_path, 'wb') as file:
                pickle.dump(node_dict, file)
            
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"{algorithm_id}{adversary_id} {model_name} took {elapsed_time} seconds to run.")

    def get_node(self, info_set, is_model_B, is_current_model_fixed, possible_actions=None):
        """Returns a node for the given information set. Creates the node if it doesn't exist."""
        if not is_current_model_fixed:
            return self.node_map.setdefault(info_set, self.Node(info_set, possible_actions))
        else:
            if is_model_B:
                return self.node_mapB[info_set]
            else:
                return self.node_mapA[info_set]


    def perform_action(self, cards, history, p0, p1, players, phase, strategy, player, action, action_index, is_exploring_phase, model_A_is_p0, alternative_play=None):
        action_char = action_symbol[action.value]
        next_history = history + action_char
        # node_action_utility receives a negative values because we are alternating between players,
        # and in the Leduc Poker game, the reward for a player is the opposite of the other player's reward
        if player == 0:
            node_action_utility = -self.nash_equilibrium_algorithm(cards, next_history, p0 * strategy[action_index], p1, players, phase, is_exploring_phase, model_A_is_p0, alternative_play)
        else:
            node_action_utility = -self.nash_equilibrium_algorithm(cards, next_history, p0, p1 * strategy[action_index], players, phase, is_exploring_phase, model_A_is_p0, alternative_play)

        return node_action_utility

    def nash_equilibrium_algorithm(self, cards, history, p0, p1, players, phase, is_exploring_phase, model_A_is_p0, alternative_play=None):
        # On the first iteration, the history is empty, so the first player starts
        plays = len(history.replace("/", ""))
        player = plays % 2
        opponent = 1 - player
        model_A_is_p0 == player
        is_model_B = player == model_A_is_p0

        is_current_model_fixed = is_model_fixed[is_model_B]
        possible_actions, rewards, next_phase_started = get_possible_actions(history, cards, player, opponent, players, phase, Actions)
        updated_phase = 'flop' if next_phase_started else phase
        updated_history = history + '/' if next_phase_started else history
        public_card = cards[2] if updated_phase == 'flop' else ""
        info_set = str(cards[player]) + str(public_card) + updated_history
        if possible_actions is None:
            return rewards
        
        if next_phase_started:
            # Player 0 should start the leduc flop
            assert player == 0

        node = self.get_node(info_set, is_model_B, is_current_model_fixed, possible_actions)

        if is_exploring_phase and not is_current_model_fixed:
            strategy = [1.0 / len(possible_actions)] * len(possible_actions)
        else:
            strategy = node.get_strategy(p0 if player == 0 else p1, is_exploring_phase, is_current_model_fixed) 
        node_actions_utilities = [0.0] * len(possible_actions)

        if algorithm == 'mccfr' or is_current_model_fixed:
            other_actions = list(possible_actions)  # Get a list of actions in the order of the enum
            chosen_action = node.get_action(strategy)
            other_actions.remove(Actions(chosen_action))  # Remove the first action from the list
            action_index = node.actions.index(chosen_action)

            updated_players = set_bet_value(player, players, chosen_action, next_phase_started)

            # Play chosen action according to the strategy
            node_chosen_action_utility = self.perform_action(cards, updated_history, p0, p1, updated_players, updated_phase, strategy, player, chosen_action, action_index, is_exploring_phase, model_A_is_p0, alternative_play)
            node_actions_utilities[action_index] = node_chosen_action_utility

            # Play for other actions
            if not is_current_model_fixed and alternative_play != opponent:
                for action in other_actions:
                    action_index = node.actions.index(action)
                    # passar um parametro para mccfr dizendo que se é jogada alternativa, e de quê jogador, se for do jogador 1, ai não tem for na jogada do jogador 0
                    updated_players = set_bet_value(player, players, action, next_phase_started)
                    node_action_utility = self.perform_action(cards, updated_history, p0, p1, updated_players, updated_phase, strategy, player, action, action_index, is_exploring_phase, model_A_is_p0, alternative_play=player)
                    node_actions_utilities[action_index] = node_action_utility

                # if len(info_set) > 1 and info_set[0] == info_set[1]:
                #     print('j')
                for action in possible_actions:
                    action_index = node.actions.index(action)
                    regret = node_actions_utilities[action_index] - node_chosen_action_utility
                    node.times_action_got_positive_reward[action_index] += (regret >= 0)

                    # if node.times_action_got_positive_reward[action_index] == node.times_regret_sum_updated and node.times_regret_sum_updated > 20 and action != Actions.PASS:
                    #     node.regret_sum[action_index] += (p1 if player == 0 else p0) * regret * 2
                    # else:
                    #     node.regret_sum[action_index] += (p1 if player == 0 else p0) * regret
                    node.regret_sum[action_index] += (p1 if player == 0 else p0) * regret
                node.times_regret_sum_updated += 1

            return node_chosen_action_utility
        
        elif algorithm == 'cfr':
            node_util = 0
            for action in possible_actions:
                action_index = node.actions.index(action)
                updated_players = set_bet_value(player, players, action, next_phase_started)
                node_action_utility = self.perform_action(cards, updated_history, p0, p1, updated_players, updated_phase, strategy, player, action, action_index, is_exploring_phase, model_A_is_p0)
                node_actions_utilities[action_index] = node_action_utility
                node_util += strategy[action_index] * node_action_utility

            if not is_current_model_fixed:
                for action in possible_actions:
                    action_index = node.actions.index(action)
                    regret = node_actions_utilities[action_index] - node_util
                    node.regret_sum[action_index] += (p1 if player == 0 else p0) * regret

            return node_util

        else:
            raise Exception("Algorithm not found: " + algorithm)
        

if __name__ == "__main__":
    trainer = ModLeducTrainer()
    trainer.log(f'../analysis/logs/{model_name}.log')
    trainer.train(iterations)