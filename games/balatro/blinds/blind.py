from enum import Enum

from games.balatro.blinds.base import BlindModifier


class BlindType(Enum):
    SMALL = "SMALL"
    BIG = "BIG"
    BOSS = "BOSS"


class Blind:
    """
    Represents a Balatro blind.
    """

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
    ):
        for modifier in self.modifiers:
            modifier.apply(
                state,
                action
            )