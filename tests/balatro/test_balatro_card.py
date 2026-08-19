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


def test_balatro_card_can_have_edition():

    card = BalatroCard(
        "A",
        "Hearts",
        edition="Foil"
    )

    assert card.edition == "Foil"


def test_balatro_card_can_have_seal():

    card = BalatroCard(
        "A",
        "Hearts",
        seal="Gold"
    )

    assert card.seal == "Gold"


def test_wild_card_matches_any_suit():

    card = BalatroCard(
        "A",
        "Hearts",
        enhancement="Wild"
    )

    assert card.matches_suit("Spades")
    assert card.matches_suit("Clubs")


def test_stone_card_does_not_have_rank():

    card = BalatroCard(
        "A",
        "Hearts",
        enhancement="Stone"
    )

    assert not card.has_rank("A")


def test_stone_card_does_not_match_suit():

    card = BalatroCard(
        "A",
        "Hearts",
        enhancement="Stone"
    )

    assert not card.matches_suit("Hearts")