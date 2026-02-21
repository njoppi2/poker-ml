import os
import random
from typing import Optional


def resolve_random_seed(explicit_seed: Optional[int] = None) -> Optional[int]:
    if explicit_seed is not None:
        return int(explicit_seed)

    env_value = os.getenv("POKER_ML_RANDOM_SEED", "").strip()
    if env_value == "":
        return None

    return int(env_value)


def build_rng(seed: Optional[int]) -> random.Random:
    return random.Random(seed)


def shuffled(values: list[int], seed: int) -> list[int]:
    copied_values = values.copy()
    build_rng(seed).shuffle(copied_values)
    return copied_values
