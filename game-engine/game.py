from player import Player, Players
from card import Deck
from common_types import PlayerGroups
import random
from blind_structure import BlindStructure
from functions import reorder_list
from typing import List, Literal, Tuple

class Game:
    def __init__(self, num_ai_players: int, num_human_players: int, initial_chips: int, increase_blind_every: int):
        self.players = Players(num_ai_players, num_human_players, initial_chips)
        self._blind_structure = BlindStructure()
        self._increase_blind_every = increase_blind_every
        self.phase_name = None
        self.table_cards_to_show_count = None
        self._round = 0
        self._round_since_last_broke = self._round
        # delete non_broke_players variable, create a function instead


    def get_blinds(self):
        return self._blind_structure.get_blinds()

    def give_players_cards(self, deck: Deck):
        self.players.give_players_cards(deck)

    def check_win(self) -> bool:
        return len(self.get_players("non_broke")) == 1
        
    def get_players(self, group: PlayerGroups):
        return self.players.get_players(group)

    def finish_round(self, someone_broke: bool):
        print(f"Round {self._round} is over. The dealer is now {self.get_current_dealer().name}.")
        self._round += 1

        if (self._round + 1) % self._increase_blind_every == 0:
            self._blind_structure.increase_blind()
        
        self.pass_dealer_chip()

        if self._round > 5:
            raise Exception("Game is taking too long. Ending simulation.")
    


    def start_phase(self, phase_name: Literal["preflop", "flop", "turn", "river"]):
        self.phase_name = phase_name
        first_player, table_cards_to_show_count = self.set_phase_variables()
        self.table_cards_to_show_count = table_cards_to_show_count
        self.initiate_players_for_phase(first_player)

    def get_current_dealer(self):
        return self.players.current_dealer
    
    def get_current_turn_player(self):
        return self.players.current_turn_player
    
    def initiate_players_for_phase(self, first_player: Player):
        self.players.initiate_players_for_phase(first_player)
    
    def set_phase_variables(self):
        first_player_id = None
        table_cards_to_show_count = None
        non_broke_players = self.get_players("non_broke")
        dealer_id = self.get_current_dealer().id

        if self.phase_name == "preflop":
            table_cards_to_show_count = 0
            straddler_id = None

            # If at least 1 player straddled
            if straddler_id is not None:
                # The initial player will be the player after the straddler
                first_player_id = straddler_id + 1

            else:
                # The initial player will be the player after the big blind
                first_player_id = dealer_id + 3

        elif self.phase_name == "flop":
            table_cards_to_show_count = 3
            # The default initial player will be the player after the dealer (small blind)
            first_player_id = dealer_id + 1

        elif self.phase_name == "turn":
            table_cards_to_show_count = 1
            # The default initial player will be the player after the dealer (small blind)
            first_player_id = dealer_id + 1

        elif self.phase_name == "river":
            table_cards_to_show_count = 1
            # The default initial player will be the player after the dealer (small blind)
            first_player_id = dealer_id + 1

        # player_order = self.players.order_players_by_id(non_broke_players, first_player_id)
        first_phase_player = self.get_closest_group_player("non_broke", first_player_id)
        table_cards_to_show_count = table_cards_to_show_count
        return (first_phase_player, table_cards_to_show_count)
    
    def get_next(self, group: PlayerGroups, id: int):
        next_player = self.get_closest_group_player(group, id + 1)
        return next_player
    
    def get_closest_group_player(self, group: PlayerGroups, id: int):
        return self.players.get_closest_group_player(group, id)
    
    def pass_dealer_chip(self):
        next_dealer = self.get_next("non_broke", self.get_current_dealer().id)
        self.players.current_dealer = next_dealer

    

