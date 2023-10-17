import random
import collections
import logging
from enum import Enum

class Actions(Enum):
    PASS = 0
    BET = 1

NUM_ACTIONS = len(Actions)

class KuhnTrainer:

    def __init__(self):
        self.nodeMap = {}
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
            self.infoSet = ""
            self.regretSum = [0.0] * NUM_ACTIONS
            self.strategy = [0.0] * NUM_ACTIONS
            self.strategySum = [0.0] * NUM_ACTIONS

        def getStrategy(self, realizationWeight):
            """Turn sum of regrets into a probability distribution for actions."""
            normalizingSum = sum(max(regret, 0) for regret in self.regretSum)
            for action in Actions:
                if normalizingSum > 0:
                    self.strategy[action.value] = max(self.regretSum[action.value], 0) / normalizingSum
                else:
                    self.strategy[action.value] = 1.0 / NUM_ACTIONS
                self.strategySum[action.value] += realizationWeight * self.strategy[action.value]
            return self.strategy

        def get_action(self, strategy):
            """Returns an action based on the strategy."""
            r = random.random()
            cumulative_probability = 0
            
            for action in Actions:
                cumulative_probability += strategy[action.value]
                if r < cumulative_probability:
                    return action.value
            
            raise Exception("No action taken for r: " + str(r) + " and cumulativeProbability: " + str(cumulative_probability) + " and strategy: " + str(strategy))

        def getAverageStrategy(self):
            avgStrategy = [0.0] * NUM_ACTIONS
            normalizingSum = sum(self.strategySum)
            for action in Actions:
                if normalizingSum > 0:
                    avgStrategy[action.value] = self.strategySum[action.value] / normalizingSum
                else:
                    avgStrategy[action.value] = 1.0 / NUM_ACTIONS
            return avgStrategy

        def __str__(self):
            return f"{self.infoSet}: {self.getAverageStrategy()}"

    def train(self, iterations):
        cards = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        util = 0
        for i in range(iterations):
            random.shuffle(cards)
            util += self.cfr(cards, "", 1, 1)
            
            dict = ""
            for n in self.nodeMap.values():
                dict += str(n) + "\n"
            sample_iteration = {
                'index': i,
                'avg_game_value': util / (i + 1),
                'result_dict': dict  # Assuming self.nodeMap contains the result dictionary
            }
            self.logger.info('', extra=sample_iteration)
            
        print(f"Average game value: {util / iterations}")
        for n in self.nodeMap.values():
            print(n)

    def mccfr(self, cards, history, p0, p1):
        plays = len(history)
        player = plays % 2
        opponent = 1 - player

        if plays > 1:
            terminalPass = history[-1] == 'p'
            doubleBet = history[-2:] == 'bb'
            isPlayerCardHigher = cards[player] > cards[opponent]

            if terminalPass:
                if history == "pp":
                    return 1 if isPlayerCardHigher else -1          #determina a recompensa
                else:
                    return 1
            elif doubleBet:
                return 2 if isPlayerCardHigher else -2              #determina a recompensa

        infoSet = str(cards[player]) + history                      #determina o infoset olhando a carta do jogador atual e o histórico
        node = self.nodeMap.get(infoSet)                            #tenta pegar o nodo do infoset correspondente

        if node is None:                                            #se não existir, cria um novo nodo
            node = self.Node()
            node.infoSet = infoSet
            self.nodeMap[infoSet] = node
            #print(infoSet)

        strategy = node.getStrategy(p0 if player == 0 else p1)      #pega a estratégia do nodo, que é um vetor de probabilidades para cada ação.
        util = [0.0] * NUM_ACTIONS
        nodeUtil = 0

        for action in Actions:
            nextHistory = history + ('p' if action == Actions.PASS else 'b')
            if player == 0:
                util[action.value] = -self.mccfr(cards, nextHistory, p0 * strategy[action.value], p1) #aqui implementa a recursao, percorrendo os nodos e calculando a utilidade esperada
            else:
                util[action.value] = -self.mccfr(cards, nextHistory, p0, p1 * strategy[action.value])
            nodeUtil += strategy[action.value] * util[action.value]

        for action in Actions:
            regret = util[action.value] - nodeUtil
            node.regretSum[action.value] += (p1 if player == 0 else p0) * regret

        return nodeUtil

if __name__ == "__main__":
    iterations = 10000
    trainer = KuhnTrainer()
    trainer.log('../analysis/logs/mccfr.log')
    trainer.train(iterations)
