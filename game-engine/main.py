from game import Game

def show_table_cards(cards):
    print("Table cards: ", cards)

# Define your game simulation function
def simulate_poker_game():
    game = Game(num_ai_players=4, num_human_players=0, initial_chips=1000, increase_blind_every=10)
    game.start_game()
        
                
# Run the poker game simulation
if __name__ == "__main__":
    simulate_poker_game()
