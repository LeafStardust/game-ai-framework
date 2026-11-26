from games.balatro.joker import Joker, JokerContext
from games.balatro.mechanics import CARD_DESTRUCTION, SPECTRAL_GENERATION


class SixthSenseJoker(Joker):

    mechanics = frozenset({CARD_DESTRUCTION, SPECTRAL_GENERATION})

    def apply(self, context: JokerContext) -> JokerContext:
        """The scoring phase is inert. The destruction phase owns this effect."""
        return context


def sixth_sense_destroys(jokers, cards, *, first_hand: bool | None) -> bool:
    """Resolve the single-card destruction trigger before any capacity check."""
    return (
        first_hand is True
        and len(cards) == 1
        and cards[0].rank == "6"
        and not cards[0].is_stone
        and any(
            type(joker) is SixthSenseJoker and not joker.debuffed
            for joker in jokers
        )
    )
