import random
import collections
import logging
from enum import Enum

random.seed(42)

iterations = 1000

class Actions(Enum):
    PASS = 0
    BET = 1

NUM_ACTIONS = len(Actions)

class KuhnTrainer:

    def __init__(self):
        self.node_map = {}
        self.log_file = None

    def log(self, log_file):
        self.log_file = log_file
        log_format = 'Iteration: %(index)s\nAverage game value: %(avg_game_value)s\n%(result_dict)s\n'
        formatter = logging.Formatter(log_format)

        # Change the file mode to 'w' for overwriting the log file
        file_handler = logging.FileHandler(log_file, mode='w')
        file_handler.setFormatter(formatter)

        self.logger = logging.getLogger('')
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
    
    class Node:
        def __init__(self):
            self.info_set = ""
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
        util = 0
        for i in range(iterations):
            random.shuffle(cards)
            util += self.cfr(cards, "", 1, 1)
            
            dict_str = ""
            for n in self.node_map.values():
                dict_str += str(n) + "\n"
            sample_iteration = {
                'index': i,
                'avg_game_value': util / (i + 1),
                'result_dict': dict_str  # Assuming self.node_map contains the result dictionary
            }
            self.logger.info('', extra=sample_iteration)
            
        print(f"Average game value: {util / iterations}")
        for n in sorted(self.node_map.values()):
            print(n)

    def cfr(self, cards, history, p0, p1):
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
        node = self.node_map.get(info_set)                            #tenta pegar o nodo do infoset correspondente

        if node is None:                                            #se não existir, cria um novo nodo
            node = self.Node()
            node.info_set = info_set
            self.node_map[info_set] = node
            #print(info_set)

        strategy = node.get_strategy(p0 if player == 0 else p1)      #pega a estratégia do nodo. ******************entender melhor******************
        util = [0.0] * NUM_ACTIONS
        node_util = 0

        for action in Actions:                                      #itera entre todas as acoes possiveis, calculando a utilidade esperada. Possivelmente eh aqui que implemente o MCCFR
            next_history = history + ('p' if action == Actions.PASS else 'b')
            if player == 0:
                util[action.value] = -self.cfr(cards, next_history, p0 * strategy[action.value], p1) #aqui implementa a recursao, percorrendo os nodos e calculando a utilidade esperada
            else:
                util[action.value] = -self.cfr(cards, next_history, p0, p1 * strategy[action.value])
            node_util += strategy[action.value] * util[action.value]

        for action in Actions:
            regret = util[action.value] - node_util
            node.regret_sum[action.value] += (p1 if player == 0 else p0) * regret

        return node_util

if __name__ == "__main__":
    trainer = KuhnTrainer()
    trainer.log('../analysis/logs/cfr.log')
    trainer.train(iterations)
