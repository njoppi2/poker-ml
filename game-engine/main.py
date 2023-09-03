from card import Deck, Card
from game import Game
from phase import Phase
from itertools import cycle
import random

def show_table_cards(cards):
    print("Table cards: ", cards)

# Define your game simulation function
def simulate_poker_game():
    game = Game(num_ai_players=4, num_human_players=0, starting_chips=1000, increase_blind_every=10)

    # This will iterate each time a round ends, and the dealer chip is passed clockwise, until there is only one player left
    while True:
        # for current_dealer in game.dealer_order:
        current_dealer = game.current_dealer
        dealer_id = current_dealer.id

        # if table.num_non_broke_players > 1

        # If the dealer is broke, skip them
        if current_dealer.is_broke():
            continue

        # num_non_broke_players = NUM_STARTING_PLAYERS # wrong
        # current_non_broke_players = [player for player in table["players"] if player.get("chips", 0) < 0]
        small_blind, big_blind = game.get_blinds()
        deck = Deck()
        game.give_players_cards(deck)

        for current_phase in ["preflop", "flop", "turn", "river"]:
            phase = Phase(game, current_phase)

            while True:
                current_player = phase.current_player

                current_player.play()
                break
                

        game.finish_round()

        if game.check_win():
            print("Game over. Winner found!")
            break
        
                
# Run the poker game simulation
if __name__ == "__main__":
    simulate_poker_game()
