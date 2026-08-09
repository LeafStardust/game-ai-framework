from games.balatro.events import BalatroEventType
from games.balatro.joker import Joker, JokerContext


class RedCardJoker(Joker):

    def __init__(self):
        self.mult = 0

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.event is None:
            return context

        if context.event.type not in (
            BalatroEventType.BOOSTER_SKIPPED,
            BalatroEventType.VOUCHER_SKIPPED
        ):
            return context

        self.mult += 3

        if context.score is not None:
            context.score.mult += 3

        return context