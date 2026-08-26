from __future__ import annotations

"""Make secret poker hands first-class literal scoring/probe authorities.

The live final-score stack already knew Balatro's base scores for Five of a Kind,
Flush House, and Flush Five, but the shared ``BalatroScorer`` and D2 Joker build
probes stopped at Straight Flush.  Once a run has actually unlocked and played a
secret hand, shop candidate/current-build valuation must not silently ignore that
hand type.

This installer adds the exact vanilla base scores to the shared scorer and extends
D2's representative hand catalogue.  Observed hand-play counts remain authoritative
for weighting, so secret-hand probes carry only the small prior weight until the run
actually demonstrates that hand.
"""

from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.scoring import BalatroScorer, HandScore
from games.balatro.build.joker_strategy import JokerBuildValueEvaluator


_SECRET_SCORES = {
    PokerHand.FIVE_OF_A_KIND: HandScore(120, 12),
    PokerHand.FLUSH_HOUSE: HandScore(140, 14),
    PokerHand.FLUSH_FIVE: HandScore(160, 16),
}

_SECRET_PROBES = (
    (
        PokerHand.FIVE_OF_A_KIND,
        (
            BalatroCard("A", "Hearts"),
            BalatroCard("A", "Spades"),
            BalatroCard("A", "Clubs"),
            BalatroCard("A", "Diamonds"),
            BalatroCard("A", "Hearts"),
        ),
    ),
    (
        PokerHand.FLUSH_HOUSE,
        (
            BalatroCard("K", "Hearts"),
            BalatroCard("K", "Hearts"),
            BalatroCard("K", "Hearts"),
            BalatroCard("8", "Hearts"),
            BalatroCard("8", "Hearts"),
        ),
    ),
    (
        PokerHand.FLUSH_FIVE,
        (
            BalatroCard("A", "Hearts"),
            BalatroCard("A", "Hearts"),
            BalatroCard("A", "Hearts"),
            BalatroCard("A", "Hearts"),
            BalatroCard("A", "Hearts"),
        ),
    ),
)


def install_secret_hand_score_authority() -> None:
    if getattr(JokerBuildValueEvaluator, "_secret_hand_score_authority_installed", False):
        return

    BalatroScorer.SCORES = {
        **BalatroScorer.SCORES,
        **_SECRET_SCORES,
    }

    existing = {hand for hand, _ in JokerBuildValueEvaluator.PROBES}
    JokerBuildValueEvaluator.PROBES = (
        *JokerBuildValueEvaluator.PROBES,
        *(probe for probe in _SECRET_PROBES if probe[0] not in existing),
    )
    JokerBuildValueEvaluator._secret_hand_score_authority_installed = True
