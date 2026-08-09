from games.balatro.events import BalatroEventType
from games.balatro.joker import Joker, JokerContext


class RideTheBusJoker(Joker):

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

        has_face_card = any(
            card.rank in ("J", "Q", "K")
            for card in context.cards
        )

        if has_face_card:
            self.mult = 0
        else:
            self.mult += 1

        if context.score is not None:
            context.score.mult += self.mult

        return context