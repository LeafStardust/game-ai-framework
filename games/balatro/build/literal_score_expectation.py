from __future__ import annotations

"""Shared literal expected-score helper for build valuation.

D2 must not sample Balatro RNG, but ``resolve_random_effects=False`` is not an
expectation: it turns Bloodstone/Misprint/Lucky branches into deterministic misses.
The live score-outcome model already enumerates those public-mechanics branches.
This helper reuses that model for representative build probes and falls back to the
ordinary literal scorer only when a legacy/manual state contains an unsupported
projection. Played-card chips are always included because candidate/current ratios
must use the score Balatro actually awards.
"""

from copy import deepcopy

from games.balatro.live.final_joker_outcomes import LiveFinalJokerScoreOutcomeModel
from games.balatro.scoring import BalatroScorer


def literal_expected_score(
    state,
    hand,
    cards,
    *,
    scorer: BalatroScorer | None = None,
) -> float:
    scorer = scorer or BalatroScorer()
    model = LiveFinalJokerScoreOutcomeModel()
    try:
        transition = model.project_transition(
            hand,
            deepcopy(state),
            deepcopy(list(cards or ())),
            include_card_chips=True,
        )
    except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
        transition = None

    if transition is not None and transition.joker_projection_complete:
        return float(transition.distribution.expected)

    # Legacy/manual states may omit public fields required by the final D1
    # projector. Keep D2 usable while remaining deterministic; no stochastic
    # branch is invented in this fallback.
    return float(
        scorer.score(
            hand,
            state=deepcopy(state),
            cards=deepcopy(list(cards or ())),
            include_card_chips=True,
            resolve_random_effects=False,
        ).total
    )
