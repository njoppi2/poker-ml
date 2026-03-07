from __future__ import annotations

import asyncio
import math
import re
from enum import Enum
from typing import List, Optional

import websockets
from treys import Card

from .common_types import PlayerGroups
from .functions import reorder_list

BET_PATTERN = re.compile(r"^Bet (\d+)$")


class PlayerTurnState(str, Enum):
    NOT_PLAYING = "NOT_PLAYING"
    WAITING_FOR_TURN = "WAITING_FOR_TURN"
    PLAYING_TURN = "PLAYING_TURN"
    FOLDED = "FOLDED"
    ALL_IN = "ALL_IN"


class Player:
    def __init__(self, game, player_id: int, name: str, chips: int, is_human: bool = False):
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
        self.turn_bet_value = 0
        self.phase_bet_value = 0
        self.round_bet_value = 0
        self.round_bet_aux = 0
        self.is_robot = not is_human
        self.turn_state: PlayerTurnState = PlayerTurnState.NOT_PLAYING
        self.played_current_phase = False
        self.chip_balance = 0
        self.chips_won_history: list[int] = []
        self.game = game
        self.is_all_in = False

    def reset_round_player(self) -> None:
        self.cards = []
        self.turn_bet_value = 0
        self.phase_bet_value = 0
        self.round_bet_value = 0
        self.round_bet_aux = 0
        self.played_current_phase = False
        self.round_start_chips = self.chips
        self.round_end_chips = self.chips
        self.is_all_in = False
        self.show_down_hand = {
            "value": None,
            "hand": [],
            "descendingSortHand": [],
        }

    def is_broke(self) -> bool:
        return self.chips == 0 and self.turn_state != PlayerTurnState.ALL_IN

    def is_not_broke(self) -> bool:
        return not self.is_broke()

    def get_turn_state(self) -> PlayerTurnState:
        return self.turn_state

    def set_turn_state(self, turn_state: PlayerTurnState) -> None:
        self.turn_state = turn_state

    def parse_bet_input(self, input_string: str) -> Optional[int]:
        match = BET_PATTERN.match(input_string)
        if match is None:
            return None
        return int(match.group(1))

    async def play_ai_turn(
        self,
        min_turn_value_to_continue: int,
        min_bet: int,
        ai_player_cards: list[str],
        table_cards: list[str],
        history: list[str],
    ) -> str:
        if self.game.policy is None:
            await self.ai_play(min_turn_value_to_continue, min_bet)
            return self.get_action(min_turn_value_to_continue)

        info_set = self.get_info_set(ai_player_cards, table_cards, history)
        action = self.game.policy.decide_next_action(info_set)
        if action == "f":
            self.set_turn_state(PlayerTurnState.FOLDED)
        elif action == "c":
            if await self.make_bet(min_turn_value_to_continue) and self.get_turn_state() == PlayerTurnState.PLAYING_TURN:
                self.set_turn_state(PlayerTurnState.WAITING_FOR_TURN)
        elif action == "k":
            await self.make_bet(0)
            self.set_turn_state(PlayerTurnState.WAITING_FOR_TURN)
        elif action.startswith("r"):
            value = min(int(action[1:]) - min_turn_value_to_continue, self.chips)
            if await self.make_bet(value) and self.get_turn_state() == PlayerTurnState.PLAYING_TURN:
                self.set_turn_state(PlayerTurnState.WAITING_FOR_TURN)
        else:
            raise ValueError(f"Invalid action from policy: {action}")

        return self.get_action(min_turn_value_to_continue)

    async def ai_play(self, min_turn_value_to_continue: int, min_bet: int) -> None:
        await asyncio.sleep(0.3)
        if self.chips < 100:
            await self.make_bet_up_to(100)
        elif min_turn_value_to_continue == min_bet:
            if self.game.rng.random() < 0.7:
                await self.make_bet_up_to(min_bet)
            else:
                await self.make_bet_up_to(2 * min_bet)
        elif min_turn_value_to_continue == 200:
            self.set_turn_state(PlayerTurnState.FOLDED)
        else:
            if self.game.rng.random() < 0.6:
                await self.make_bet_up_to(min_turn_value_to_continue)
            else:
                additional_bet = int(
                    self.game.rng.random() * (self.chips - min_turn_value_to_continue)
                )
                await self.make_bet_up_to(
                    max(2 * min_turn_value_to_continue, min_bet) + additional_bet
                )

        if self.get_turn_state() == PlayerTurnState.PLAYING_TURN:
            self.set_turn_state(PlayerTurnState.WAITING_FOR_TURN)

    async def receive_human_action(
        self,
        min_turn_value_to_continue: int,
        min_bet: int,
    ) -> str:
        if self.game.websocket is None:
            self.set_turn_state(PlayerTurnState.FOLDED)
            return "Fold"

        while self.get_turn_state() == PlayerTurnState.PLAYING_TURN:
            try:
                action = await self.game.websocket.recv()
            except websockets.exceptions.ConnectionClosed:
                self.set_turn_state(PlayerTurnState.FOLDED)
                return "Fold"

            bet_value = self.parse_bet_input(action)
            if action == "Fold":
                self.set_turn_state(PlayerTurnState.FOLDED)
                return action

            if action == "Check" and min_turn_value_to_continue == 0:
                await self.make_bet(0)
                self.set_turn_state(PlayerTurnState.WAITING_FOR_TURN)
                return action

            if action == "Call" and min_turn_value_to_continue <= self.chips:
                await self.make_bet(min_turn_value_to_continue)
                if self.get_turn_state() == PlayerTurnState.PLAYING_TURN:
                    self.set_turn_state(PlayerTurnState.WAITING_FOR_TURN)
                return action

            if bet_value is not None:
                is_legal_raise = (
                    bet_value >= min(2 * min_turn_value_to_continue, self.chips)
                    and bet_value <= self.chips
                    and bet_value >= min(min_bet, self.chips)
                )
                if is_legal_raise and await self.make_bet(bet_value):
                    if self.get_turn_state() == PlayerTurnState.PLAYING_TURN:
                        self.set_turn_state(PlayerTurnState.WAITING_FOR_TURN)
                    return action

        raise RuntimeError("Human turn exited without an action")

    async def play(
        self,
        min_turn_value_to_continue: int,
        min_bet: int,
        ai_player_cards: list[str],
        table_cards: list[str],
        history: list[str],
    ) -> tuple[int, str]:
        if self.is_robot:
            action = await self.play_ai_turn(
                min_turn_value_to_continue,
                min_bet,
                ai_player_cards,
                table_cards,
                history,
            )
        else:
            action = await self.receive_human_action(min_turn_value_to_continue, min_bet)

        self.set_played_current_phase(True)
        if self.get_turn_state() == PlayerTurnState.PLAYING_TURN:
            raise RuntimeError("Player turn did not settle correctly")
        return self.get_turn_bet_value(), self.parse_relative_bets(action)

    def parse_relative_bets(self, action: str) -> str:
        bet_value = self.parse_bet_input(action)
        if bet_value is not None:
            return f"Bet {self.round_bet_value}"
        return action

    def get_info_set(self, player_cards: list[str], table_cards: list[str], history: list[str]) -> str:
        parsed_player_cards = "".join(card[0] for card in player_cards)
        parsed_table_cards = "".join(card[0] for card in table_cards)
        history_with_bets_rounded_up = [self.round_up_bets(action) for action in history]
        history_abbreviated = [
            self.parse_action_to_info_set(action)
            for action in history_with_bets_rounded_up
        ]
        parsed_history = "".join(self.add_hyphen_to_history(history_abbreviated))
        return parsed_history + ":|" + parsed_player_cards + ("/" if parsed_table_cards else "") + parsed_table_cards

    def add_hyphen_to_history(self, history: list[str]) -> list[str]:
        if "/" not in history:
            return history

        new_history = history.copy()
        items_until_slash = []
        for item in history:
            if item == "/":
                break
            items_until_slash.append(item)

        if len(items_until_slash) % 2 == 1:
            new_history.insert(history.index("/"), "-")
        return new_history

    def round_up_bets(self, action: str) -> str:
        bet_value = self.parse_bet_input(action)
        if bet_value is None:
            return action
        return f"Bet {math.ceil(bet_value / 100) * 100}"

    def parse_action_to_info_set(self, action: str) -> str:
        if action == "Fold":
            return "f"
        if action == "Check":
            return "k"
        if action == "Call":
            return "c"
        if action in {"/", "-"}:
            return action

        bet_value = self.parse_bet_input(action)
        if bet_value is not None:
            return f"r{bet_value}"
        raise ValueError(f"Invalid action: {action}")

    def get_action(self, min_turn_value_to_continue: int) -> str:
        if self.turn_state == PlayerTurnState.FOLDED or self.turn_bet_value < min_turn_value_to_continue:
            return "Fold"
        if self.turn_bet_value == 0:
            return "Check"
        if self.turn_bet_value == min_turn_value_to_continue:
            return "Call"
        return f"Bet {self.turn_bet_value}"

    async def make_bet_up_to(self, amount: int) -> bool:
        return await self.make_bet(min(amount, self.chips))

    async def make_bet(self, amount: int) -> bool:
        if self.chips < amount:
            return False

        self.calculate_is_all_in(amount)
        self.set_turn_bet_value(amount)
        self.set_phase_bet_value(self.phase_bet_value + amount)
        self.set_round_bet_value(self.round_bet_value + amount)
        self.remove_chips(amount)
        await self.game.add_to_pot(amount)
        return True

    def calculate_is_all_in(self, amount: int) -> bool:
        if self.chips == amount:
            self.is_all_in = True
            self.set_turn_state(PlayerTurnState.ALL_IN)
            return True
        return False

    async def pay_blind(self, blind_value: int) -> None:
        await self.make_bet(blind_value)
        self.set_turn_bet_value(0)

    def set_turn_bet_value(self, amount: int) -> None:
        self.turn_bet_value = amount

    def get_turn_bet_value(self) -> int:
        return self.turn_bet_value

    def set_phase_bet_value(self, amount: int) -> None:
        self.phase_bet_value = amount

    def set_round_bet_value(self, amount: int) -> None:
        self.round_bet_value = amount
        self.round_bet_aux = amount

    def set_played_current_phase(self, played_current_phase: bool) -> None:
        self.played_current_phase = played_current_phase

    def get_played_current_phase(self) -> bool:
        return self.played_current_phase

    def remove_chips(self, amount: int) -> None:
        self.chips -= amount

    def add_chips(self, amount: int) -> None:
        self.chips += amount

    def set_chips(self, amount: int) -> None:
        self.chips = amount

    def add_chip_balance(self, amount: int) -> None:
        self.chip_balance += amount
        self.chips_won_history.append(amount)

    def __str__(self) -> str:
        return f"{self.name} has {self.chips} chips, and has the hand: {', '.join(map(str, self.cards))}"


class Players:
    def __init__(self, game, num_ai_players: int, num_human_players: int, initial_chips: int):
        self.game = game
        self.initial_players = self._set_initial_players(game, num_ai_players, num_human_players, initial_chips)
        self.current_dealer = self._set_initial_dealer()
        self.current_turn_player: Optional[Player] = None

    def _set_initial_players(
        self,
        game,
        num_ai_players: int,
        num_human_players: int,
        initial_chips: int,
    ) -> List[Player]:
        players = [Player(game, i, f"AI {i}", initial_chips) for i in range(num_ai_players)]
        players.extend(
            Player(game, num_ai_players + i, f"Player {num_ai_players + i}", initial_chips, is_human=True)
            for i in range(num_human_players)
        )
        return list(players)

    def _set_initial_dealer(self) -> Player:
        non_broke_players = self.get_players("non_broke")
        randomly_determined_initial_dealer = self.game.rng.randrange(len(non_broke_players))
        return non_broke_players[randomly_determined_initial_dealer]

    def get_players(self, group: PlayerGroups):
        if group == "all":
            condition = lambda player: True
        elif group == "non_broke":
            condition = lambda player: player.is_not_broke()
        elif group == "can_bet_in_current_turn":
            condition = lambda player: player.is_not_broke() and player.get_turn_state() not in {
                PlayerTurnState.FOLDED,
                PlayerTurnState.ALL_IN,
            }
        elif group == "active_in_hand":
            condition = lambda player: player.is_not_broke() and player.get_turn_state() != PlayerTurnState.FOLDED
        elif group == "all_in":
            condition = lambda player: player.get_turn_state() == PlayerTurnState.ALL_IN
        elif group == "human":
            condition = lambda player: not player.is_robot
        elif group == "not_human":
            condition = lambda player: player.is_robot
        else:
            raise ValueError(f"Unknown player group: {group}")

        return [player for player in self.initial_players if condition(player)]

    def order_players_by_id(self, players: List[Player], raw_id: int) -> list[Player]:
        player_id = raw_id % len(self.get_players("all"))
        return reorder_list(players, lambda player: player.id == player_id)

    def get_closest_group_player(self, group: PlayerGroups, raw_id: int) -> Optional[Player]:
        player_id = raw_id % len(self.get_players("all"))
        ordered_players = self.order_players_by_id(self.initial_players, player_id)
        group_players = set(self.get_players(group))
        return next((player for player in ordered_players if player in group_players), None)

    def get_next(self, group: PlayerGroups, player_id: int) -> Optional[Player]:
        return self.get_closest_group_player(group, player_id + 1)

    def initiate_players_for_phase(self, first_player: Optional[Player]) -> None:
        self.current_turn_player = first_player

    def initiate_players_for_round(self) -> None:
        for player in self.get_players("all"):
            player.set_turn_state(PlayerTurnState.NOT_PLAYING)

        for player in self.get_players("non_broke"):
            player.set_turn_state(PlayerTurnState.WAITING_FOR_TURN)
