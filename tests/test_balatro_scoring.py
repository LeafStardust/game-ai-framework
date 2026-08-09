from games.balatro.scoring import BalatroScorer
from games.balatro.hand import PokerHand
from games.balatro.card import BalatroCard


def test_pair_scoring():

    scorer = BalatroScorer()

    score = scorer.score(
        PokerHand.PAIR
    )

    assert score.chips == 10
    assert score.mult == 2
    assert score.total == 20


def test_full_house_scoring():

    scorer = BalatroScorer()

    score = scorer.score(
        PokerHand.FULL_HOUSE
    )

    assert score.chips == 40
    assert score.mult == 4
    assert score.total == 160


def test_bonus_enhancement():

    scorer = BalatroScorer()

    score = scorer.score(
        PokerHand.HIGH_CARD,
        cards=[
            BalatroCard(
                "A",
                "Hearts",
                enhancement="Bonus"
            )
        ]
    )

    assert score.chips == 35


def test_mult_enhancement():

    scorer = BalatroScorer()

    score = scorer.score(
        PokerHand.HIGH_CARD,
        cards=[
            BalatroCard(
                "A",
                "Hearts",
                enhancement="Mult"
            )
        ]
    )

    assert score.mult == 5


def test_glass_enhancement():

    scorer = BalatroScorer()

    score = scorer.score(
        PokerHand.HIGH_CARD,
        cards=[
            BalatroCard(
                "A",
                "Hearts",
                enhancement="Glass"
            )
        ]
    )

    assert score.x_mult == 2.0


def test_stone_enhancement():

    scorer = BalatroScorer()

    score = scorer.score(
        PokerHand.HIGH_CARD,
        cards=[
            BalatroCard(
                "A",
                "Hearts",
                enhancement="Stone"
            )
        ]
    )

    assert score.chips == 55


def test_steel_enhancement():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "hand": [
                BalatroCard(
                    "A",
                    "Hearts",
                    enhancement="Steel"
                )
            ],
            "jokers": []
        }
    )()

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state
    )

    assert score.x_mult == 1.5


def test_foil_edition():

    scorer = BalatroScorer()

    score = scorer.score(
        PokerHand.HIGH_CARD,
        cards=[
            BalatroCard(
                "A",
                "Hearts",
                edition="Foil"
            )
        ]
    )

    assert score.chips == 55


def test_holographic_edition():

    scorer = BalatroScorer()

    score = scorer.score(
        PokerHand.HIGH_CARD,
        cards=[
            BalatroCard(
                "A",
                "Hearts",
                edition="Holographic"
            )
        ]
    )

    assert score.mult == 11


def test_polychrome_edition():

    scorer = BalatroScorer()

    score = scorer.score(
        PokerHand.HIGH_CARD,
        cards=[
            BalatroCard(
                "A",
                "Hearts",
                edition="Polychrome"
            )
        ]
    )

    assert score.x_mult == 1.5


def test_combined_card_modifiers():

    scorer = BalatroScorer()

    score = scorer.score(
        PokerHand.HIGH_CARD,
        cards=[
            BalatroCard(
                "A",
                "Hearts",
                enhancement="Mult",
                edition="Polychrome",
                seal="Gold"
            )
        ]
    )

    assert score.chips == 5
    assert score.mult == 5
    assert score.x_mult == 1.5