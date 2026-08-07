from enum import Enum

from games.balatro.blinds.base import BlindModifier


class BlindType(Enum):
    SMALL = "SMALL"
    BIG = "BIG"
    BOSS = "BOSS"


class Blind:

    def __init__(
        self,
        blind_type: BlindType,
        requirement: int,
        reward: int = 0,
        modifiers: list[BlindModifier] | None = None
    ):
        self.type = blind_type
        self.requirement = requirement
        self.reward = reward
        self.modifiers = modifiers or []


    def apply_modifiers(
        self,
        state,
        action
    ) -> bool:

        for modifier in self.modifiers:

            if not modifier.apply(
                state,
                action
            ):
                return False

        return True


    def copy(self):

        return Blind(
            self.type,
            self.requirement,
            self.reward,
            self.modifiers.copy()
        )


def create_small_blind(
    requirement: int
) -> Blind:

    return Blind(
        BlindType.SMALL,
        requirement
    )


def create_big_blind(
    requirement: int
) -> Blind:

    return Blind(
        BlindType.BIG,
        requirement
    )