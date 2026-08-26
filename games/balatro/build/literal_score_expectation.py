from __future__ import annotations

"""Shared literal expected-score helper for build valuation.

D2 must not sample Balatro RNG, but ``resolve_random_effects=False`` is not an
expectation when a scoring Joker is genuinely stochastic. Bloodstone and Misprint
already have finite public-mechanics outcome models in D1, so D2 reuses those only
when such a source is actually present. Deterministic builds stay on the fast literal
scorer, which matters for Blueprint/Brainstorm permutation search. Played-card chips
are always included because candidate/current ratios must use the score Balatro
actually awards.
"""

from copy import deepcopy

from games.balatro.live.final_joker_outcomes import LiveFinalJokerScoreOutcomeModel
from games.balatro.scoring import BalatroScorer


_STOCHASTIC_SCORING_JOKERS = frozenset({"BloodstoneJoker", "MisprintJoker"})
_COPY_JOKERS = frozenset({"BlueprintJoker", "BrainstormJoker"})


def _requires_outcome_model(state) -> bool:
    jokers = tuple(getattr(state, "jokers", ()) or ())
    names = {type(joker).__name__ for joker in jokers}
    if names & _STOCHASTIC_SCORING_JOKERS:
        return True
    # A copy Joker only creates stochastic score when there is a stochastic target
    # in the same roster; the target's presence above is therefore sufficient.
    return False


def _deterministic_literal_score(state, hand, cards, scorer: BalatroScorer) -> float:
    return float(
        scorer.score(
            hand,
            state=deepcopy(state),
            cards=deepcopy(list(cards or ())),
            include_card_chips=True,
            resolve_random_effects=False,
        ).total
    )


def literal_expected_score(
    state,
    hand,
    cards,
    *,
    scorer: BalatroScorer | None = None,
) -> float:
    scorer = scorer or BalatroScorer()
    if not _requires_outcome_model(state):
        return _deterministic_literal_score(state, hand, cards, scorer)

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
    return _deterministic_literal_score(state, hand, cards, scorer)
