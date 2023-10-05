from cfr import CFR

class Node:
    """
    A class representing a node in a game tree.

    Attributes:
    - infoset: a string representing the information set of the node
    - probability: a float representing the probability of reaching the node
    - parent_node: a Node object representing the parent node of the current node
    - children_nodes: a list of Node objects representing the children nodes of the current node
    """

    def __init__(self, infoset, probability):
        self._infoset = infoset
        self._probability = probability
        self._parent_node = None
        self._children_nodes = []

    def set_parent(self, parent_node):
        self._parent_node = parent_node

    def add_child(self, child_node):
        self._children_nodes.append(child_node)

    def infoset(self):
        return str(self._infoset)

    def probability(self):
        return self._probability

    def parent(self):
        return self._parent_node

    def children(self):
        return self._children_nodes

    def is_terminal(self):
        return len(self._children_nodes) == 0

    def payoff(self):
        """
        Returns the payoff of the node.

        Returns:
        - a list of three integers representing the payoff for player 1, player 2, and chance player, respectively
        """
        if self.infoset() == '0':
            return [0, 0, 0]
        elif self.infoset() == '1':
            return [1, 1, 1]
        else:
            p1_action = int(self.infoset()[1])
            p2_action = int(self.parent().infoset()[1])
            if p1_action == p2_action:
                return [0, 0, 0]
            elif (p1_action - p2_action) % 3 == 1:
                return [1, -1, 0]
            else:
                return [-1, 1, 0]

class RPS:
    def __init__(self):
        self.num_actions = 3
        self.root = Node(0, 1)

    def root_node(self):
        return self.root

    def chance_node(self):
        return Node(1, 1/3)

    def action_nodes(self, infoset):
        return [Node(infoset + str(i), 1/self.num_actions) for i in range(self.num_actions)]

    def payoff(self, node):
        if node.infoset() == '0':
            return [0, 0, 0]
        elif node.infoset() == '1':
            return [1, 1, 1]
        else:
            p1_action = int(node.infoset()[1])
            p2_action = int(node.parent().infoset()[1])

# create a CFR instance with the RPS game
game = RPS()

cfr = CFR(game)

# train the CFR algorithm for 1000 iterations
cfr.train(1000)

# get the strategy profile for the root node
root_node = cfr.game.root_node()
strategy = cfr.get_strategy(root_node)

# print the strategy profile
print(strategy)