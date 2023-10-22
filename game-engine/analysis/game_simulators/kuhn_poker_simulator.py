import random
from enum import Enum

#random.seed(42)

class Actions(Enum):
    PASS = 0
    BET = 1

NUM_ACTIONS = len(Actions)

def get_action(infoset, strategy):
    """Returns an action based on the strategy."""
    r = random.random()
    cumulative_probability = 0
    
    for action in Actions:
        cumulative_probability += strategy.get(infoset, [])[action.value]
        if r < cumulative_probability:
            #print(r, cumulative_probability, action.value)
            return 'p' if action.value == 0  else 'b'

def kuhn_poker_simulator(p1_strategy, p2_strategy):
    deck = [1, 2, 3]
    action_history = ""

    random.shuffle(deck)
    #print(deck)
    player1_card = deck[0]
    player2_card = deck[1]
    #print(player1_card, player2_card)

    while True:
        plays = len(action_history)

        if plays > 1:
            terminal_pass = action_history[-1] == 'p'
            double_bet = action_history[-2:] == 'bb'

            is_p1_card_higher = player1_card > player2_card

            if terminal_pass:
                #print(player1_card, player2_card)
                #print(action_history)
                if action_history == "pp":
                    return 1 if is_p1_card_higher else -1
                else:
                    return 1
            elif double_bet:
                #print(player1_card, player2_card)
                #print(action_history)
                return 2 if is_p1_card_higher else -2
            
        if (plays % 2 == 0):
            action_history += get_action(str(player1_card)+action_history, p1_strategy)
        else:
            action_history += get_action(str(player2_card)+action_history, p2_strategy)
        #print(action_history)


if __name__ == "__main__":
    iterations = 1000000
    p1_strategy = { "2": [0.999767547617347, 0.0002324523826530058],
                    "1p": [0.6581017469872316, 0.3418982530127684],
                    "2pb": [0.40102201937504384, 0.5989779806249561],
                    "1b": [0.9999850218680726, 1.4978131927386016e-05],
                    "3": [0.20169279427548814, 0.7983072057245119],
                    "3pb": [3.714551927590757e-05, 0.9999628544807241],
                    "1": [0.7367179530571595, 0.26328204694284063],
                    "2p": [0.9998602113940337, 0.0001397886059663086],
                    "1pb": [0.9999898190006018, 1.0180999398246848e-05],
                    "2b": [0.6610484683077579, 0.3389515316922421],
                    "3p": [6.0246407807934454e-05, 0.9999397535921921],
                    "3b": [1.5061601951983614e-05, 0.999984938398048]}
    
    p2_strategy = { "1": [0.6666666, 0.3333334],
                    "1p": [0.6666666, 0.3333334],
                    "1pb": [1, 0],
                    "1b": [1, 0],
                    "2": [1, 0],
                    "2p": [1, 0],
                    "2pb": [0.6666666, 0.3333334],
                    "2b": [0.6666666, 0.3333334],
                    "3": [1, 0],
                    "3p": [1, 0],
                    "3pb": [1, 0],
                    "3b": [1, 0]}

    random_strategy = { "1": [0.5, 0.5],
                        "1p": [0.5, 0.5],
                        "1pb": [0.5, 0.5],
                        "1b": [0.5, 0.5],
                        "2": [0.5, 0.5],
                        "2p": [0.5, 0.5],
                        "2pb": [0.5, 0.5],
                        "2b": [0.5, 0.5],
                        "3": [0.5, 0.5],
                        "3p": [0.5, 0.5],
                        "3pb": [0.5, 0.5],
                        "3b": [0.5, 0.5]}
    
    bad_strategy = {  "1": [0, 1],
                        "1p": [0, 1],
                        "1pb": [0, 1],
                        "1b": [0, 1],
                        "2": [0, 1],
                        "2p": [0, 1],
                        "2pb": [1, 0],
                        "2b": [1, 0],
                        "3": [1, 0],
                        "3p": [1, 0],
                        "3pb": [1, 0],
                        "3b": [1, 0]}
    
    p1_avg_game_value = 0
    for i in range(iterations):
        reward = kuhn_poker_simulator(bad_strategy, bad_strategy)
        p1_avg_game_value += reward
        #print("p1_avg_game_value:"+str(p1_avg_game_value))
        #print("reward:"+str(reward))
        #print("Iteration", i, "done.\n")

    p1_avg_game_value /= iterations
    print("Resulting average game value for player 1:", p1_avg_game_value)
    print("Resulting average game value for player 2:", -p1_avg_game_value)
