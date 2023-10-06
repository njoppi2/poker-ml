import random
from enum import Enum

class Actions(Enum):
    ROCK = 0
    PAPER = 1
    SCISSORS = 2

class RPSTrainer:
    def __init__(self, oppStrategy):
        # Constants for the actions
        self.NUM_ACTIONS = len(Actions)
        # Initialize arrays for regret, strategy, and strategy sum
        self.regretSum = [0.0] * self.NUM_ACTIONS
        self.strategy = [0.0] * self.NUM_ACTIONS
        self.strategySum = [0.0] * self.NUM_ACTIONS
        self.oppStrategy = self.generateOponentStrategy(oppStrategy)

    def generateOponentStrategy(self, strategy):
        if strategy == "optimal":
            return self.strategy
        elif isinstance(strategy, tuple) and len(strategy) == self.NUM_ACTIONS:
            return strategy


    def getStrategy(self):
        normalizingSum = sum(max(self.regretSum[a], 0) for a in range(self.NUM_ACTIONS))

        for action in Actions:
            if normalizingSum > 0:
                self.strategy[action.value] = max(self.regretSum[action.value], 0) / normalizingSum
            else:
                self.strategy[action.value] = 1.0 / self.NUM_ACTIONS

            self.strategySum[action.value] += self.strategy[action.value]

        return self.strategy


    def getAction(self, strategy):
        """Returns an action based on the strategy."""
        r = random.random()
        cumulativeProbability = 0
        
        for action in Actions:
            cumulativeProbability += strategy[action.value]
            if r < cumulativeProbability:
                return action.value
        
        raise Exception("No action taken for r: " + str(r) + " and cumulativeProbability: " + str(cumulativeProbability) + " and strategy: " + str(strategy))


    def train(self, iterations):
        actionUtility = [0.0] * self.NUM_ACTIONS

        for _ in range(iterations):
            strategy = self.getStrategy()
            myAction = self.getAction(strategy)
            otherAction = self.getAction(self.oppStrategy)

            # Define action utilities for the opponent's actions
            actionUtility[otherAction] = 0
            actionUtility[0 if otherAction == self.NUM_ACTIONS - 1 else otherAction + 1] = 1
            actionUtility[self.NUM_ACTIONS - 1 if otherAction == 0 else otherAction - 1] = -1

            # Update regrets based on action utilities
            for action in Actions:
                self.regretSum[action.value] += actionUtility[action.value] - actionUtility[myAction]


    def getAverageStrategy(self):
        avgStrategy = [0.0] * self.NUM_ACTIONS
        normalizingSum = sum(self.strategySum)

        # Calculate average strategy
        for action in Actions:
            if normalizingSum > 0:
                avgStrategy[action.value] = self.strategySum[action.value] / normalizingSum
            else:
                avgStrategy[action.value] = 1.0 / self.NUM_ACTIONS

        return avgStrategy


if __name__ == "__main__":
    opp_strategy = {
        "fixed": (0.35, 0.325, 0.325),
        "optimal": "optimal"
    }

    trainer = RPSTrainer(opp_strategy["optimal"])
    trainer.train(100000)
    print(trainer.getAverageStrategy())
