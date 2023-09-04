from typing import List
from card import Card
from typing import List, Literal, Tuple
from enum import Enum
from functions import reorder_list
from card import Deck
import random
from common_types import PlayerGroups

class PlayerTurnState(Enum):
    NOT_PLAYING = "NOT_PLAYING"
    WAITING_FOR_TURN = "WAITING_FOR_TURN"
    PLAYING_TURN = "PLAYING_TURN"
    FOLDED = "FOLDED"
    ALL_IN = "ALL_IN"

class Player:
    def __init__(self, player_id: int, name: str, chips: int, is_human=False):
        self.id = player_id
        self.name = name
        self.chips = chips
        self.round_start_chips = chips
        self.round_end_chips = chips
        self.cards: List[Card] = []
        self.show_down_hand = {
            "hand": [],
            "descendingSortHand": [],
        }
        self.turn_bet_value: int | None = 0
        self.phase_bet_value: int | None = 0
        self.bet_reconciled = False
        self.folded = False
        self.is_all_in = False
        self.can_raise = True
        self.stack_investment = 0
        self.robot = not is_human
        self.turn_state: PlayerTurnState = PlayerTurnState.NOT_PLAYING
        self.played_current_phase = False

    def is_broke(self):
        return self.chips <= 0

    def is_not_broke(self):
        return self.chips > 0
    
    def get_turn_state(self):
        return self.turn_state
    
    def set_turn_state(self, turn_state: PlayerTurnState):
        self.turn_state = turn_state
    
    def get_bet_from_input(self):
        while True:
            try:
                bet_value = int(input("Enter the amount you want to bet: "))
                if bet_value <= 0:
                    print("Please enter a valid positive bet amount.")
                    continue
                if bet_value > self.chips:
                    print(f"You don't have enough chips. You only have {self.chips} chips.")
                    continue
                return bet_value
            except ValueError:
                print("Invalid input. Please enter a valid integer.")

    def play(self, min_turn_value_to_continue: int):
        assert self.get_turn_state() == PlayerTurnState.WAITING_FOR_TURN
        self.set_turn_state(PlayerTurnState.PLAYING_TURN)
        
        while self.get_turn_state() == PlayerTurnState.PLAYING_TURN:
            action = input(f"{self.name}, it's your turn. Enter your action (check, bet, fold, etc.): ").strip().lower()

            if action == "c":
                turn_bet = 0
                state = PlayerTurnState.WAITING_FOR_TURN
            elif action == "b":
                turn_bet = self.get_bet_from_input()
                if turn_bet == self.chips:
                    state = PlayerTurnState.ALL_IN 
            elif action == "f":
                turn_bet = None
                state = PlayerTurnState.FOLDED
                self.set_turn_state(state)
                self.folded = True
                break
            else:
                print("Invalid action")
                continue

            if turn_bet >= min_turn_value_to_continue or state == PlayerTurnState.ALL_IN:
                self.set_turn_state(PlayerTurnState.WAITING_FOR_TURN)
                all_in = self.make_bet(turn_bet)
                if all_in:
                    self.set_turn_state(PlayerTurnState.ALL_IN)
                self.set_played_current_phase(True)
                break
            else:
                print(f"You need to bet at least {min_turn_value_to_continue} to continue.")
        
        assert self.get_turn_state() != PlayerTurnState.PLAYING_TURN
        return self.get_turn_bet_value()

    def make_bet(self, amount: int) -> bool:
        if amount == 0:
            return False
        elif self.chips <= amount:
            self.all_in()
            return True
        else:
            self.turn_bet_value += amount
            self.phase_bet_value += amount
            self.chips -= amount
            return False

    def pay_blind(self, blind_value: int):
        self.make_bet(blind_value)
        self.set_turn_bet_value(0)

    def set_turn_bet_value(self, amount: int):
        self.turn_bet_value = amount

    def get_turn_bet_value(self):
        return self.turn_bet_value

    def set_phase_bet_value(self, amount: int):
        self.phase_bet_value = amount

    def get_phase_bet_value(self):
        return self.phase_bet_value

    def set_played_current_phase(self, played_current_phase: bool):
        self.played_current_phase = played_current_phase

    def get_played_current_phase(self):
        return self.played_current_phase
    
    def all_in(self):
        self.turn_bet_value += self.chips
        self.phase_bet_value += self.chips
        self.chips = 0
        self.all_in = True

    def __str__(self):
        return f"{self.name} has {self.chips} chips, and has the hand: {', '.join(map(str, self.cards))}"


class Players:
    def __init__(self, num_ai_players: int, num_human_players: int, initial_chips: int):
        self.initial_players: List[Player] = self._set_initial_players(num_ai_players, num_human_players, initial_chips)
        self.current_dealer: Player = self._set_initial_dealer()
        self.current_turn_player: Player = None

    def _set_initial_players(self, num_ai_players: int, num_human_players: int, initial_chips: int) -> List[Player]:
        players = [Player(i, f"AI {i}", initial_chips) for i in range(num_ai_players)]
        players += [Player(num_ai_players + i, f"Player {num_ai_players + i}", initial_chips, is_human=True) for i in range(num_human_players)]
        return list(players)
    
    def _set_initial_dealer(self) -> List[Player]:
        randomly_determined_initial_dealer = random.randint(0, len(self.get_players("non_broke")) -1)
        # dealer_order = self.order_players_by_id(self.get_players("non_broke"), randomly_determined_initial_dealer)
        
        initial_dealer = self.get_players("non_broke")[randomly_determined_initial_dealer]
        return initial_dealer

    def get_players(self, group: PlayerGroups):
        condition = None
        if group == "all":
            condition = lambda player: True
        elif group == "non_broke":
            condition = lambda player: player.is_not_broke()
        elif group == "can_bet_in_current_turn":
            condition = lambda player: player.is_not_broke() and not player.folded and not player.is_all_in
        elif group == "can_win_round":
            condition = lambda player: player.is_not_broke() and not player.folded

        return [player for player in self.initial_players if condition(player)]

    def order_players_by_id(self, players: List[Player], raw_id: int):
        id = raw_id % len(self.get_players("all"))
        return reorder_list(players, lambda player: player.id == id)
        
    def give_players_cards(self, deck: Deck):
        for player in self.initial_players:
            if player.is_broke():
                continue
            player.cards = deck.get_cards(2)
            print(player)

    def get_closest_group_player(self, group: PlayerGroups, raw_id: int):
        id = raw_id % len(self.get_players("all"))

        # The final result should have all initial players
        ordered_players = self.order_players_by_id(self.initial_players, id)
        
        player_found = next((p for p in ordered_players if p in self.get_players(group)), None)
        if player_found is None:
            raise Exception("No player found")
        
        return player_found

    def get_next(self, group: PlayerGroups, id: int):
        next_player = self.get_closest_group_player(group, id + 1)
        return next_player
    
    def get_turn_state(self, player: Player):
        return player.get_turn_state()
    
    def set_turn_state(self, player: Player, turn_state: PlayerTurnState):
        player.set_turn_state(turn_state)
    
    def initiate_players_for_phase(self, first_player: Player):
        self.current_turn_player = first_player
        players = self.get_players("non_broke")

        # Set all players to WAITING_FOR_TURN
        [self.set_turn_state(player, PlayerTurnState.WAITING_FOR_TURN) for player in players]        

        
