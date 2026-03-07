from __future__ import annotations

import pickle
from pathlib import Path
from random import Random
from typing import Any


def action_from_code(action_code: int, selected_action_index: int, last_action: str) -> str:
    if last_action.isdigit():
        action_map = {0: "f", 1: "c"}
    else:
        action_map = {0: "k"}

    if selected_action_index in action_map:
        return action_map[selected_action_index]

    return f"r{action_code}00"


class NashBlueprintPolicy:
    def __init__(self, *, model_path: str | Path, rng: Random):
        self.model_path = Path(model_path)
        self.rng = rng
        self._model: dict[str, Any] | None = None

    def _load_model(self) -> dict[str, Any]:
        if self._model is None:
            with self.model_path.open("rb") as file_handle:
                self._model = pickle.load(file_handle)

        return self._model

    def decide_next_action(self, infoset: str) -> str:
        action_data = self._load_model().get(infoset)
        if action_data is None:
            return "c"

        actions, probabilities = action_data
        selected_action_code = self.rng.choices(actions, weights=probabilities, k=1)[0]

        selected_action_index = actions.index(selected_action_code)
        split_result = infoset.split(":|")
        if split_result and split_result[0]:
            last_action = split_result[0][-1]
        else:
            last_action = "y"

        return action_from_code(selected_action_code, selected_action_index, last_action)
