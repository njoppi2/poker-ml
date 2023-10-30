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
from concurrent.futures import ProcessPoolExecutor


# num_processes = multiprocessing.cpu_count()
# pool = multiprocessing.Pool(processes=num_processes)  # Create a Pool of worker processes

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

    def __init__(self, iterations, algorithm, cards, exploring_phase, exploration_type, total_action_symbol, min_reality_weight, decrese_weight_of_initial_strategies, max_bet, fixed_strategyA=None, fixed_strategyB=None):
        self.node_map = {}
        self.node_mapA = self.node_map
        self.node_mapB = self.node_map
        self.log_file = None

        self.iterations = iterations
        self.algorithm = algorithm
        self.cards = cards
        self.exploring_phase = exploring_phase
        self.exploration_type = exploration_type
        self.fixed_strategyA = fixed_strategyA
        self.fixed_strategyB = fixed_strategyB
        self.max_bet = max_bet
        self.model_name = f'{self.algorithm}-{len(self.cards)}cards-{self.max_bet}maxbet-EP{self.exploration_type}{float_to_custom_string(self.exploring_phase)}-mRW{float_to_custom_string(min_reality_weight)}-iter{self.iterations}'

        self.is_model_fixed = (fixed_strategyA is not None), (fixed_strategyB is not None)
        self.is_there_a_learning_model = not (self.is_model_fixed[0] and self.is_model_fixed[1])

        self.Actions = [{"name": "PASS", "value": 0}]

        for i in range(1, max_bet + 1):
            self.Actions.append({"name": f"BET{i}", "value": i})

        self.total_num_actions = len(self.Actions)
        self.action_symbol = total_action_symbol[:self.total_num_actions]

        self.min_reality_weight = min_reality_weight
        self.decrese_weight_of_initial_strategies = decrese_weight_of_initial_strategies

        self.create_nodes_from_pickle(fixed_strategyA, fixed_strategyB)
        self.log(f'../analysis/logs/{self.model_name}.log')
        self.train()
        

    def create_nodes_from_pickle(self, fileA, fileB):
        current_directory = os.path.dirname(os.path.abspath(__file__))

        if fileA is not None:
            node_mapA = {}
            blueprints_directory_pA = os.path.join(current_directory, f'../analysis/blueprints/{fileA}.pkl')
            with open(blueprints_directory_pA, 'rb') as f:
                dict_map_pA = pickle.load(f)
            for key, value in dict_map_pA.items():
                action_values, strategy = value
                actions = list(filter(lambda a: a['value'] in action_values, self.Actions))
                node_mapA[key] = self.Node(key, actions, strategy)
            self.node_mapA = MappingProxyType(node_mapA)
        if fileB is not None:
            node_mapB = {}
            blueprints_directory_pB = os.path.join(current_directory, f'../analysis/blueprints/{fileB}.pkl')
            with open(blueprints_directory_pB, 'rb') as f:
                dict_map_pB = pickle.load(f)
            for key, value in dict_map_pB.items():
                action_values, strategy = value
                actions = list(filter(lambda a: a['value'] in action_values, self.Actions))
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
        def __init__(self, info_set, actions, strategy=None):

            self.actions = list(actions)
            self.num_actions = len(actions)
            self.info_set = info_set
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

            min_width_info_set = f"{self.info_set:<10}"  # Ensuring minimum 10 characters for self.info_set
            return f"{min_width_info_set}: {formatted_avg_strategy} {self.times_regret_sum_updated}  {self.times_strategy_sum_updated}  {self.times_got_strategy_without_0_rw}  {self.times_got_strategy_without_0_strat}"
        
        def __lt__(self, other):
            return self.info_set < other.info_set
        
    def print_model(self, total_actions, sum_of_rewards, iterations):
        columns = ""
        for action in total_actions:
            columns += f"{action} "
        print(f"Columns   : {columns}")
        for n in sorted(self.node_map.values()):
            print(n.color_print_node(self.Actions))
        print(f"Size of model node map = {len(self.node_map)}, should be 249\n")

    def train(self):
        """If you call the train method multiple times with the same parameters, it won't produce the
        same output models, because the cards list starts shuffled differently usually, and because the seed
        needs to be set again."""
        # cards.sort(key=lambda x: x.value)

        print(f"Parameters: {self.model_name}\n")

        sum_of_rewards = [0] * 2
        """ p0 and p1 store, respectively, the probability of the player 0 and player 1 reaching the current node,
        from its "parent" node """
        iterations = self.iterations
        p0 = 1
        p1 = 1
        chips = self.total_num_actions - 1
        turn_bet_value = 1
        round_bet_value = 1
        played_current_phase = False
        final_avg_game_valueA = 0

        start_time = time.time()
        times_running = 1 if not self.is_model_fixed[0] and not self.is_model_fixed[1] else 2
        for p in range(times_running):
            model_A_is_p0 = 1 - p
            if self.is_model_fixed[0] is not None or self.is_model_fixed[1] is not None:
                if model_A_is_p0:
                    print(f"Player {self.fixed_strategyA or 'training model'} is starting.")
                else:
                    print(f"Player {self.fixed_strategyB or 'training model'} is starting.")

            for i in range(iterations):
                total_iteration = i + p * iterations + 1
                random.shuffle(self.cards)
                initial_player = (chips, turn_bet_value, round_bet_value, played_current_phase)
                players = (initial_player, initial_player)
                is_exploring_phase = i < self.exploring_phase * iterations
                iteration_reward = self.nash_equilibrium_algorithm(self.cards, "", p0, p1, players, 'preflop', is_exploring_phase, model_A_is_p0)
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
                    'avg_game_valueA': final_avg_game_valueA or sum_of_rewards[0] / max((i + 1) - self.exploring_phase * iterations, 1),
                    'avg_game_valueB': sum_of_rewards[1] / max((i + 1) - self.exploring_phase * iterations, 1),
                    'avg_regretA': sum((sum(n.regret_sum) / len(n.regret_sum)) for n in self.node_mapA.values()) / (len(self.node_mapA.values()) * total_iteration),
                    'avg_regretB': sum((sum(n.regret_sum) / len(n.regret_sum)) for n in self.node_mapB.values()) / (len(self.node_mapB.values()) * total_iteration),
                }

                # if i < 10:
                #     self.logger.info('', extra=sample_iteration)
                self.logger.info('', extra=sample_iteration)

            final_avg_game_valueA = sum_of_rewards[0] / (iterations * (1 - self.exploring_phase))

        # if at least one of the players is not a fixed strategy, print their average strategy
        algorithm_id = generate_random_string(3)
        avg_game_valueA = sum_of_rewards[0] / iterations
        print(f"Average game value for {self.fixed_strategyA or algorithm_id} as p0: {avg_game_valueA}")
        avg_game_valueB = sum_of_rewards[1] / iterations
        print(f"Average game value for {self.fixed_strategyB or algorithm_id} as p0: {avg_game_valueB}")
        adversary_id = ''
        adversary_name = ''
        if self.is_there_a_learning_model:
            if self.is_model_fixed[0]:
                adversary_id = '-' + self.fixed_strategyA[:3]
                adversary_name = self.fixed_strategyA
            elif self.is_model_fixed[1]:
                adversary_id = '-' + self.fixed_strategyB[:3]
                adversary_name = self.fixed_strategyB

            self.print_model(self.Actions, sum_of_rewards, iterations)
            pickle_name = f'{algorithm_id}{adversary_id}-{self.model_name}.pkl'
            final_strategy_path = f'../analysis/blueprints/{pickle_name}'
            create_file(final_strategy_path)
            node_dict = {}
            for n in sorted(self.node_map.values()):
                node_dict[n.info_set] = (list(map(lambda a: a['value'], n.actions)), n.get_average_strategy())
            with open(final_strategy_path, 'wb') as file:
                pickle.dump(node_dict, file)
            
        end_time = time.time()
        elapsed_time = end_time - start_time
        if adversary_name:
            print(f'model was trained against: {adversary_name}')
        if self.is_there_a_learning_model:
            print(f"{algorithm_id}{adversary_id}-{self.model_name} took {elapsed_time} seconds to run.")

    def get_node(self, info_set, is_model_B, is_current_model_fixed, possible_actions=None):
        """Returns a node for the given information set. Creates the node if it doesn't exist."""
        if not is_current_model_fixed:
            return self.node_map.setdefault(info_set, self.Node(info_set, possible_actions))
        else:
            if is_model_B:
                return self.node_mapB[info_set]
            else:
                return self.node_mapA[info_set]
            
    def perform_action_wrapper(self, args):
        (cards, updated_history, p0, p1, updated_players, updated_phase, strategy, player, action, action_index, is_exploring_phase, model_A_is_p0, alternative_play) = args
        return self.perform_action(cards, updated_history, p0, p1, updated_players, updated_phase, strategy, player, action, action_index, is_exploring_phase, model_A_is_p0, alternative_play), action_index

    def perform_action(self, cards, history, p0, p1, players, phase, strategy, player, action, action_index, is_exploring_phase, model_A_is_p0, alternative_play=None):
        action_char = self.action_symbol[action['value']]
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

        is_current_model_fixed = self.is_model_fixed[is_model_B]
        possible_actions, rewards, next_phase_started = get_possible_actions(history, cards, player, opponent, players, phase, self.Actions)
        updated_phase = 'flop' if next_phase_started else phase
        updated_history = history + '/' if next_phase_started else history
        public_card = cards[2] if updated_phase == 'flop' else ""
        info_set = str(cards[player]) + str(public_card) + updated_history
        explore_with_cfr = self.exploration_type == "cfr" and is_exploring_phase

        if possible_actions is None:
            return rewards
        
        if next_phase_started:
            # Player 0 should start the leduc flop
            assert player == 0

        node = self.get_node(info_set, is_model_B, is_current_model_fixed, possible_actions)
        if is_exploring_phase and not is_current_model_fixed:
            strategy = [1.0 / len(possible_actions)] * len(possible_actions)
        else:
            strategy = node.get_strategy(p0 if player == 0 else p1, is_exploring_phase, is_current_model_fixed, self.min_reality_weight, self.decrese_weight_of_initial_strategies, info_set) 
        node_actions_utilities = [0.0] * len(possible_actions)

        if (self.algorithm == 'mccfr' and not explore_with_cfr) or is_current_model_fixed:
            other_actions = list(possible_actions)  # Get a list of actions in the order of the enum
            chosen_action = node.get_action(strategy)
            other_actions.remove(chosen_action)  # Remove the first action from the list
            chosen_action_index = node.actions.index(chosen_action)

            updated_players = set_bet_value(player, players, chosen_action["value"], next_phase_started)

            # Play chosen action according to the strategy
            node_actions_utilities[chosen_action_index] = self.perform_action(cards, updated_history, p0, p1, updated_players, updated_phase, strategy, player, chosen_action, chosen_action_index, is_exploring_phase, model_A_is_p0, alternative_play)

            # Play for other actions
            if not is_current_model_fixed and alternative_play != opponent:
                if plays <= -1:
                    with ProcessPoolExecutor() as executor:
                        arguments = []
                        for action in other_actions:
                            action_index = node.actions.index(action)
                            is_chosen_action = action_index == chosen_action_index
                            args = (cards, updated_history, p0, p1, set_bet_value(player, players, action["value"], next_phase_started), updated_phase, strategy, player, action, node.actions.index(action), is_exploring_phase, model_A_is_p0, alternative_play if is_chosen_action else player)
                            arguments.append(args)
                        results = executor.map(self.perform_action_wrapper, arguments)
                    # Process results
                    for result in results:
                        utility, index = result
                        node_actions_utilities[index] = utility
                else:
                    for action in other_actions:
                        action_index = node.actions.index(action)
                        # passar um parametro para mccfr dizendo que se é jogada alternativa, e de quê jogador, se for do jogador 1, ai não tem for na jogada do jogador 0
                        updated_players = set_bet_value(player, players, action["value"], next_phase_started)
                        node_action_utility = self.perform_action(cards, updated_history, p0, p1, updated_players, updated_phase, strategy, player, action, action_index, is_exploring_phase, model_A_is_p0, alternative_play=player)
                        node_actions_utilities[action_index] = node_action_utility

                for action in possible_actions:
                    action_index = node.actions.index(action)
                    regret = node_actions_utilities[action_index] - node_actions_utilities[chosen_action_index]
                    node.times_action_got_positive_reward[action_index] += (regret >= 0)

                    # if node.times_action_got_positive_reward[action_index] == node.times_regret_sum_updated and node.times_regret_sum_updated > 20 and action != self.Actions.PASS:
                    #     node.regret_sum[action_index] += (p1 if player == 0 else p0) * regret * 2
                    # else:
                    #     node.regret_sum[action_index] += (p1 if player == 0 else p0) * regret
                    node.regret_sum[action_index] += (p1 if player == 0 else p0) * regret
                node.times_regret_sum_updated += 1

            return node_actions_utilities[chosen_action_index]
        
        elif explore_with_cfr or self.algorithm == 'cfr':
            node_util = 0
            for action in possible_actions:
                action_index = node.actions.index(action)
                updated_players = set_bet_value(player, players, action["value"], next_phase_started)
                node_action_utility = self.perform_action(cards, updated_history, p0, p1, updated_players, updated_phase, strategy, player, action, action_index, is_exploring_phase, model_A_is_p0)
                node_actions_utilities[action_index] = node_action_utility
                node_util += strategy[action_index] * node_action_utility

            if not is_current_model_fixed:
                for action in possible_actions:
                    action_index = node.actions.index(action)
                    regret = node_actions_utilities[action_index] - node_util
                    node.regret_sum[action_index] += (p1 if player == 0 else p0) * regret
                node.times_regret_sum_updated += 1

            return node_util

        else:
            raise Exception("Algorithm not found: " + self.algorithm)
        

if __name__ == "__main__":

    random.seed(42)

    _iterations = 1000
    _algorithm = 'mccfr'
    cards = [Card.Q, Card.Q, Card.K, Card.K, Card.A, Card.A]
    _exploring_phase = 0
    _exploration_type = "cfr"

    """ Be careful when creating a model by playing against fixed strategies, because your model might not have all info_sets """
    _fixed_strategyA = None
    _fixed_strategyB = None
    # _fixed_strategyA = 'Cyz-cfr-6cards-2maxbet-EPcfr0-mRW0_0001-iter10000'
    # _fixed_strategyB = 'pbD-Cyz-mccfr-6cards-2maxbet-EPcfr0-mRW0_0001-iter100000'
    max_bet = 3

    total_action_symbol = ['p', 'b', 'B', '3', '4', '5', '6', '7', '8', '9', 'q']
    min_reality_weight = 0.000
    decrese_weight_of_initial_strategies = False

    trainer = ModLeducTrainer(_iterations, _algorithm, cards, _exploring_phase, _exploration_type, total_action_symbol, min_reality_weight, decrese_weight_of_initial_strategies, max_bet, _fixed_strategyA, _fixed_strategyB)