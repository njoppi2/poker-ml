import random
from functions import color_print
from enum import Enum
from collections import Counter
from treys import Evaluator, Deck
from treys import Card as Card2
import heapq
from itertools import combinations

evaluator = Evaluator()

class Card(Enum):
    TWO = 2
    THREE = 3
    FOUR = 5
    FIVE = 7
    SIX = 11
    SEVEN = 13
    EIGHT = 17
    NINE = 19
    TEN = 23
    JACK = 29
    QUEEN = 31
    KING = 37
    ACE = 41

    def __str__(self):
        return self.name
    
    def __lt__(self, other):
        return self.value < other.value


def get_turn_board_abstraction(board, hand):
    phase = 'river'
    board_value = 1
    for board_card in board:
        board_value *= Card2.get_prime(board_card)

    if board_value % 41 == 0:
        first_card = 'ace'
    elif board_value % 37 == 0 or board_value % 31 == 0 or board_value % 29 == 0:
        first_card = 'high'
    else:
        first_card = 'low'

    level_5_straightness = board_value % 210 == 0 or board_value % 1155 == 0 or board_value % 5005 == 0 or board_value % 17017 == 0 or board_value % 46189 == 0 or board_value % 96577 == 0 or board_value % 215441 == 0 or board_value % 392863 == 0 or board_value % 765049 == 0
    # level_4_straightness checks if board_value is a multiplication of 4 primes that are consecutive with a gap of 1 prime in between 
    level_4_straightness = not level_5_straightness and (board_value % 4305 == 0
        or board_value % 330 == 0 or board_value % 462 == 0 or board_value % 770 == 0
        or board_value % 1365 == 0 or board_value % 2145 == 0 or board_value % 3003 == 0
        or board_value % 6545 == 0 or board_value % 7735 == 0 or board_value % 12155 == 0
        or board_value % 19019 == 0 or board_value % 24871 == 0 or board_value % 29393 == 0
        or board_value % 55913 == 0 or board_value % 62491 == 0 or board_value % 81719 == 0
        or board_value % 121771 == 0 or board_value % 147407 == 0 or board_value % 164749 == 0
        or board_value % 230299 == 0 or board_value % 290377 == 0 or board_value % 351509 == 0
        or board_value % 468901 == 0 or board_value % 501239 == 0 or board_value % 631997 == 0
        or board_value % 847757 == 0 or board_value % 1011839 == 0 or board_value % 1081621 == 0 or board_value % 1363783 == 0
    )
    level_3_straightness = not level_4_straightness and not level_5_straightness and (
        board_value % 20677 == 0 or board_value % 12673 == 0 or board_value % 7429 == 0 or board_value % 4199 == 0 or board_value % 2431 == 0 or board_value % 1001 == 0 or board_value % 385 == 0 or board_value % 105 == 0
        )
    level_2_straightness = not level_3_straightness and not level_4_straightness and not level_5_straightness and (
        board_value % 30 == 0 
        or board_value % 42 == 0 or board_value % 70 == 0
        or board_value % 165 == 0 or board_value % 231 == 0
        or board_value % 455 == 0 or board_value % 715 == 0
        or board_value % 1309 == 0 or board_value % 1547 == 0
        or board_value % 2717 == 0 or board_value % 3553 == 0
        or board_value % 5083 == 0 or board_value % 5681 == 0
        or board_value % 9367 == 0 or board_value % 11339 == 0
        or board_value % 13547 == 0 or board_value % 17081 == 0
        or board_value % 24679 == 0 or board_value % 26381 == 0
        or board_value % 33263 == 0)
    level_1_straightness = not level_2_straightness and not level_3_straightness and not level_4_straightness and not level_5_straightness and (
        board_value % 246 == 0
        or board_value % 410 == 0 or board_value % 615 == 0 
        # consecutive with 2 gaps of 1 prime in between
        or board_value % 110 == 0 or board_value % 273 == 0 or board_value % 935 == 0 or board_value % 1729 == 0 or board_value % 4301 == 0 or board_value % 7163 == 0 or board_value % 12121 == 0 or board_value % 20387 == 0 or board_value % 29233 == 0
        or board_value % 36859 == 0 or board_value % 43993 == 0 or board_value % 47027 == 0
        # consecutive with 1 gap of 2 primes in between
        or board_value % (2*3*11) == 0 or board_value % (2*7*11) == 0
        or board_value % (3*5*13) == 0 or board_value % (3*11*13) == 0
        or board_value % (5*7*17) == 0 or board_value % (5*13*17) == 0
        or board_value % (7*11*19) == 0 or board_value % (7*17*19) == 0
        or board_value % (11*13*23) == 0 or board_value % (11*19*23) == 0
        or board_value % (13*17*29) == 0 or board_value % (13*23*29) == 0
        or board_value % (17*19*31) == 0 or board_value % (17*29*31) == 0
        or board_value % (19*23*37) == 0 or board_value % (19*31*37) == 0
        or board_value % (23*29*41) == 0 or board_value % (23*37*41) == 0
    )
    
    if level_5_straightness:
        straightness = 's5'
    elif level_4_straightness:
        straightness = 's4'
    elif level_3_straightness:
        straightness = 's3'
    elif level_2_straightness:
        straightness = 's2'
    elif level_1_straightness:
        straightness = 's1'
    else:
        straightness = 's0'

    suit_value = [Card2.get_suit_int(card) for card in board]
    suit_counter = {}
    for suit in suit_value:
        suit_counter[suit] = suit_counter.get(suit, 0) + 1

    # Find the most common result and its number of occurrences
    most_common_suit = max(suit_counter, key=suit_counter.get)
    board_flushness = suit_counter[most_common_suit]
    flushness = 'f' + str(board_flushness)

    # prime numbers to the power of 4
    quads = (board_value % 16 == 0 or board_value % 81 == 0 or board_value % 625 == 0 or board_value % 2401 == 0 or board_value % 14641 == 0 or board_value % 28561 == 0 or board_value % 83521 == 0 or board_value % 130321 == 0 or board_value % 279841 == 0 or board_value % 707281 == 0 or board_value % 923521 == 0 or board_value % 1874161 == 0 or board_value % 2825761 == 0)

    # prime numbers cubed
    trips = not quads and (board_value % 8 == 0 or board_value % 27 == 0 or board_value % 125 == 0 or board_value % 343 == 0 or board_value % 1331 == 0 or board_value % 2197 == 0 or board_value % 4913 == 0
        or board_value % 12167 == 0 or board_value % 24389 == 0 or board_value % 29791 == 0 or board_value % 50653 == 0 or board_value % 68921 == 0)
    

    # prime numbers squared
    deuce_pair = board_value % 4 == 0
    trey_pair = board_value % 9 == 0
    four_pair = board_value % 25 == 0
    five_pair = board_value % 49 == 0
    six_pair = board_value % 121 == 0
    seven_pair = board_value % 169 == 0
    eight_pair = board_value % 289 == 0
    nine_pair = board_value % 361 == 0
    ten_pair = board_value % 529 == 0
    jack_pair = board_value % 841 == 0
    queen_pair = board_value % 961 == 0
    king_pair = board_value % 1369 == 0
    ace_pair = board_value % 1681 == 0
    
    two_pair = (deuce_pair + trey_pair + four_pair + five_pair + six_pair + seven_pair + eight_pair + nine_pair + ten_pair + jack_pair + queen_pair + king_pair + ace_pair) == 2
    pair = not trips and not two_pair and (deuce_pair or trey_pair or four_pair or five_pair or six_pair or seven_pair or eight_pair or nine_pair or ten_pair or jack_pair or queen_pair or king_pair or ace_pair)
    

    if quads or (trips and two_pair):
        repetitiveness = 'nuts'
    elif trips:
        repetitiveness = 'trips'
    elif two_pair:
        repetitiveness = 'two_pair'
    elif pair:
        repetitiveness = 'pair'
    else:
        repetitiveness = 'different'


    """ PLAYER """

    first_hand_card = Card2.get_prime(hand[0])
    second_hand_card = Card2.get_prime(hand[1])

    hand_value = first_hand_card * second_hand_card
    total_player_value = hand_value * board_value

    highest_board_card_raw, second_highest_board_card_raw = heapq.nlargest(2, board)
    highest_board_card = Card2.get_prime(highest_board_card_raw)
    second_highest_board_card = Card2.get_prime(second_highest_board_card_raw)

    # prime numbers squared
    player_deuce_pair = total_player_value % 4 == 0
    player_trey_pair = total_player_value % 9 == 0
    player_four_pair = total_player_value % 25 == 0
    player_five_pair = total_player_value % 49 == 0
    player_six_pair = total_player_value % 121 == 0
    player_seven_pair = total_player_value % 169 == 0
    player_eight_pair = total_player_value % 289 == 0
    player_nine_pair = total_player_value % 361 == 0
    player_ten_pair = total_player_value % 529 == 0
    player_jack_pair = total_player_value % 841 == 0
    player_queen_pair = total_player_value % 961 == 0
    player_king_pair = total_player_value % 1369 == 0
    player_ace_pair = total_player_value % 1681 == 0

    # Quads
    player_has_exclusive_quads = not quads and (total_player_value % 16 == 0 or total_player_value % 81 == 0 or total_player_value % 625 == 0 or total_player_value % 2401 == 0 or total_player_value % 14641 == 0 or total_player_value % 28561 == 0 or total_player_value % 83521 == 0 or total_player_value % 130321 == 0 or total_player_value % 279841 == 0 or total_player_value % 707281 == 0 or total_player_value % 923521 == 0 or total_player_value % 1874161 == 0 or total_player_value % 2825761 == 0)    
    
    # Flush
    player_suit_value = [Card2.get_suit_int(card) for card in board + hand]
    player_suit_counter = {}
    for player_suit in player_suit_value:
        player_suit_counter[player_suit] = player_suit_counter.get(player_suit, 0) + 1

    # Find the most common result and its number of occurrences
    most_common_player_suit = max(player_suit_counter, key=player_suit_counter.get)
    player_suit_occurrences = player_suit_counter[most_common_player_suit]

    player_has__exclusive_flush = player_suit_occurrences >= 5 > board_flushness
    player_has_exclusive_flush_draw = not player_has__exclusive_flush and player_suit_occurrences == 4 > board_flushness
    # player_has_exclusive_flush_2draw = not player_has__exclusive_flush and not player_has_exclusive_flush_draw and player_suit_occurrences == 3 > board_flushness

    # Straight
    player_has_straight = total_player_value % (41*2*3*5*7) == 0 or total_player_value % (2*3*5*7*11) == 0 or total_player_value % (3*5*7*11*13) == 0 or total_player_value % (5*7*11*13*17) == 0 or total_player_value % (7*11*13*17*19) == 0 or total_player_value % (11*13*17*19*23) == 0 or total_player_value % (13*17*19*23*29) == 0 or total_player_value % (17*19*23*29*31) == 0 or total_player_value % (19*23*29*31*37) == 0 or total_player_value % (23*29*31*37*41) == 0
    player_has_exclusive_2outs_straight = not player_has_straight and not level_5_straightness and total_player_value % 210 == 0 and total_player_value % 1155 == 0 or total_player_value % 5005 == 0 or total_player_value % 17017 == 0 or total_player_value % 46189 == 0 or total_player_value % 96577 == 0 or total_player_value % 215441 == 0 or total_player_value % 392863 == 0 or total_player_value % 765049 == 0    
    player_has_exclusive_1out_straight = not player_has_straight and not player_has_exclusive_2outs_straight and not level_4_straightness and (board_value % 4305 == 0
        or total_player_value % 330 == 0 or total_player_value % 462 == 0 or total_player_value % 770 == 0
        or total_player_value % 1365 == 0 or total_player_value % 2145 == 0 or total_player_value % 3003 == 0
        or total_player_value % 6545 == 0 or total_player_value % 7735 == 0 or total_player_value % 12155 == 0
        or total_player_value % 19019 == 0 or total_player_value % 24871 == 0 or total_player_value % 29393 == 0
        or total_player_value % 55913 == 0 or total_player_value % 62491 == 0 or total_player_value % 81719 == 0
        or total_player_value % 121771 == 0 or total_player_value % 147407 == 0 or total_player_value % 164749 == 0
        or total_player_value % 230299 == 0 or total_player_value % 290377 == 0 or total_player_value % 351509 == 0
        or total_player_value % 468901 == 0 or total_player_value % 501239 == 0 or total_player_value % 631997 == 0
        or total_player_value % 847757 == 0 or total_player_value % 1011839 == 0 or total_player_value % 1081621 == 0 or total_player_value % 1363783 == 0
    )

    # Straight Flush
    player_has_straight_flush = player_has_straight and player_has__exclusive_flush and evaluator.evaluate(board, hand) >= 10
    
    # Trips
    player_has_exclusive_trips = not player_has_exclusive_quads and not trips and (total_player_value % 8 == 0 or total_player_value % 27 == 0 or total_player_value % 125 == 0 or total_player_value % 343 == 0 or total_player_value % 1331 == 0 or total_player_value % 2197 == 0 or total_player_value % 4913 == 0
        or total_player_value % 12167 == 0 or total_player_value % 24389 == 0 or total_player_value % 29791 == 0 or total_player_value % 50653 == 0 or total_player_value % 68921 == 0)
    
    # Two pair
    player_has_exclusive_two_pair = not player_has_exclusive_quads and not two_pair and (player_deuce_pair + player_trey_pair + player_four_pair + player_five_pair + player_six_pair + player_seven_pair + player_eight_pair + player_nine_pair + player_ten_pair + player_jack_pair + player_queen_pair + player_king_pair + player_ace_pair) == 2

    # Pair
    pocket_pair_value = not player_has_exclusive_quads and not player_has_exclusive_trips and 2 if (hand_value % 4 == 0) else 3 if (hand_value % 9 == 0) else 5 if (hand_value % 25 == 0) else 7 if (hand_value % 49 == 0) else 11 if (hand_value % 121 == 0) else 13 if (hand_value % 169 == 0) else 17 if (hand_value % 289 == 0) else 19 if (hand_value % 361 == 0) else 23 if (hand_value % 529 == 0) else 29 if (hand_value % 841 == 0) else 31 if (hand_value % 961 == 0) else 37 if (hand_value % 1369 == 0) else 41 if (hand_value % 1681 == 0) else 0
    player_has_higher_pocket_pair = not player_has_exclusive_quads and not player_has_exclusive_trips and pocket_pair_value > highest_board_card
    player_has_highest_board_pair = not player_has_exclusive_quads and not player_has_exclusive_trips and hand_value % highest_board_card == 0
    player_has_second_highest_board_pair = not player_has_exclusive_quads and not player_has_exclusive_trips and hand_value % second_highest_board_card == 0 or pocket_pair_value >= second_highest_board_card
    player_has_pair = not player_has_exclusive_quads and not player_has_exclusive_trips and board_value % first_hand_card == 0 or board_value % second_hand_card == 0 or first_hand_card == second_hand_card

    if player_has_straight_flush or player_has_exclusive_quads or (player_has_exclusive_trips and player_has_exclusive_two_pair):
        player_hand_quality = 'nuts'
    elif player_has__exclusive_flush:
        player_hand_quality = 'flush'
    elif player_has_straight:
        player_hand_quality = 'straight'
    elif player_has_exclusive_trips:
        player_hand_quality = 'trips'
    elif player_has_exclusive_two_pair:
        player_hand_quality = 'two_pair'
    elif player_has_higher_pocket_pair:
        player_hand_quality = 'higher_pocket_pair'
    elif player_has_highest_board_pair:
        player_hand_quality = 'highest_board_pair'
    elif player_has_second_highest_board_pair:
        player_hand_quality = 'second_highboard_pair'
    elif player_has_pair:
        player_hand_quality = 'lowpair'
    elif hand_value % 41 == 0:
        player_hand_quality = 'acecard'
    elif hand_value % 37 == 0 or hand_value % 31 == 0 or hand_value % 29 == 0:
        player_hand_quality = 'highcard'
    else:
        player_hand_quality = 'lowcard'

    if phase == 'flop' or phase == 'turn':
        player_potential = '_flushdraw' if player_has_exclusive_flush_draw else '' + '_straightdraw2outs' if player_has_exclusive_2outs_straight else '_straightdraw1out' if player_has_exclusive_1out_straight else ''
    else:
        player_potential = ''

    return (first_card + '-' + straightness + '-' + flushness + '-' + repetitiveness), (player_hand_quality + player_potential)


# card1 = Card2.new('Qs')
# card2 = Card2.new('5s')
# card3 = Card2.new('Js')
# card4 = Card2.new('3s')
# card5 = Card2.new('As')

# card6 = Card2.new('2s')
# card7 = Card2.new('4s')

# board = [card1, card2, card3, card4, card5]
# hand = [card6, card7]

# print(get_turn_board_abstraction(board, hand))
# print(get_turn_board_abstraction(board, hand))
a = {}
deck = Deck()
# for combination in list(set(combinations(deck.draw(10), 7))):
for i in range(10):
    deck = Deck()
    combination = deck.draw(7)
    board = combination[:5]
    hand = combination[5:]
    result = get_turn_board_abstraction(board, hand)
    a[result] = True
    print(Card2.print_pretty_cards(board))
    print(Card2.print_pretty_cards(hand))
    print(get_turn_board_abstraction(board, hand))
    print("------------------")

print(len(a.values()))
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
    