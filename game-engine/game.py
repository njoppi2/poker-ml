from player import Player
from card import Deck
import random
from blind_structure import BlindStructure
from functions import reorder_list
from typing import List, Literal, Tuple

class Game:
    def __init__(self, num_ai_players: int, num_human_players: int, starting_chips: int, increase_blind_every: int):
        self._round = 0
        self.starting_players: Tuple[Player] = self._set_starting_players(num_ai_players, num_human_players, starting_chips)
        self.non_broke_players: Tuple[Player] = self.get_non_broke_players()
        self.current_dealer_order: Tuple[Player] = self._set_starting_dealer_order()
        self.current_dealer: int = self.current_dealer_order[self._round]
        self.current_phase_player_order: Tuple[Player] = ()
        self._blind_structure = BlindStructure()
        self._increase_blind_every = increase_blind_every
        self.phase_name = None
        self.player_order = None
        self.table_cards_to_show_count = None
        self.current_player = None


    def _set_starting_players(self, num_ai_players: int, num_human_players: int, starting_chips: int) -> Tuple[Player]:
        players = [Player(i, f"AI {i}", starting_chips) for i in range(num_ai_players)]
        players += [Player(num_ai_players + i, f"Player {num_ai_players + i}", starting_chips, is_human=True) for i in range(num_human_players)]
        return tuple(players)

    def order_players_by_id(self, players: Tuple[Player], id: int):
        final_id = id % len(players)
        return reorder_list(players, lambda player: player.id == final_id)

    def _set_starting_dealer_order(self) -> Tuple[Player]:
        randomly_determined_starting_dealer = random.randint(0, len(self.non_broke_players) -1)
        dealer_order = self.order_players_by_id(self.get_non_broke_players(), randomly_determined_starting_dealer)

        return tuple(dealer_order)

    def get_blinds(self):
        return self._blind_structure.get_blinds()

    def give_players_cards(self, deck: Deck):
        for player in self.starting_players:
            if player.is_broke():
                continue
            player.cards = deck.get_cards(2)
            print(player)

    def get_non_broke_players(self):
        return [player for player in self.starting_players if player.is_not_broke()]

    def get_non_broke_player_by_id(self, id):
        non_broke_players = self.get_non_broke_players()
        final_id = id % len(non_broke_players)

        # The final result should have all starting players
        ordered_players = self.order_players_by_id(self.starting_players, final_id)

        for starting_player in ordered_players:
            if starting_player in non_broke_players:
                return starting_player

    def set_current_phase_player_order(self, starting_player_id: int):
        non_broke_players = self.get_non_broke_players()
        final_id = starting_player_id % len(non_broke_players)
        self.current_phase_player_order = self.order_players_by_id(non_broke_players, final_id)

    def check_win(self) -> bool:
        return len(self.get_non_broke_players()) == 1
    
    def set_dealer(self, next_dealer: Player):
        self.current_dealer = next_dealer
    
    def finish_round(self):
        print(f"Round {self._round} is over. The dealer is now {self.current_dealer.name}.")
        self._round += 1

        if (self._round + 1) % self._increase_blind_every == 0:
            self._blind_structure.increase_blind()

        # Check if someone broke in this round
        current_non_broke_players = self.get_non_broke_players()
        if len(self.non_broke_players) != len(current_non_broke_players):
            self.non_broke_players = current_non_broke_players
            
            next_dealer = self.get_non_broke_player_by_id(self.current_dealer.id + 1)
            self.set_dealer(next_dealer)

            self.current_dealer_order = self.order_players_by_id(current_non_broke_players, next_dealer.id)
        # If no one broke this round
        else:
            num_non_broke_players = len(self.non_broke_players)
            next_dealer = self.current_dealer_order[self._round % num_non_broke_players]
            self.set_dealer(next_dealer)

        if self._round > 5:
            raise Exception("Game is taking too long. Ending simulation.")
        


    def start_phase(self, phase_name: Literal["preflop", "flop", "turn", "river"]):
        self.phase_name = phase_name
        player_order, table_cards_to_show_count = self.set_phase_variables()
        self.player_order = player_order
        self.table_cards_to_show_count = table_cards_to_show_count
        self.current_player = self.player_order[0]

    def set_phase_variables(self):
        first_player_id = None
        table_cards_to_show_count = None
        non_broke_players = self.get_non_broke_players()
        dealer_id = self.current_dealer.id

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
        player_order = self.order_players_by_id(non_broke_players, final_id)
        table_cards_to_show_count = table_cards_to_show_count
        return (player_order, table_cards_to_show_count)
    
    def next_player(self):
        current_player_id = self.current_player.id

        for _, i in enumerate(self.player_order):
            next_player = self.get_non_broke_player_by_id(current_player_id + 1 + i)
            if next_player.folded or next_player.all_in:
                continue
            else:
                self.current_player = next_player
                return


