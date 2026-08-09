from games.balatro.joker import Joker, JokerContext


class DaggerJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "BLIND_SELECTED":
            return context

        jokers = getattr(context.state, "jokers", [])

        target = next(
            (
                joker
                for joker in jokers
                if joker is not self
            ),
            None
        )

        if target is None:
            return context

        context.data["destroy_joker"] = target
        context.data["dagger_mult"] = (
            context.data.get("dagger_mult", 0) + 20
        )

        return context