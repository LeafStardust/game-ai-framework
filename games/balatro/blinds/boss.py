from games.balatro.blinds.blind import Blind, BlindType


class BossBlind(Blind):
    """
    Represents a boss blind.
    """

    def __init__(
        self,
        requirement: int,
        modifiers=None
    ):
        super().__init__(
            BlindType.BOSS,
            requirement,
            modifiers=modifiers
        )