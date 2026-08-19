from games.balatro.scoring import BalatroScorer
from games.balatro.hand import PokerHand
from games.balatro.card import BalatroCard
from games.balatro.state import BalatroState


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

    # v0.9 folds XMult at its activation boundary so later additive Mult effects
    # preserve real Balatro ordering instead of carrying a deferred x_mult field.
    assert score.mult == 2.0
    assert score.x_mult == 1.0
    assert score.total == 10


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

    assert score.mult == 1.5
    assert score.x_mult == 1.0
    assert score.total == 7


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

    assert score.mult == 1.5
    assert score.x_mult == 1.0
    assert score.total == 7


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
    assert score.mult == 7.5
    assert score.x_mult == 1.0
    assert score.total == 37


def test_planet_level_one_keeps_base_score():

    scorer = BalatroScorer()
    state = BalatroState()

    score = scorer.score(
        PokerHand.PAIR,
        state
    )

    assert score.chips == 10
    assert score.mult == 2


def test_planet_level_two_increases_score():

    scorer = BalatroScorer()
    state = BalatroState()

    state.hand_levels["PAIR"] = 2

    score = scorer.score(
        PokerHand.PAIR,
        state
    )

    assert score.chips == 25
    assert score.mult == 3


def test_planet_level_three_applies_bonus_twice():

    scorer = BalatroScorer()
    state = BalatroState()

    state.hand_levels["PAIR"] = 3

    score = scorer.score(
        PokerHand.PAIR,
        state
    )

    assert score.chips == 40
    assert score.mult == 4


def test_planet_upgrade_only_affects_matching_hand():

    scorer = BalatroScorer()
    state = BalatroState()

    state.hand_levels["PAIR"] = 2

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state
    )

    assert score.chips == 5
    assert score.mult == 1