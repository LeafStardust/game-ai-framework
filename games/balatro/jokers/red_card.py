from games.balatro.events import BalatroEventType
from games.balatro.joker import Joker, JokerContext


class RedCardJoker(Joker):

    def __init__(self):
        self.mult = 0

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if (
            context.event is not None
            and context.event.type in (
                BalatroEventType.BOOSTER_SKIPPED,
                BalatroEventType.VOUCHER_SKIPPED,
            )
        ):
            self.mult += 3
            return context

        if context.score is not None:
            context.score.mult += self.mult

        return context
