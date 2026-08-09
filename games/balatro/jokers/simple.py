from games.balatro.joker import Joker
from games.balatro.scoring import HandScore


class FlatMultJoker(Joker):
    """
    Adds a fixed amount of Mult to the hand score.
    """

    def __init__(
        self,
        mult: int
    ):
        self.mult = mult


    def apply(
        self,
        state,
        score: HandScore
    ) -> HandScore:

        return HandScore(
            score.chips,
            score.mult + self.mult
        )