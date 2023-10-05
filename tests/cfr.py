import numpy as np
from collections import defaultdict

class CFR:
    """
    Class that implements the Counterfactual Regret Minimization algorithm for solving
    sequential games with imperfect information. It uses regret matching to compute
    a strategy profile for each player.
    """
    def __init__(self, game):
        """
        Initializes the CFR algorithm with the given game.

        Args:
        - game: an instance of the Game class representing the game to be solved.
        """
        self.game = game
        self.regret_sum = defaultdict(lambda: np.zeros(game.num_actions))
        self.strategy = defaultdict(lambda: np.zeros(game.num_actions))
        self.strategy_sum = defaultdict(lambda: np.zeros(game.num_actions))

    def train(self, num_iterations):
        """
        Trains the CFR algorithm for a given number of iterations.

        Args:
        - num_iterations: an integer representing the number of iterations to run.
        """
        for i in range(num_iterations):
            self.cfr(self.game.root, 1, 1)

    def cfr(self, node, p0, p1):
        """
        Computes the counterfactual regret for each action in the given node.

        Args:
        - node: an instance of the Node class representing the current node in the game tree.
        - p0: a float representing the probability of reaching the current node for player 0.
        - p1: a float representing the probability of reaching the current node for player 1.

        Returns:
        - node_util: a float representing the expected utility of the current node.
        """
        if node.is_terminal():
            return node.payoff()

        if node.is_chance():
            return sum(p * self.cfr(child, p0, p1) for child, p in node.children())

        player = node.player()
        if player == 0:
            strategy = self.strategy[node.infoset()]
            util = np.zeros(self.game.num_actions)
            node_util = 0
            for i, action in enumerate(node.actions()):
                if strategy[i] > 0:
                    next_node = node.child(action)
                    util[i] = -self.cfr(next_node, p0 * strategy[i], p1)
                    node_util += strategy[i] * util[i]
            for i, action in enumerate(node.actions()):
                regret = util[i] - node_util
                self.regret_sum[node.infoset()][i] += p1 * regret
            return node_util

        elif player == 1:
            strategy = self.strategy[node.infoset()]
            util = np.zeros(self.game.num_actions)
            node_util = 0
            for i, action in enumerate(node.actions()):
                if strategy[i] > 0:
                    next_node = node.child(action)
                    util[i] = -self.cfr(next_node, p0, p1 * strategy[i])
                    node_util += strategy[i] * util[i]
            for i, action in enumerate(node.actions()):
                regret = util[i] - node_util
                self.regret_sum[node.infoset()][i] += p0 * regret
            return node_util

    def get_strategy(self, node):
        """
        Computes the strategy profile for the given node.

        Args:
        - node: an instance of the Node class representing the current node in the game tree.

        Returns:
        - a numpy array representing the strategy profile for the current node.
        """
        infoset = node.infoset()
        normalizing_sum = sum(self.strategy_sum[infoset])
        if normalizing_sum > 0:
            return self.strategy[infoset] / normalizing_sum
        else:
            return np.ones(self.game.num_actions) / self.game.num_actions

    def update_strategy(self):
        """
        Updates the strategy profile for each information set based on the accumulated regret.
        """
        for infoset in self.regret_sum:
            regret = self.regret_sum[infoset]
            positive_regret = np.maximum(regret, 0)
            normalizing_sum = sum(positive_regret)
            if normalizing_sum > 0:
                self.strategy[infoset] = positive_regret / normalizing_sum
            else:
                self.strategy[infoset] = np.ones(self.game.num_actions) / self.game.num_actions
            self.strategy_sum[infoset] += self.strategy[infoset]
            self.regret_sum[infoset] = np.zeros(self.game.num_actions)