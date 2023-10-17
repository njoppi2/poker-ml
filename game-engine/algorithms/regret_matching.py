import random
from enum import Enum

class Actions(Enum):
    ROCK = 0
    PAPER = 1
    SCISSORS = 2

NUM_ACTIONS = len(Actions)

class RPSTrainer:
    def __init__(self, opp_strategy):
        # Constants for the actions
        NUM_ACTIONS = len(Actions)
        # Initialize arrays for regret, strategy, and strategy sum
        self.regret_sum = [0.0] * NUM_ACTIONS
        self.strategy = [0.0] * NUM_ACTIONS
        self.strategy_sum = [0.0] * NUM_ACTIONS
        self.opp_strategy = self.generate_oponent_strategy(opp_strategy)

    def generate_oponent_strategy(self, strategy):
        if strategy == "optimal":
            return self.strategy
        elif isinstance(strategy, tuple) and len(strategy) == NUM_ACTIONS:
            return strategy


    def get_strategy(self):
        """Turn sum of regrets into a probability distribution for actions."""
        normalizing_sum = sum(max(self.regret_sum[a], 0) for a in range(NUM_ACTIONS))

        for action in Actions:
            if normalizing_sum > 0:
                self.strategy[action.value] = max(self.regret_sum[action.value], 0) / normalizing_sum
            else:
                self.strategy[action.value] = 1.0 / NUM_ACTIONS

            self.strategy_sum[action.value] += self.strategy[action.value]

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


    def regret_matching(self):
        action_utility = [0.0] * NUM_ACTIONS

        strategy = self.get_strategy()
        my_action = self.get_action(strategy)
        other_action = self.get_action(self.opp_strategy)
        reward = 1
        
        if my_action == Actions.SCISSORS.value or other_action == Actions.SCISSORS.value:
            reward = 2

        # Define action utilities for the opponent's actions
        action_utility[other_action] = 0
        action_utility[(other_action + 1) % NUM_ACTIONS] = reward
        action_utility[(other_action - 1) % NUM_ACTIONS] = -reward

        # Update regrets based on action utilities
        for action in Actions:
            action_regret = action_utility[action.value] - action_utility[my_action]
            self.regret_sum[action.value] += action_regret


    def train(self, iterations):
        for _ in range(iterations):
            self.regret_matching()


    def get_average_strategy(self):
        avg_strategy = [0.0] * NUM_ACTIONS
        normalizing_sum = sum(self.strategy_sum)

        # Calculate average strategy
        for action in Actions:
            if normalizing_sum > 0:
                avg_strategy[action.value] = self.strategy_sum[action.value] / normalizing_sum
            else:
                avg_strategy[action.value] = 1.0 / NUM_ACTIONS

        return avg_strategy


if __name__ == "__main__":
    opp_strategy = {
        "fixed": (0.4, 0.3, 0.3),
        "optimal": "optimal"
    }

    trainer = RPSTrainer(opp_strategy["optimal"])
    trainer.train(100000)
    print(trainer.get_average_strategy())
