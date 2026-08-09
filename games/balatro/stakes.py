from dataclasses import dataclass
from enum import IntEnum


class StakeLevel(IntEnum):
    WHITE = 1
    RED = 2
    GREEN = 3
    BLACK = 4
    BLUE = 5
    PURPLE = 6
    ORANGE = 7
    GOLD = 8


@dataclass(frozen=True)
class BalatroStake:
    level: StakeLevel
    name: str
    small_blind_reward: bool = True
    discard_modifier: int = 0
    score_requirements: dict[int, int] | None = None
    eternal_joker_chance: float = 0.0
    perishable_joker_chance: float = 0.0
    rental_joker_chance: float = 0.0

    def requirement_for_ante(self, ante: int, base: int) -> int:
        if self.score_requirements and ante in self.score_requirements:
            return self.score_requirements[ante]
        return base


WHITE_STAKE = BalatroStake(
    StakeLevel.WHITE,
    "WHITE",
)

RED_STAKE = BalatroStake(
    StakeLevel.RED,
    "RED",
    small_blind_reward=False,
)

GREEN_STAKE = BalatroStake(
    StakeLevel.GREEN,
    "GREEN",
    small_blind_reward=False,
    score_requirements={
        1: 300,
        2: 900,
        3: 2600,
        4: 8000,
        5: 20000,
        6: 36000,
        7: 60000,
        8: 100000,
    },
)

BLACK_STAKE = BalatroStake(
    StakeLevel.BLACK,
    "BLACK",
    small_blind_reward=False,
    score_requirements=GREEN_STAKE.score_requirements,
    eternal_joker_chance=0.30,
)

BLUE_STAKE = BalatroStake(
    StakeLevel.BLUE,
    "BLUE",
    small_blind_reward=False,
    discard_modifier=-1,
    score_requirements=GREEN_STAKE.score_requirements,
    eternal_joker_chance=0.30,
)

PURPLE_STAKE = BalatroStake(
    StakeLevel.PURPLE,
    "PURPLE",
    small_blind_reward=False,
    discard_modifier=-1,
    score_requirements={
        1: 300,
        2: 1000,
        3: 3200,
        4: 9000,
        5: 25000,
        6: 60000,
        7: 110000,
        8: 200000,
    },
    eternal_joker_chance=0.30,
)

ORANGE_STAKE = BalatroStake(
    StakeLevel.ORANGE,
    "ORANGE",
    small_blind_reward=False,
    discard_modifier=-1,
    score_requirements=PURPLE_STAKE.score_requirements,
    eternal_joker_chance=0.30,
    perishable_joker_chance=0.30,
)

GOLD_STAKE = BalatroStake(
    StakeLevel.GOLD,
    "GOLD",
    small_blind_reward=False,
    discard_modifier=-1,
    score_requirements=PURPLE_STAKE.score_requirements,
    eternal_joker_chance=0.30,
    perishable_joker_chance=0.30,
    rental_joker_chance=0.30,
)


STAKES = {
    stake.name: stake
    for stake in (
        WHITE_STAKE,
        RED_STAKE,
        GREEN_STAKE,
        BLACK_STAKE,
        BLUE_STAKE,
        PURPLE_STAKE,
        ORANGE_STAKE,
        GOLD_STAKE,
    )
}


def create_stake(name: str) -> BalatroStake:
    return STAKES[name]
