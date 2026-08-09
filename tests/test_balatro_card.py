from games.balatro.card import BalatroCard


def test_balatro_card_has_no_enhancement_by_default():

    card = BalatroCard(
        "A",
        "Hearts"
    )

    assert card.enhancement is None


def test_balatro_card_can_have_enhancement():

    card = BalatroCard(
        "A",
        "Hearts",
        "Steel"
    )

    assert card.enhancement == "Steel"