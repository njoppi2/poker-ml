import random
import collections
from enum import Enum

class Actions(Enum):
    PASS = 0
    BET = 1

NUM_ACTIONS = len(Actions)

class KuhnTrainer:

    def __init__(self):
        self.nodeMap = {}
    
    class Node:
        def __init__(self):
            self.infoSet = ""
            self.regretSum = [0.0] * NUM_ACTIONS
            self.strategy = [0.0] * NUM_ACTIONS
            self.strategySum = [0.0] * NUM_ACTIONS

        def getStrategy(self, realizationWeight):
            normalizingSum = sum(max(regret, 0) for regret in self.regretSum)
            for action in Actions:
                if normalizingSum > 0:
                    self.strategy[action.value] = max(self.regretSum[action.value], 0) / normalizingSum
                else:
                    self.strategy[action.value] = 1.0 / NUM_ACTIONS
                self.strategySum[action.value] += realizationWeight * self.strategy[action.value]
            return self.strategy

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
        cards = [1, 2, 3]
        util = 0
        for i in range(iterations):
            random.shuffle(cards)
            util += self.cfr(cards, "", 1, 1)
        
        print(f"Average game value: {util / iterations}")
        for n in self.nodeMap.values():
            print(n)

    def cfr(self, cards, history, p0, p1):
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

        strategy = node.getStrategy(p0 if player == 0 else p1)      #pega a estratégia do nodo. ******************entender melhor******************
        util = [0.0] * NUM_ACTIONS
        nodeUtil = 0

        for action in Actions:                                      #itera entre todas as acoes possiveis, calculando a utilidade esperada. Possivelmente eh aqui que implemente o MCCFR
            nextHistory = history + ('p' if action == Actions.PASS else 'b')
            if player == 0:
                util[action.value] = -self.cfr(cards, nextHistory, p0 * strategy[action.value], p1) #aqui implementa a recursao, percorrendo os nodos e calculando a utilidade esperada
            else:
                util[action.value] = -self.cfr(cards, nextHistory, p0, p1 * strategy[action.value])
            nodeUtil += strategy[action.value] * util[action.value]

        for action in Actions:
            regret = util[action.value] - nodeUtil
            node.regretSum[action.value] += (p1 if player == 0 else p0) * regret

        return nodeUtil

if __name__ == "__main__":
    iterations = 100000
    trainer = KuhnTrainer()
    trainer.train(iterations)
