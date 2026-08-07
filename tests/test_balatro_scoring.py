from games.balatro.scoring import BalatroScorer
from games.balatro.hand import PokerHand


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