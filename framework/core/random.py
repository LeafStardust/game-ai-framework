import random


def set_seed(seed: int | None):
    """
    Sets global random seed.
    """

    if seed is not None:
        random.seed(seed)