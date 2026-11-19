from types import SimpleNamespace

from games.balatro.card import BalatroCard
from games.balatro.joker import JokerContext
from games.balatro.jokers.vampire import VampireJoker


def test_vampire_owner_ignores_debuffed_enhanced_scoring_card():
    card = BalatroCard("A", "Spades", enhancement="Mult", debuffed=True)
    vampire = VampireJoker()

    result = vampire.apply(
        JokerContext(
            state=SimpleNamespace(),
            cards=[card],
            trigger="HAND_PLAYED",
            data={"scoring_cards": [card]},
        )
    )

    assert result.data["scoring_cards"] == [card]
    assert card.enhancement == "Mult"
    assert vampire.x_mult == 1.0
