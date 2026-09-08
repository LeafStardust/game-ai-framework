import random

from framework.core.random import set_seed


def test_seed_reproducibility():

    set_seed(42)

    first = random.random()

    set_seed(42)

    second = random.random()

    assert first == second