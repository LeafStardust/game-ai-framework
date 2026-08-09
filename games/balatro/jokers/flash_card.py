from games.balatro.events import BalatroEventType
from games.balatro.joker import Joker, JokerContext


class FlashCardJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        rerolls = context.data.get("rerolls", 0)

        context.score.mult += rerolls * 2

        return context