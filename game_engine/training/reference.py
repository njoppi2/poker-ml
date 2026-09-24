"""Optional OpenSpiel adapter for independently checking solvers and evaluation.

Install with `pip install -e '.[training-reference]'`. OpenSpiel is deliberately
not a dependency of the app or the normal training CLI.
"""
import pyspiel
import numpy as np
from open_spiel.python import policy as spiel_policy

from .game import LeducGame


class SpielGame(pyspiel.Game):
    def __init__(self, model: LeducGame):
        self.model = model
        game_type = pyspiel.GameType(
            short_name="poker_ml_leduc", long_name="Poker ML modified Leduc",
            dynamics=pyspiel.GameType.Dynamics.SEQUENTIAL,
            chance_mode=pyspiel.GameType.ChanceMode.EXPLICIT_STOCHASTIC,
            information=pyspiel.GameType.Information.IMPERFECT_INFORMATION,
            utility=pyspiel.GameType.Utility.ZERO_SUM,
            reward_model=pyspiel.GameType.RewardModel.TERMINAL,
            max_num_players=2, min_num_players=2,
            provides_information_state_string=True,
            provides_information_state_tensor=False,
            provides_observation_string=False,
            provides_observation_tensor=False, parameter_specification={},
        )
        game_info = pyspiel.GameInfo(
            num_distinct_actions=max(len(model.deals), model.chips),
            max_chance_outcomes=len(model.deals), num_players=2,
            min_utility=-model.chips, max_utility=model.chips,
            utility_sum=0.0, max_game_length=model.max_depth + 1,
        )
        super().__init__(game_type, game_info, {})

    def new_initial_state(self):
        return SpielState(self)

    def make_py_observer(self, iig_obs_type=None, params=None):
        class Observer:
            tensor = np.zeros(0, dtype=np.float32)
            dict = {}

            def set_from(self, state, player):
                pass

            def string_from(self, state, player):
                if state.deal is None or state.is_terminal():
                    return ""
                return state.information_state_string(player)
        return Observer()


class SpielState(pyspiel.State):
    def __init__(self, game):
        super().__init__(game)
        self.model = game.model
        self.deal = None
        self.index = 0

    def current_player(self):
        if self.deal is None:
            return pyspiel.PlayerId.CHANCE
        if self.is_terminal():
            return pyspiel.PlayerId.TERMINAL
        return self.model.nodes[self.index].player

    def is_terminal(self):
        return self.deal is not None and self.model.nodes[self.index].player < 0

    def _legal_actions(self, player):
        return list(range(len(self.model.nodes[self.index].children)))

    def chance_outcomes(self):
        return list(enumerate(self.model.chance))

    def _apply_action(self, action):
        if self.deal is None:
            self.deal = action
        else:
            self.index = self.model.nodes[self.index].children[action]

    def _action_to_string(self, player, action):
        return str(action)

    def information_state_string(self, player=None):
        if self.deal is None:
            return ""
        if self.is_terminal():
            return f"terminal:{self.index}"
        node = self.model.nodes[self.index]
        key = self.model.infosets[node.infos[self.deal]].key
        player = node.player if player is None else player
        if player == node.player:
            return key
        history, cards = key.split(":|")
        return history + ":|" + "QKA"[self.model.deals[self.deal][player]] + cards[1:]

    def returns(self):
        value = self.model.nodes[self.index].payoffs[self.deal] if self.is_terminal() else 0.0
        return [value, -value]

    def __str__(self):
        return f"{self.deal}:{self.index}"

    def __deepcopy__(self, memo):
        # The compiled immutable tree is shared. Copy the state, not the game.
        state = SpielState(self.get_game())
        state.deal, state.index = self.deal, self.index
        return state


class SpielPolicy(spiel_policy.Policy):
    def __init__(self, game, rows):
        super().__init__(game, [0, 1])
        self.rows = rows

    def action_probabilities(self, state, player_id=None):
        info = state.model.nodes[state.index].infos[state.deal]
        return dict(enumerate(self.rows[info]))
