from __future__ import annotations

"""Use next-round discard allowance for Banner-involved shop valuation.

Banner scores +30 Chips per discard remaining. During SHOP the live state's
``discards_remaining`` is the leftover amount from the blind that just ended, not
the allowance the acquired build will start the next blind with. This can make
Banner itself, or another Joker that multiplies an existing Banner, look arbitrarily
weak/strong depending on how many discards happened to be spent last round.

When the authoritative public reset allowance is observed, project that allowance
for D2's representative shop probes. The ordinary scorer remains the score authority;
this policy changes only the temporal state fed into it.
"""

import copy

from games.balatro.build.joker_strategy import JokerBuildValueEvaluator


def _is_banner(joker: object) -> bool:
    return type(joker).__name__ == "BannerJoker"


def install_banner_candidate_value_policy() -> None:
    if getattr(JokerBuildValueEvaluator, "_banner_candidate_value_installed", False):
        return

    original = JokerBuildValueEvaluator._direct_scoring_gain

    def direct_scoring_gain(self, state, joker):
        if str(getattr(state, "phase", "")) != "SHOP":
            return original(self, state, joker)
        if not bool(getattr(state, "round_reset_discards_observed", False)):
            return original(self, state, joker)
        if not (
            _is_banner(joker)
            or any(_is_banner(value) for value in tuple(getattr(state, "jokers", ()) or ()))
        ):
            return original(self, state, joker)

        projected = copy.deepcopy(state)
        projected.discards_remaining = max(
            0,
            int(getattr(state, "round_reset_discards", 0) or 0),
        )
        return original(self, projected, joker)

    JokerBuildValueEvaluator._direct_scoring_gain = direct_scoring_gain
    JokerBuildValueEvaluator._banner_candidate_value_installed = True
