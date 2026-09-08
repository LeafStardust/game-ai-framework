from __future__ import annotations

from dataclasses import replace

from games.balatro.live.hand_decision import LiveHandDecisionEvaluator


class CeruleanBellHandDecisionEvaluator(LiveHandDecisionEvaluator):
    """Keep Cerulean Bell exact at authoritative live checkpoints.

    The production observer hydrates the card Balatro has already forced. After a
    hypothetical redraw the game chooses a new card with hidden RNG. Until the D1
    redraw layer owns that post-draw choice directly, mark such deeper projections
    incomplete instead of silently claiming exactness.
    """

    UNSUPPORTED = "BossBlind:Cerulean Bell future forced selection"

    def project_play(self, state, action):
        projection = super().project_play(state, action)
        if any(
            bool(getattr(card, "forced_selection", False))
            for card in getattr(state, "hand", [])
        ):
            return projection

        unsupported = tuple(
            dict.fromkeys((*projection.unsupported_jokers, self.UNSUPPORTED))
        )
        return replace(
            projection,
            joker_projection_complete=False,
            unsupported_jokers=unsupported,
        )
