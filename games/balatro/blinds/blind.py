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
        modifiers: list[BlindModifier] | None = None,
        disabled: bool = False,
        tag_key: str | None = None,
    ):
        if tag_key is not None and not isinstance(tag_key, str):
            raise TypeError("tag_key must be a string or None")
        normalized_tag = tag_key.strip().lower() if tag_key is not None else None
        if tag_key is not None and not normalized_tag:
            raise ValueError("tag_key must be a non-empty string when observed")

        self.type = blind_type
        self.requirement = requirement
        self.reward = reward
        self.modifiers = modifiers or []
        self.disabled = bool(disabled)
        self.tag_key = normalized_tag


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
            self.modifiers.copy(),
            disabled=self.disabled,
            tag_key=self.tag_key,
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