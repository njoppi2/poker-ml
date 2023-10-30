import random
from mod_leduc import ModLeducTrainer
from functions import Card
from enum import Enum

random.seed(42)

iterations = 2000
algorithm = 'mccfr'
cards = [Card.Q, Card.Q, Card.K, Card.K, Card.A, Card.A]
exploring_phase = 0
exploration_type = "cfr"

""" Be careful when creating a model by playing against fixed strategies, because your model might not have all info_sets """
fixed_strategyA = None
fixed_strategyB = None
# fixed_strategyA = 'Cyz-cfr-6cards-2maxbet-EPcfr0-mRW0_0001-iter10000'
# fixed_strategyB = 'pbD-Cyz-mccfr-6cards-2maxbet-EPcfr0-mRW0_0001-iter100000'
max_bet = 2

total_action_symbol = ['p', 'b', 'B', '3', '4', '5', '6', '7', '8', '9']
min_reality_weight = 0.0001
decrese_weight_of_initial_strategies = False

trainer = ModLeducTrainer(iterations, algorithm, cards, exploring_phase, exploration_type, total_action_symbol, min_reality_weight, decrese_weight_of_initial_strategies, max_bet, fixed_strategyA, fixed_strategyB)
