from games.balatro.blinds.blind import (
    create_small_blind,
    create_big_blind
)


SMALL_BLIND_REQUIREMENTS = {
    1: 300,
    2: 450,
    3: 700,
    4: 900,
    5: 1200
}


BIG_BLIND_REQUIREMENTS = {
    1: 450,
    2: 675,
    3: 1050,
    4: 1350,
    5: 1800
}


BOSS_BLIND_REQUIREMENTS = {
    1: 2000,
    2: 3000,
    3: 4500,
    4: 6000,
    5: 8000
}


def small_blind(
    ante: int
):

    return create_small_blind(
        SMALL_BLIND_REQUIREMENTS.get(
            ante,
            1200 * ante
        )
    )


def big_blind(
    ante: int
):

    return create_big_blind(
        BIG_BLIND_REQUIREMENTS.get(
            ante,
            1800 * ante
        )
    )


def boss_blind_requirement(
    ante: int
) -> int:

    return BOSS_BLIND_REQUIREMENTS.get(
        ante,
        8000 * ante
    )