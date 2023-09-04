from player import Player, Players
from card import Deck
from common_types import PlayerGroups, Phases
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
        self.round_num = 0
        # delete non_broke_players variable, create a function instead

    def start_game(self):
        while not self.check_win():
            print(f"\nRound {self.round_num} is starting. The dealer is {self.get_current_dealer().name}.")

            small_blind, big_blind = self.get_blinds()
            round = Round(self, small_blind, big_blind)
            round.start()
            self.finish_round(someone_broke=False)

        print("Game over. Winner found!")
    
    def get_blinds(self):
        return self._blind_structure.get_blinds()

    def check_win(self) -> bool:
        return len(self.players.get_players("non_broke")) == 1
        
    def finish_round(self, someone_broke: bool):
        self.round_num += 1

        if (self.round_num + 1) % self._increase_blind_every == 0:
            self._blind_structure.increase_blind()
        
        self.pass_dealer_chip()

        if self.round_num >= 3:
            raise Exception("Game is taking too long. Ending simulation.")

    def get_current_dealer(self):
        return self.players.current_dealer
                
    def pass_dealer_chip(self):
        next_dealer = self.players.get_next("non_broke", self.get_current_dealer().id)
        self.players.current_dealer = next_dealer


class Round:
    """
    A round is a series of phases, starting with the preflop phase, and ending with the river phase.
    For each round there's a fixed dealer, players have fixed cards, the blinds are fixed, and a final result, like a win or a draw.
    """
    def __init__(self, game: Game, small_blind: int, big_blind: int):
        self.game = game
        self.players = game.players
        self.small_blind = small_blind
        self.big_blind = big_blind

    def start(self):
        deck = Deck()
        self.give_players_cards(deck)
        for current_phase in Phases:
            phase = Phase(self, current_phase, self.small_blind, self.big_blind)
            phase.start()

    def give_players_cards(self, deck: Deck):
        self.players.give_players_cards(deck)


class Phase:
    """
    There are 4 phases in a round: preflop, flop, turn, river.
    """
    def __init__(self, round: Round, phase_name: Phases, small_blind: int, big_blind: int):
        self.round: Round = round
        self.players: Players = round.players
        self.phase_name = phase_name
        self.small_blind = small_blind
        self.big_blind = big_blind

    def start(self):
        first_player, table_cards_to_show_count = self.set_phase_variables()
        self.table_cards_to_show_count = table_cards_to_show_count
        self.players.initiate_players_for_phase(first_player)

        if self.phase_name == Phases.PRE_FLOP:
            small_blind_player = self.players.get_closest_group_player("non_broke", self.players.current_dealer.id + 1)
            big_blind_player = self.players.get_closest_group_player("non_broke", self.players.current_dealer.id + 2)

            small_blind_player.bet(self.small_blind)
            big_blind_player.bet(self.big_blind)

        while len(self.players.get_players("can_win_round")) > 1:
            current_player = self.get_current_turn_player()
            turn = Turn(self, current_player)
            turn.start()

            if self.finish_phase():
                break

            self.set_current_turn_player(self.players.get_next("can_bet_in_current_turn", current_player.id))

    def get_current_turn_player(self):
        return self.players.current_turn_player
    
    def set_current_turn_player(self, player: Player):
        self.players.current_turn_player = player

    def set_phase_variables(self):
        first_player_id = None
        table_cards_to_show_count = None
        non_broke_players = self.players.get_players("non_broke")
        dealer_id = self.players.current_dealer.id

        if self.phase_name == Phases.PRE_FLOP:
            table_cards_to_show_count = 0
            straddler_id = None

            # If at least 1 player straddled
            if straddler_id is not None:
                # The initial player will be the player after the straddler
                first_player_id = straddler_id + 1

            else:
                # The initial player will be the player after the big blind
                first_player_id = dealer_id + 3

        elif self.phase_name == Phases.FLOP:
            table_cards_to_show_count = 3
            # The default initial player will be the player after the dealer (small blind)
            first_player_id = dealer_id + 1

        elif self.phase_name == Phases.TURN:
            table_cards_to_show_count = 1
            # The default initial player will be the player after the dealer (small blind)
            first_player_id = dealer_id + 1

        elif self.phase_name == Phases.RIVER:
            table_cards_to_show_count = 1
            # The default initial player will be the player after the dealer (small blind)
            first_player_id = dealer_id + 1

        # player_order = self.players.order_players_by_id(non_broke_players, first_player_id)
        first_phase_player = self.players.get_closest_group_player("non_broke", first_player_id)
        table_cards_to_show_count = table_cards_to_show_count
        return (first_phase_player, table_cards_to_show_count)

    def finish_phase(self):
        # Implement logic to determine if the phase is complete
        pass


class Turn:
    """
    In a turn a fixed player takes an action, that can be a bet, a call, a raise, a check, a fold, or an all-in.
    """
    def __init__(self, phase: Phase, player: Player):
        self.phase = phase
        self.player = player

    def start(self):
        self.player.play()

        # Implement logic for handling player actions within the turn

        self.finish()

    def finish(self):
        # Implement logic to finish the turn
        pass