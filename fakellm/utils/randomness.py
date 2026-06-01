"""Seeded random number generator utility."""

import random
from typing import Optional


def get_rng(seed: Optional[int] = None) -> random.Random:
    """
    Return a random.Random instance, optionally seeded for reproducibility.

    Args:
        seed: Optional integer seed. If None, a fresh unseeded instance is returned.

    Returns:
        A random.Random instance.
    """
    rng = random.Random()
    if seed is not None:
        rng.seed(seed)
    return rng