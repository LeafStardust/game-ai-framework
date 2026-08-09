from games.balatro.joker import Joker
from games.balatro.scoring import HandScore


class BannerJoker(Joker):

    def apply(
        self,
        state,
        cards,
        score: HandScore
    ) -> HandScore:

        chips = state.discards_remaining * 30

        return HandScore(
            score.chips + chips,
            score.mult
        )