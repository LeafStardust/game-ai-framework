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

The same installer also repairs held-Hanged-Man simulation after permanent card
destruction was centralized. ``HangedMan.use`` already applies the shared permanent
destruction transition, including owned-deck removal and destruction-triggered Joker
state. The old timing simulator then attempted to remove the same owned cards a
second time and failed every otherwise-valid simulation. Hanged Man now validates
owned live-id uniqueness before use, applies the shared transition exactly once, and
fails closed on ambiguous/missing authoritative identities.
"""

import copy
from dataclasses import replace

from games.balatro.build.consumable_targeting import ContextualConsumableTargetEvaluator
from games.balatro.consumable import ConsumableContext
from games.balatro.live.consumable_timing_base import LiveConsumableTimingPolicy


_BLUE_JOKER_CHIPS_PER_CARD = 2.0
_B6_CHIP_SCALE = 0.01


def _active_blue_jokers(state) -> int:
    return sum(
        1
        for joker in tuple(getattr(state, "jokers", ()) or ())
        if type(joker).__name__ == "BlueJoker"
        and not bool(getattr(joker, "debuffed", False))
    )


def _owned_targets_are_unambiguous(state, cards) -> bool:
    owned = tuple(getattr(state, "owned_deck", ()) or ())
    if getattr(state, "owned_deck", None) is None:
        return False
    for card in tuple(cards or ()):
        live_id = getattr(card, "live_id", None)
        if live_id is None:
            return False
        matches = sum(
            getattr(candidate, "live_id", None) == live_id
            for candidate in owned
        )
        if matches != 1:
            return False
    return True


def install_hanged_man_blue_joker_policy() -> None:
    if not getattr(
        ContextualConsumableTargetEvaluator,
        "_hanged_man_blue_joker_cost_installed",
        False,
    ):
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

    if getattr(
        LiveConsumableTimingPolicy,
        "_hanged_man_single_destruction_simulation_installed",
        False,
    ):
        return

    original_simulate_use = LiveConsumableTimingPolicy._simulate_use

    def simulate_use(self, state, *, consumable_index: int, target_indices: tuple[int, ...]):
        simulated = copy.deepcopy(state)
        if not (0 <= consumable_index < len(simulated.consumables)):
            return None
        if any(index < 0 or index >= len(simulated.hand) for index in target_indices):
            return None

        consumable = simulated.consumables[consumable_index]
        if str(getattr(consumable, "name", "")) != "The Hanged Man":
            return original_simulate_use(
                self,
                state,
                consumable_index=consumable_index,
                target_indices=target_indices,
            )

        cards = [simulated.hand[index] for index in target_indices]
        if not _owned_targets_are_unambiguous(simulated, cards):
            return None

        context = ConsumableContext(state=simulated, cards=cards)
        if not consumable.can_use(context):
            return None

        # HangedMan.use owns the one canonical permanent-destruction transition.
        consumable.use(context)

        destroyed_ids = {id(card) for card in cards}
        simulated.discard_pile = [
            card
            for card in getattr(simulated, "discard_pile", ())
            if id(card) not in destroyed_ids
        ]
        simulated.consumables.pop(consumable_index)
        return simulated

    LiveConsumableTimingPolicy._simulate_use = simulate_use
    LiveConsumableTimingPolicy._hanged_man_single_destruction_simulation_installed = True
