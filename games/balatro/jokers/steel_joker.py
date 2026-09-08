from games.balatro.joker import Joker, JokerContext
from games.balatro.mechanics import STEEL_CARD_PAYOFF


class SteelJoker(Joker):

    mechanics = frozenset({STEEL_CARD_PAYOFF})

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.score is None:
            return context

        owned_deck = getattr(context.state, "owned_deck", None)
        if owned_deck is None:
            return context

        steel_cards = sum(
            getattr(card, "enhancement", None) == "Steel"
            for card in owned_deck
        )
        context.score.x_mult *= 1 + (0.2 * steel_cards)
        return context
