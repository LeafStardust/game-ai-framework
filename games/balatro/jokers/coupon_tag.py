from games.balatro.joker import Joker, JokerContext


class CouponTagJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "ROUND_STARTED":
            return context

        context.data["shop_free"] = True

        return context