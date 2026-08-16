from games.balatro.deck_rules import starting_deck_size_for_name
from games.balatro.joker import Joker, JokerContext


class ErosionJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        owned_deck = getattr(context.state, "owned_deck", None)
        target_size = starting_deck_size_for_name(
            getattr(context.state, "deck_name", None)
        )
        if owned_deck is None or target_size is None:
            return context

        missing = max(target_size - len(owned_deck), 0)
        context.score.mult += missing * 4

        return context
