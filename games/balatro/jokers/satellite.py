from games.balatro.joker import Joker, JokerContext


class SatelliteJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "ROUND_ENDED":
            return context

        planets = set(
            context.data.get("used_planets", [])
        )

        context.data["money"] = (
            context.data.get("money", 0)
            + len(planets)
        )

        return context