from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Optional

from treys import Card, Deck, Evaluator

from .ai import NashBlueprintPolicy
from .blind_structure import BlindStructure
from .common_types import ChipMode, LeducPhases, PokerPhases
from .config import GameConfig
from .player import Player, PlayerTurnState, Players
from .protocol import serialize_game_state
from .random_control import build_rng, resolve_random_seed


class Game:
    def __init__(
        self,
        websocket,
        game_type: str,
        config: GameConfig,
    ):
        self.websocket = websocket
        self.game_type = game_type
        self.is_leduc = game_type == "Leduc"
        self.chip_mode = config.chip_mode
        self.reset_chips_every_round = self.chip_mode == ChipMode.RESET_EACH_ROUND
        self.max_rounds = config.max_rounds
        self.initial_chips = config.initial_chips
        self.random_seed = resolve_random_seed(config.random_seed)
        self.rng = build_rng(self.random_seed)
        self.players = Players(self, config.num_ai_players, config.num_human_players, config.initial_chips)
        ai_players = self.players.get_players("not_human")
        self.ai_player = ai_players[0] if ai_players else None
        self.policy = (
            NashBlueprintPolicy(model_path=config.model_path, rng=self.rng)
            if ai_players
            else None
        )
        self._blind_structure = BlindStructure(self.is_leduc)
        self._increase_blind_every = config.increase_blind_every
        self.table_cards: list[Card] = []
        self.round_num = 0
        self.total_pot = 0
        self.phase_pot = 0
        self.phase_name: PokerPhases | LeducPhases | None = None
        self.min_turn_value_to_continue: int = 0
        self.min_bet = 0
        self.is_game_over = False
        self.winner_name: Optional[str] = None

    async def start_game(self) -> None:
        while not self.is_finished():
            small_blind, big_blind = self.get_blinds()
            round_instance = Round(self, small_blind, big_blind)
            await round_instance.start()
            self.finish_round()
            await self.send_game_state()

    def get_blinds(self) -> tuple[int, int]:
        return self._blind_structure.get_blinds()

    def check_win(self) -> bool:
        return len(self.players.get_players("non_broke")) == 1

    def is_finished(self) -> bool:
        if self.chip_mode == ChipMode.RESET_EACH_ROUND:
            return self.max_rounds is not None and self.round_num >= self.max_rounds
        return self.check_win()

    def finish_round(self) -> None:
        self.round_num += 1

        if self._increase_blind_every and self.round_num % self._increase_blind_every == 0:
            self._blind_structure.increase_blind()

        if self.is_finished():
            self.is_game_over = True
            self.winner_name = self.get_winner_name()
            return

        self.pass_dealer_chip()

    def get_winner_name(self) -> Optional[str]:
        if self.chip_mode == ChipMode.PERSISTENT_MATCH:
            remaining_players = self.players.get_players("non_broke")
            if len(remaining_players) == 1:
                return remaining_players[0].name
            return None

        all_players = sorted(
            self.players.get_players("all"),
            key=lambda player: player.chip_balance,
            reverse=True,
        )
        if not all_players:
            return None
        if len(all_players) > 1 and all_players[0].chip_balance == all_players[1].chip_balance:
            return None
        return all_players[0].name

    def get_current_dealer(self) -> Player:
        return self.players.current_dealer

    def pass_dealer_chip(self) -> None:
        next_dealer = self.players.get_next("non_broke", self.get_current_dealer().id)
        self.players.current_dealer = next_dealer

    async def add_to_pot(self, amount: int) -> None:
        self.total_pot += amount
        self.phase_pot += amount

    def finalize_round_balances(self) -> None:
        for player in self.players.get_players("all"):
            round_chip_balance = player.chips - player.round_start_chips
            player.round_end_chips = player.chips
            player.add_chip_balance(round_chip_balance)
            if self.reset_chips_every_round:
                player.set_chips(self.initial_chips)

    async def send_game_state(self) -> None:
        if self.websocket:
            await self.websocket.send(serialize_game_state(self))


class Round:
    def __init__(self, game: Game, small_blind: int, big_blind: int):
        self.game = game
        self.history: list[str] = []
        self.players = game.players
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.game.min_bet = big_blind
        self.players_in_the_hand: list[Player] = []
        self.is_showdown = False
        self.players.initiate_players_for_round()
        leduc_deck = [
            Card.new("As"),
            Card.new("Ad"),
            Card.new("Ks"),
            Card.new("Kd"),
            Card.new("Qs"),
            Card.new("Qd"),
        ]
        self.deck = leduc_deck if self.game.is_leduc else Deck().GetFullDeck()
        self.game.rng.shuffle(self.deck)
        self.table_str: list[str] = []
        self.ai_player_cards_str = []

    async def start(self) -> None:
        self.give_players_cards(self.deck)
        phases = LeducPhases if self.game.is_leduc else PokerPhases
        for current_phase in phases:
            first_player, table_cards_to_show_count = self.get_phase_variables(current_phase)
            new_table_cards = [self.deck.pop() for _ in range(table_cards_to_show_count)]
            self.game.table_cards.extend(new_table_cards)
            self.table_str = [Card.int_to_str(card) for card in self.game.table_cards]
            phase = Phase(self, current_phase, self.small_blind, self.big_blind, first_player)
            await phase.start()

            players_in_the_hand = self.players.get_players("active_in_hand")
            if len(players_in_the_hand) == 1:
                self.players_in_the_hand.extend(players_in_the_hand)
                self.is_showdown = False
                break
            if current_phase == PokerPhases.RIVER or current_phase == LeducPhases.FLOP:
                self.players_in_the_hand.extend(players_in_the_hand)
                self.is_showdown = True

        self.finish_round()

    def get_phase_variables(self, phase_name: PokerPhases | LeducPhases) -> tuple[Player, int]:
        if self.game.is_leduc:
            phase_info = {
                LeducPhases.PRE_FLOP: {"table_cards_count": 0, "offset": 0},
                LeducPhases.FLOP: {"table_cards_count": 1, "offset": 1},
            }
        else:
            phase_info = {
                PokerPhases.PRE_FLOP: {"table_cards_count": 0, "offset": 3},
                PokerPhases.FLOP: {"table_cards_count": 3, "offset": 1},
                PokerPhases.TURN: {"table_cards_count": 1, "offset": 1},
                PokerPhases.RIVER: {"table_cards_count": 1, "offset": 1},
            }

        phase_data = phase_info[phase_name]
        first_player_id = self.players.current_dealer.id + phase_data["offset"]
        first_phase_player = self.players.get_closest_group_player("non_broke", first_player_id)
        return first_phase_player, phase_data["table_cards_count"]

    def give_players_cards(self, deck) -> None:
        for player in self.players.initial_players:
            if player.is_broke():
                continue

            num_cards_to_draw = 1 if self.game.is_leduc else 2
            player.cards = [deck.pop() for _ in range(num_cards_to_draw)]

        if self.game.ai_player:
            self.ai_player_cards_str = [Card.int_to_str(card) for card in self.game.ai_player.cards]

    def reset_round_player(self, player: Player) -> None:
        player.reset_round_player()
        if player.chips == 0:
            player.set_turn_state(PlayerTurnState.NOT_PLAYING)
        else:
            player.set_turn_state(PlayerTurnState.WAITING_FOR_TURN)

    def take_from_player_round_bet(self, player: Player, amount: int) -> int:
        if player.round_bet_value < amount:
            amount = player.round_bet_aux
        player.round_bet_aux -= amount
        self.game.total_pot -= amount
        return amount

    def distribute_pot(self, order_of_best_hands: list[list[Player]]) -> None:
        for equivalent_hand_group in order_of_best_hands:
            if all(player.round_bet_aux == 0 for player in self.players.get_players("non_broke")):
                break

            sorted_hand_group = sorted(
                equivalent_hand_group,
                key=lambda player: player.round_bet_aux,
            )

            for hand_group_player in sorted_hand_group:
                hand_group_player_pot = hand_group_player.round_bet_aux
                remaining_players_to_receive = [
                    player
                    for player in sorted_hand_group
                    if player.round_bet_aux >= hand_group_player_pot
                ]
                if not remaining_players_to_receive:
                    continue

                chips_for_remaining_players = 0
                for non_broke_player in self.players.get_players("non_broke"):
                    if non_broke_player.round_bet_aux == 0:
                        continue
                    amount_taken = self.take_from_player_round_bet(
                        non_broke_player,
                        hand_group_player_pot,
                    )
                    chips_for_remaining_players += amount_taken

                remaining_players_to_receive_count = len(remaining_players_to_receive)
                chips_remaining = chips_for_remaining_players % remaining_players_to_receive_count
                random_player = self.game.rng.choice(remaining_players_to_receive)
                random_player.add_chips(chips_remaining)
                chips_for_remaining_players -= chips_remaining

                chips_per_player = chips_for_remaining_players // remaining_players_to_receive_count
                for group_player in remaining_players_to_receive:
                    group_player.add_chips(chips_per_player)

        self.game.finalize_round_balances()
        assert self.game.total_pot == 0

    def calculate_winners(self) -> list[list[Player]]:
        evaluator = Evaluator()

        for player in self.players_in_the_hand:
            if self.game.is_leduc:
                hand_card_value = Card.get_rank_int(player.cards[0])
                pair_value = (
                    100
                    if self.is_showdown
                    and Card.get_rank_int(self.game.table_cards[0]) == Card.get_rank_int(player.cards[0])
                    else 0
                )
                player.show_down_hand["value"] = -hand_card_value - pair_value
            else:
                player.show_down_hand["value"] = evaluator.evaluate(self.game.table_cards, player.cards)

        sorted_players = sorted(self.players_in_the_hand, key=lambda player: player.show_down_hand["value"])
        rank_groups = defaultdict(list)
        for player in sorted_players:
            rank_groups[player.show_down_hand["value"]].append(player)
        return list(rank_groups.values())

    def finish_round(self) -> None:
        assert self.players_in_the_hand
        assert (len(self.players_in_the_hand) >= 2) == self.is_showdown
        assert self.game.total_pot == sum(
            player.round_bet_value for player in self.players.get_players("non_broke")
        )
        assert all(
            player.round_bet_aux == player.round_bet_value
            for player in self.players.get_players("non_broke")
        )

        order_of_best_hands = self.calculate_winners()
        self.distribute_pot(order_of_best_hands)

        for player in self.players.get_players("all"):
            self.reset_round_player(player)

        self.game.table_cards = []


class Phase:
    def __init__(
        self,
        round_instance: Round,
        phase_name: PokerPhases | LeducPhases,
        small_blind: int,
        big_blind: int,
        first_player: Player,
    ):
        self.round = round_instance
        self.players = round_instance.players
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.round.game.phase_name = phase_name
        self.players.initiate_players_for_phase(first_player)

    async def start(self) -> int:
        self.round.game.phase_pot = 0
        await self.round.game.send_game_state()

        if self.round.game.phase_name in {PokerPhases.PRE_FLOP, LeducPhases.PRE_FLOP}:
            small_blind_player = self.players.get_closest_group_player(
                "non_broke",
                self.players.current_dealer.id + 1,
            )
            big_blind_player = self.players.get_closest_group_player(
                "non_broke",
                self.players.current_dealer.id + 2,
            )
            await small_blind_player.pay_blind(self.small_blind)
            await big_blind_player.pay_blind(self.big_blind)

        while len(self.players.get_players("active_in_hand")) > 1:
            current_player = self.get_current_turn_player()
            assert self.get_min_phase_value_to_continue() >= 0
            if current_player is None:
                break

            players_waiting_for_turn = self.players.get_players("can_bet_in_current_turn")
            if (
                current_player.get_played_current_phase()
                and self.get_min_phase_value_to_continue() == current_player.phase_bet_value
            ):
                break
            if current_player in players_waiting_for_turn and players_waiting_for_turn:
                turn = Turn(self, current_player, self.get_min_phase_value_to_continue())
                await turn.start()

            players_that_can_bet = self.players.get_players("can_bet_in_current_turn")
            if players_that_can_bet:
                self.set_current_turn_player(
                    self.players.get_next("can_bet_in_current_turn", current_player.id)
                )
                await self.round.game.send_game_state()
            else:
                break

        await self.round.game.send_game_state()
        await asyncio.sleep(0.2)
        self.finish_phase()
        return self.round.game.phase_pot

    def get_min_phase_value_to_continue(self) -> int:
        return max(player.phase_bet_value for player in self.players.get_players("active_in_hand"))

    def get_current_turn_player(self) -> Optional[Player]:
        return self.players.current_turn_player

    def set_current_turn_player(self, player: Optional[Player]) -> None:
        self.players.current_turn_player = player

    def reset_phase_player(self, player: Player) -> None:
        player.set_played_current_phase(False)
        player.set_phase_bet_value(0)

    def finish_phase(self) -> None:
        for player in self.players.get_players("non_broke"):
            self.reset_phase_player(player)
        self.round.history.append("/")


class Turn:
    def __init__(self, phase: Phase, player: Player, min_phase_value_to_continue: int):
        self.phase = phase
        self.player = player
        self.min_phase_value_to_continue = min_phase_value_to_continue
        self.current_player_phase_bet = player.phase_bet_value
        self.phase.round.game.min_turn_value_to_continue = (
            self.min_phase_value_to_continue - self.current_player_phase_bet
        )

    async def start(self) -> int:
        assert self.player.get_turn_state() == PlayerTurnState.WAITING_FOR_TURN
        self.player.set_turn_state(PlayerTurnState.PLAYING_TURN)
        await self.phase.round.game.send_game_state()

        bet, action = await self.player.play(
            self.phase.round.game.min_turn_value_to_continue,
            self.phase.round.game.min_bet,
            self.phase.round.ai_player_cards_str,
            self.phase.round.table_str,
            self.phase.round.history,
        )

        await self.finish_turn(action)
        return bet

    async def finish_turn(self, action: str) -> None:
        self.phase.round.history.append(action)
        self.player.set_turn_bet_value(0)
        self.phase.round.game.min_turn_value_to_continue = 0
