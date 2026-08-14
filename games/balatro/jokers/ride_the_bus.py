from games.balatro.events import BalatroEventType
from games.balatro.joker import (
    Joker,
    JokerContext,
    Playstyle,
    PlaystyleAffinity,
)


class RideTheBusJoker(Joker):

    playstyle_affinities = {
        Playstyle.NO_FACE_CARDS: PlaystyleAffinity.POSITIVE,
        Playstyle.FACE_CARDS: PlaystyleAffinity.NEGATIVE,
    }

    def __init__(self):
        self.mult = 0

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.event is None:
            return context

        if context.event.type != BalatroEventType.HAND_SCORED:
            return context

        scoring_cards = context.data.get("scoring_cards", context.cards)
        has_face_card = any(
            card.rank in ("J", "Q", "K")
            for card in scoring_cards
        )

        if has_face_card:
            self.mult = 0
        else:
            self.mult += 1

        if context.score is not None:
            context.score.mult += self.mult

        return context
