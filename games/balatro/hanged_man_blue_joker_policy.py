from __future__ import annotations

"""Let Hanged Man trade deck quality against Blue Joker's exact deck-size cost.

The live pack generator historically removed Hanged Man from the action set whenever
Blue Joker was owned. That hard veto is mechanically too strong: destroying weak
cards can still improve a deck enough to justify losing Blue Joker Chips.

B6's intrinsic card scale already normalizes ordinary playing-card Chips at 0.01 per
Chip. Blue Joker contributes exactly +2 Chips per card remaining in deck, so one
permanently removed card costs 0.02 on that same existing local scale for each active
Blue Joker. This policy subtracts only that mechanically derived cost and leaves the
existing intrinsic/contextual thinning evaluation otherwise unchanged.
"""

from dataclasses import replace

from games.balatro.build.consumable_targeting import ContextualConsumableTargetEvaluator


_BLUE_JOKER_CHIPS_PER_CARD = 2.0
_B6_CHIP_SCALE = 0.01


def _active_blue_jokers(state) -> int:
    return sum(
        1
        for joker in tuple(getattr(state, "jokers", ()) or ())
        if type(joker).__name__ == "BlueJoker"
        and not bool(getattr(joker, "debuffed", False))
    )


def install_hanged_man_blue_joker_policy() -> None:
    if getattr(
        ContextualConsumableTargetEvaluator,
        "_hanged_man_blue_joker_cost_installed",
        False,
    ):
        return

    original = ContextualConsumableTargetEvaluator._rank_hanged_man_targets

    def rank_hanged_man_targets(self, state, consumable):
        ranked = tuple(original(self, state, consumable))
        blue_count = _active_blue_jokers(state)
        if blue_count <= 0:
            return ranked

        adjusted = []
        for evaluation in ranked:
            removed = len(tuple(getattr(evaluation, "cards", ()) or ()))
            blue_cost = (
                float(removed)
                * float(blue_count)
                * _BLUE_JOKER_CHIPS_PER_CARD
                * _B6_CHIP_SCALE
            )
            adjusted.append(
                replace(
                    evaluation,
                    total_gain=float(evaluation.total_gain) - blue_cost,
                    rationale=(
                        *tuple(evaluation.rationale),
                        f"Blue Joker deck-size cost: {removed} removed x {blue_count} active x 2 Chips = {removed * blue_count * 2} Chips",
                        f"B6 chip-normalized Blue Joker opportunity cost=-{blue_cost:.3f}",
                        "Hanged Man remains admissible only when net target value stays positive",
                    ),
                )
            )

        return self._sorted(adjusted)

    ContextualConsumableTargetEvaluator._rank_hanged_man_targets = rank_hanged_man_targets
    ContextualConsumableTargetEvaluator._hanged_man_blue_joker_cost_installed = True
