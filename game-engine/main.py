from card import Deck, Card
from game import Game
from itertools import cycle
import random

def show_table_cards(cards):
    print("Table cards: ", cards)

# Define your game simulation function
def simulate_poker_game():
    game = Game(num_ai_players=4, num_human_players=0, initial_chips=1000, increase_blind_every=10)

    # This will iterate each time a round ends, and the dealer chip is passed clockwise, until there is only one player left
    while not game.check_win():
        small_blind, big_blind = game.get_blinds()
        deck = Deck()
        game.give_players_cards(deck)

        for current_phase in ["preflop", "flop", "turn", "river"]:
            game.start_phase(current_phase)

            while True:
                current_player = game.get_current_turn_player()

                current_player.play()
                break
                
        game.finish_round(False)

    print("Game over. Winner found!")
        
                
# Run the poker game simulation
if __name__ == "__main__":
    simulate_poker_game()
