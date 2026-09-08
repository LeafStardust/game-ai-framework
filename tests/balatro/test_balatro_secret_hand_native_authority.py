from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.hand import PokerHand
from games.balatro.scoring import BalatroScorer


def test_secret_hand_scores_are_native_to_canonical_scorer():
    expected = {
        PokerHand.FIVE_OF_A_KIND: (120, 12),
        PokerHand.FLUSH_HOUSE: (140, 14),
        PokerHand.FLUSH_FIVE: (160, 16),
    }

    for hand, (chips, mult) in expected.items():
        score = BalatroScorer.SCORES[hand]
        assert score.chips == chips
        assert score.mult == mult


def test_secret_hand_probes_are_native_to_b3_evaluator():
    probe_hands = {hand for hand, _ in JokerBuildValueEvaluator.PROBES}

    assert PokerHand.FIVE_OF_A_KIND in probe_hands
    assert PokerHand.FLUSH_HOUSE in probe_hands
    assert PokerHand.FLUSH_FIVE in probe_hands
