from games.balatro.joker import Joker, JokerContext


class MadnessJoker(Joker):

    def __init__(self):
        self.x_mult = 1.0

    def apply(self, context: JokerContext) -> JokerContext:
        nonboss_start = context.trigger in {
            "SMALL_BLIND_SELECTED",
            "BIG_BLIND_SELECTED",
        } or (context.trigger == "BLIND_SELECTED" and context.data.get("boss_blind") is False)
        if nonboss_start and not context.data.get("blueprint", False):
            self.x_mult += 0.5

            queued = context.data.get("queued_joker_destructions", ())
            candidates = tuple(
                joker
                for joker in getattr(context.state, "jokers", [])
                if joker is not self
                and not getattr(joker, "eternal", False)
                and not getattr(joker, "getting_sliced", False)
                and all(joker is not pending for pending in queued)
            )

            if candidates:
                context.data["destroy_joker_candidates"] = candidates
            return context

        if context.score is not None:
            context.score.x_mult *= self.x_mult

        return context
