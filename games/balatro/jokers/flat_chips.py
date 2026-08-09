from games.balatro.joker import Joker
from games.balatro.scoring import HandScore


class FlatChipsJoker(Joker):
    """
    Adds a fixed amount of Chips to the hand score.
    """

    def __init__(
        self,
        chips: int
    ):
        self.chips = chips

    def apply(
        self,
        state,
        score: HandScore
    ) -> HandScore:

        return HandScore(
            score.chips + self.chips,
            score.mult
        )