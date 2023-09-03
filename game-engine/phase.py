from game import Game
from typing import Literal


class Phase:
    def __init__(self, game: Game, phase_name: Literal["preflop", "flop", "turn", "river"]):
        self.game = game
        self.phase_name = phase_name
        player_order, table_cards_to_show_count = self.define_phase_variables()
        self.player_order = player_order
        self.table_cards_to_show_count = table_cards_to_show_count
        self.current_player = self.player_order[0]

    def define_phase_variables(self):
        first_player_id = None
        table_cards_to_show_count = None
        non_broke_players = self.game.get_non_broke_players()
        dealer_id = self.game.current_dealer.id

        if self.phase_name == "preflop":
            table_cards_to_show_count = 0
            straddler_id = None

            # If at least 1 player straddled
            if straddler_id is not None:
                # The starting player will be the player after the straddler
                first_player_id = straddler_id + 1

            else:
                # The starting player will be the player after the big blind
                first_player_id = dealer_id + 3

        elif self.phase_name == "flop":
            table_cards_to_show_count = 3
            # The default starting player will be the player after the dealer (small blind)
            first_player_id = dealer_id + 1

        elif self.phase_name == "turn":
            table_cards_to_show_count = 1
            # The default starting player will be the player after the dealer (small blind)
            first_player_id = dealer_id + 1

        elif self.phase_name == "river":
            table_cards_to_show_count = 1
            # The default starting player will be the player after the dealer (small blind)
            first_player_id = dealer_id + 1

        final_id = first_player_id % len(non_broke_players)
        player_order = self.game.order_players_by_id(non_broke_players, final_id)
        table_cards_to_show_count = table_cards_to_show_count
        return (player_order, table_cards_to_show_count)
    
    def next_player(self):
        current_player_id = self.current_player.id

        for _, i in enumerate(self.player_order):
            next_player = self.game.get_non_broke_player_by_id(current_player_id + 1 + i)
            if next_player.folded or next_player.all_in:
                continue
            else:
                self.current_player = next_player
                return