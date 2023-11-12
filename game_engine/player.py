from typing import List
from typing import List, Literal, Tuple
from enum import Enum
from functions import reorder_list
from treys import Card, Deck
import random
import asyncio
from common_types import PlayerGroups, Encoder
import time
import websockets
import json
import re


class PlayerTurnState(Enum):
    NOT_PLAYING = "NOT_PLAYING"
    WAITING_FOR_TURN = "WAITING_FOR_TURN"
    PLAYING_TURN = "PLAYING_TURN"
    FOLDED = "FOLDED"
    ALL_IN = "ALL_IN"

import json

class PlayerEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Players):
            players_data = [PlayerEncoder().default(player) for player in obj.initial_players]
            dealer_data = PlayerEncoder().default(obj.current_dealer)
            everyone_in_all_in = not obj.current_turn_player
            # assert everyone_in_all_in ==  all(player.get_turn_state() == PlayerTurnState.ALL_IN for player in obj.get_players("active_in_hand"))
            current_turn_player_data = PlayerEncoder().default(obj.current_turn_player) if not everyone_in_all_in else "EVERYONE_IN_ALL_IN"

            return {
                "initial_players": players_data,
                "current_dealer": dealer_data,
                "current_turn_player": current_turn_player_data
            }

        if isinstance(obj, Player):
            cards_data = [Card.int_to_str(card) for card in obj.cards]
            turn_state_data = Encoder().default(obj.turn_state)

            return {
                "id": obj.id,
                "name": obj.name,
                "chips": obj.chips,
                "round_start_chips": obj.round_start_chips,
                "round_end_chips": obj.round_end_chips,
                "cards": cards_data,
                "show_down_hand": obj.show_down_hand,
                "turn_bet_value": obj.turn_bet_value,
                "phase_bet_value": obj.phase_bet_value,
                "round_bet_value": obj.round_bet_value,
                "is_robot": obj.is_robot,
                "turn_state": turn_state_data,
                "played_current_phase": obj.played_current_phase,
                "chip_balance": obj.chip_balance,
                "chip_balance_history": obj.chip_balance_history
            }
        return super().default(obj)

class Player:
    def __init__(self, game, player_id: int, name: str, chips: int, is_human=False):
        self.id = player_id
        self.name = name
        self.chips = chips
        self.round_start_chips = chips
        self.round_end_chips = chips
        self.cards: list[Card] = []
        self.show_down_hand = {
            "value": None,
            "hand": [],
            "descendingSortHand": [],
        }
        self.turn_bet_value: int = 0
        self.phase_bet_value: int = 0
        self.round_bet_value: int = 0
        self.round_bet_aux: int = 0
        self.is_robot = not is_human
        self.turn_state: PlayerTurnState = PlayerTurnState.NOT_PLAYING
        self.played_current_phase = False
        self.chip_balance = 0
        self.chip_balance_history = []
        self.game = game

    def reset_round_player(self):
        self.cards = []
        self.turn_bet_value = 0
        self.phase_bet_value = 0
        self.round_bet_value = 0
        self.round_bet_aux = 0
        self.bet_reconciled = False
        
        self.can_raise = True
        self.stack_investment = 0
        self.played_current_phase = False
        self.round_start_chips = self.chips
        self.round_end_chips = self.chips
        self.show_down_hand =  {
            "value": None,
            "hand": [],
            "descendingSortHand": [],
        }

    def is_broke(self):
        assert self.chips >= 0
        return self.chips == 0 and self.turn_state != PlayerTurnState.ALL_IN

    def is_not_broke(self):
        return not self.is_broke()
    
    def get_turn_state(self):
        return self.turn_state
    
    def set_turn_state(self, turn_state: PlayerTurnState):
        self.turn_state = turn_state
    
    def is_valid_bet_format(self, input_string):
        # Define a regular expression pattern to match "Bet {integer}"
        pattern = r'^Bet \d+$'

        # Use re.match to check if the input_string matches the pattern
        if re.match(pattern, input_string):
            return ["Bet", int(input_string.split()[1])]
        else:
            return False
            
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

    async def ai_play(self, min_turn_value_to_continue: int):
        time.sleep(1)  # Pause execution for 2 seconds
        print("min_turn_value_to_continue: ", min_turn_value_to_continue)
        if self.chips < 100:
            await self.make_bet_up_to(100)
        else:
            if min_turn_value_to_continue == 50:
                await self.make_bet_up_to(77)
            elif min_turn_value_to_continue == 200:
                state = PlayerTurnState.FOLDED
                self.set_turn_state(state)
            else:
                # random number from 0 to 1
                random_number = random.random()
                if random_number < 0.8:
                    await self.make_bet_up_to(min_turn_value_to_continue)
                else:
                    await self.make_bet_up_to(min_turn_value_to_continue + 40)
            if self.get_turn_state() == PlayerTurnState.PLAYING_TURN:
                self.set_turn_state(PlayerTurnState.WAITING_FOR_TURN)
        self.set_played_current_phase(True)

    async def play(self, min_turn_value_to_continue: int):
        if self.is_robot:
            await self.ai_play(min_turn_value_to_continue)
        else:
            while self.get_turn_state() == PlayerTurnState.PLAYING_TURN:
                try:
                    action = await self.game.websocket.recv()

                    # action = input(f"{self.name}, it's your turn. Enter your action (check, bet, fold, etc.): ").strip().lower()

                    if action == "Check" or self.is_valid_bet_format(action):
                        if action == "Check":
                            turn_bet = 0
                        else:
                            turn_bet = self.is_valid_bet_format(action)[1]
                        if turn_bet >= min_turn_value_to_continue:
                            if await self.make_bet(turn_bet):
                                if self.get_turn_state() == PlayerTurnState.PLAYING_TURN:
                                    self.set_turn_state(PlayerTurnState.WAITING_FOR_TURN)
                                    break
                        else:
                            print(f"You must bet at least the minimum bet to continue, which is {min_turn_value_to_continue}.")
                    elif action == "Fold":
                        self.set_turn_state(PlayerTurnState.FOLDED)
                        break
                    else:
                        print("Invalid action")
                except websockets.exceptions.ConnectionClosedOK:
                    break
        
        self.set_played_current_phase(True)
        assert self.get_turn_state() != PlayerTurnState.PLAYING_TURN
        return self.get_turn_bet_value()
    
    async def make_bet_up_to(self, amount: int) -> bool:
        if self.chips >= amount:
            return await self.make_bet(amount)
        else:
            return await self.make_bet(self.chips)

    async def make_bet(self, amount: int) -> bool:

        if self.chips >= amount:
            self.calculate_is_all_in(amount)

            self.set_turn_bet_value(self.turn_bet_value + amount)
            self.set_phase_bet_value(self.phase_bet_value + amount)
            self.set_round_bet_value(self.round_bet_value + amount)
            self.remove_chips(amount)
            await self.game.add_to_pot(amount)
            return True
        else:
            print("Something went wrong")
            return False

    def calculate_is_all_in(self, amount):
        if self.chips == amount:
            self.is_all_in = True
            self.set_turn_state(PlayerTurnState.ALL_IN)
            return True
        else:
            return False

    async def pay_blind(self, blind_value: int):
        await self.make_bet(blind_value)
        self.set_turn_bet_value(0)

    def set_turn_bet_value(self, amount: int):
        self.turn_bet_value = amount

    def get_turn_bet_value(self):
        return self.turn_bet_value

    def set_phase_bet_value(self, amount: int):
        self.phase_bet_value = amount

    def get_phase_bet_value(self):
        return self.phase_bet_value

    def set_round_bet_value(self, amount: int):
        self.round_bet_value = amount
        self.round_bet_aux = amount

    def get_round_bet_value(self):
        return self.round_bet_value

    def set_played_current_phase(self, played_current_phase: bool):
        self.played_current_phase = played_current_phase

    def get_played_current_phase(self):
        return self.played_current_phase

    def remove_chips(self, amount: int):
        assert self.chips >= amount
        self.chips -= amount
    
    def add_chips(self, amount: int):
        self.chips += amount

    def set_chips(self, amount: int):
        self.chips = amount

    def add_chip_balance(self, amount: int):
        self.chip_balance += amount
        self.chip_balance_history.append(amount)

    def __str__(self):
        return f"{self.name} has {self.chips} chips, and has the hand: {', '.join(map(str, self.cards))}"


class Players:
    def __init__(self, game, num_ai_players: int, num_human_players: int, initial_chips: int):
        self.initial_players: List[Player] = self._set_initial_players(game, num_ai_players, num_human_players, initial_chips)
        self.current_dealer: Player = self._set_initial_dealer()
        self.current_turn_player: Player = None

    def _set_initial_players(self, game, num_ai_players: int, num_human_players: int, initial_chips: int) -> List[Player]:
        players = [Player(game, i, f"AI {i}", initial_chips) for i in range(num_ai_players)]
        players += [Player(game, num_ai_players + i, f"Player {num_ai_players + i}", initial_chips, is_human=True) for i in range(num_human_players)]
        [print(player.id) for player in players]
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
            condition = lambda player: player.is_not_broke() and player.get_turn_state() != PlayerTurnState.FOLDED and player.get_turn_state() != PlayerTurnState.ALL_IN
        elif group == "active_in_hand":
            condition = lambda player: player.is_not_broke() and player.get_turn_state() != PlayerTurnState.FOLDED
        elif group == "all_in":
            condition = lambda player: player.get_turn_state() == PlayerTurnState.ALL_IN

        return [player for player in self.initial_players if condition(player)]

    def order_players_by_id(self, players: List[Player], raw_id: int):
        id = raw_id % len(self.get_players("all"))
        return reorder_list(players, lambda player: player.id == id)

    def get_closest_group_player(self, group: PlayerGroups, raw_id: int):
        id = raw_id % len(self.get_players("all"))

        # The final result should have all initial players
        ordered_players = self.order_players_by_id(self.initial_players, id)
        
        player_found = next((p for p in ordered_players if p in self.get_players(group)), None)
        if player_found is None:
            print("No player found, everyone is probably on all in or folded.")
        
        return player_found

    def get_next(self, group: PlayerGroups, id: int):
        next_player = self.get_closest_group_player(group, id + 1)
        return next_player
    
    def get_turn_state(self, player: Player):
        return player.get_turn_state()
        
    def initiate_players_for_phase(self, first_player: Player):
        self.current_turn_player = first_player

    def initiate_players_for_round(self):
        all_players = self.get_players("all")
        [player.set_turn_state(PlayerTurnState.NOT_PLAYING) for player in all_players]        
    
        non_broke_players = self.get_players("non_broke")
        [player.set_turn_state(PlayerTurnState.WAITING_FOR_TURN) for player in non_broke_players]        