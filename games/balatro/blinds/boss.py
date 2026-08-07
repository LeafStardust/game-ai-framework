from games.balatro.blinds.blind import Blind, BlindType

from games.balatro.blinds.modifiers.restrictions import (
    DisableFirstCardModifier
)


class BossBlind(Blind):

    def __init__(
        self,
        requirement: int,
        modifiers=None,
        name: str = "BOSS"
    ):
        super().__init__(
            BlindType.BOSS,
            requirement,
            modifiers=modifiers
        )

        self.name = name


    def copy(self):

        return self.__class__(
            self.requirement
        )


class TheHook(BossBlind):

    def __init__(
        self,
        requirement: int
    ):
        super().__init__(
            requirement,
            modifiers=[
                DisableFirstCardModifier()
            ],
            name="THE_HOOK"
        )


class TheWall(BossBlind):

    def __init__(
        self,
        requirement: int
    ):
        super().__init__(
            requirement,
            name="THE_WALL"
        )