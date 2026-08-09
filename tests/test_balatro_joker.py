from games.balatro.jokers.simple import FlatMultJoker
from games.balatro.scoring import BalatroScorer
from games.balatro.hand import PokerHand


def test_flat_mult_joker():

    scorer = BalatroScorer()

    state = type(
        "TestState",
        (),
        {
            "jokers": [
                FlatMultJoker(4)
            ]
        }
    )()

    score = scorer.score(
        PokerHand.PAIR,
        state
    )

    assert score.chips == 10
    assert score.mult == 6
    assert score.total == 60