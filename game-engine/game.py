from player import Player, PlayerTurnState, Players
from card import Deck, Cards
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
            print("-----------------------------")
            print(f"\nRound {self.round_num} is starting. The dealer is {self.get_current_dealer().name}.\n")

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
        self.total_pot = 0
        self.players_in_the_hand = []
        self.is_showdown = False

    def start(self):
        deck = Deck()
        table_cards = Cards()
        self.give_players_cards(deck)
        for current_phase in Phases:
            print(f"\n{current_phase.value} phase is starting.")
            first_player, table_cards_to_show_count = self.get_phase_variables(current_phase)
            table_cards.extend_cards(deck.get_cards(table_cards_to_show_count))
            print(f"Table cards are:", table_cards, "\n")
            phase = Phase(self, current_phase, self.small_blind, self.big_blind, first_player)
            phase_pot = phase.start()
            self.add_to_pot(phase_pot)
            print("total pot: ", self.total_pot)

                
            # Check if everyone folded but 1 player
            players_in_the_hand = self.players.get_players("active_in_hand")
            if len(players_in_the_hand) == 1:
                self.players_in_the_hand.extend(players_in_the_hand)
                self.is_showdown = False
                break
            elif current_phase == Phases.RIVER:
                print("\nShowdown!")
                
                self.players_in_the_hand.extend(players_in_the_hand)
                self.is_showdown = True
            
        self.finish_round()

    def get_phase_variables(self, phase_name: Phases):
        phase_info = {
            Phases.PRE_FLOP: {"table_cards_count": 0, "offset": 3},
            Phases.FLOP: {"table_cards_count": 3, "offset": 1},
            Phases.TURN: {"table_cards_count": 1, "offset": 1},
            Phases.RIVER: {"table_cards_count": 1, "offset": 1},
        }
        
        phase_data = phase_info.get(phase_name, {"table_cards_count": None, "offset": None})
        
        table_cards_to_show_count = phase_data["table_cards_count"]
        offset = phase_data["offset"]
        
        first_player_id = self.players.current_dealer.id + offset
        
        first_phase_player = self.players.get_closest_group_player("non_broke", first_player_id)
        
        return first_phase_player, table_cards_to_show_count


    def give_players_cards(self, deck: Deck):
        self.players.give_players_cards(deck)

    def reset_round_player(self, player: Player):
        player.set_turn_state(PlayerTurnState.NOT_PLAYING)
        player.all_in = False
        player.folded = False
        player.set_round_bet_value(0)

    def add_to_pot(self, amount: int):
        self.total_pot += amount

    def rank_hands(self):
        pass

    def distribute_pot(self):
        if self.is_showdown:
            self.players_in_the_hand[0].add_chips(self.total_pot)
        else:
            self.players_in_the_hand[0].add_chips(self.total_pot)

    def finish_round(self):
        # Assert that there's at least 1 player in the hand
        assert len(self.players_in_the_hand) >= 1
        # Assert that there are 2 or more players in the hand if there is a showdown
        assert ((len(self.players_in_the_hand) >= 2) == self.is_showdown)
        # Assert that the total pot is equal to the sum of the bets of all players
        assert self.total_pot == sum([player.round_bet_value for player in self.players.get_players("non_broke")])

        self.distribute_pot()
        
        [self.reset_round_player(player) for player in self.players.get_players("non_broke")]
        

class Phase:
    """
    There are 4 phases in a round: preflop, flop, turn, river.
    """
    def __init__(self, round: Round, phase_name: Phases, small_blind: int, big_blind: int, first_player: Player):
        self.round: Round = round
        self.players: Players = round.players
        self.phase_name = phase_name
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.min_phase_bet_to_continue = 0
        self.phase_pot = 0
        self.players.initiate_players_for_phase(first_player)

    def start(self):

        if self.phase_name == Phases.PRE_FLOP:
            small_blind_player = self.players.get_closest_group_player("non_broke", self.players.current_dealer.id + 1)
            big_blind_player = self.players.get_closest_group_player("non_broke", self.players.current_dealer.id + 2)
            small_blind_player.pay_blind(self.small_blind)
            big_blind_player.pay_blind(self.big_blind)

            self.add_to_pot(self.small_blind + self.big_blind)
            self.min_phase_bet_to_continue = self.big_blind

        # Iterate over each phase turn
        while len(self.players.get_players("active_in_hand")) > 1:
            current_player = self.get_current_turn_player()
            min_turn_bet_to_continue = self.min_phase_bet_to_continue - current_player.phase_bet_value
            assert min_turn_bet_to_continue >= 0
            # Check if every player has either folded or bet the minimum to continue
            if current_player.get_played_current_phase() and min_turn_bet_to_continue == 0:
                break
            elif current_player.turn_state != PlayerTurnState.FOLDED and current_player.turn_state != PlayerTurnState.ALL_IN:
                turn = Turn(self, current_player, min_turn_bet_to_continue)

            player_turn_bet = turn.start()

            if current_player.turn_state == PlayerTurnState.FOLDED:
                pass
            else:
                self.add_to_pot(player_turn_bet)
                if self.min_phase_bet_to_continue < current_player.phase_bet_value:
                    self.min_phase_bet_to_continue = current_player.phase_bet_value

            self.set_current_turn_player(self.players.get_next("can_bet_in_current_turn", current_player.id))
        self.finish_phase()
        return self.phase_pot

    def get_current_turn_player(self):
        return self.players.current_turn_player
    
    def set_current_turn_player(self, player: Player):
        self.players.current_turn_player = player

    def reset_phase_player(self, player: Player):
        player.set_played_current_phase(False)
        player.set_phase_bet_value(0)

    def add_to_pot(self, amount: int):
        self.phase_pot += amount

    def finish_phase(self):
        [self.reset_phase_player(player) for player in self.players.get_players("non_broke")]

class Turn:
    """
    In a turn a fixed player takes an action, that can be a bet, a call, a raise, a check, a fold, or an all-in.
    """
    def __init__(self, phase: Phase, player: Player, min_value_to_continue: int):
        self.phase = phase
        self.player = player
        self.min_value_to_continue = min_value_to_continue

    def start(self):
        bet = self.player.play(self.min_value_to_continue)
        if self.player.turn_state != PlayerTurnState.FOLDED:
            self.player.played_current_phase

        self.finish_turn()

        return bet

    def finish_turn(self):
        self.player.set_turn_bet_value(0)