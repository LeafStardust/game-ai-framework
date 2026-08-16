from games.balatro.joker import Joker, JokerContext


class BaseballCardJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None or context.trigger != "OTHER_JOKER":
            return context

        other_joker = context.data.get("other_joker")
        if other_joker is None or other_joker is self:
            return context

        if str(getattr(other_joker, "rarity", "")).upper() == "UNCOMMON":
            context.score.x_mult *= 1.5

        return context
