from __future__ import annotations

"""Opened-pack Emperor expectation from Balatro's public Tarot generation pool.

The Emperor creates up to two Tarot cards in free consumable slots using ordinary
``create_card('Tarot', ..., soulable=nil, key_append='emp')`` semantics. The current
live generation-pool snapshot already reflects held/visible duplicate exclusion,
challenge bans, pool flags, and Showman. No hidden seed, pool order, or generated
identity is read.

When two cards can be generated, this evaluator deliberately values only the better
of the two generated Tarot options. That is a conservative lower bound: it avoids
pretending two future Tarot uses are independent/additive while still recognizing
that Emperor creates real option value. Without Showman the two ordinary draws are
without replacement; with Showman they are with replacement. Balatro's Strength
empty-pool fallback is preserved for the degenerate one-record/two-draw case.
"""

from copy import deepcopy
from itertools import combinations

from games.balatro.actions import SELECT_PACK_CARD, BalatroAction
from games.balatro.live.pack import LivePackChoice
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore


EMPEROR = "The Emperor"
_STRENGTH_RECORD = {
    "center": "c_strength",
    "label": "Strength",
    "ability_name": "Strength",
    "ability_set": "TAROT",
}


class EmperorExpectationEvaluator:
    def __init__(self, *, pack_policy: BalatroPackPolicy) -> None:
        self.pack_policy = pack_policy

    @staticmethod
    def _tarot_pool(state) -> tuple[dict, ...]:
        pools = getattr(state, "consumable_generation_pools", {}) or {}
        values = pools.get("TAROT", ()) if isinstance(pools, dict) else ()
        return tuple(dict(record) for record in values if isinstance(record, dict))

    def _tarot_value(self, state, record: dict) -> float:
        # Under Showman, Emperor can generate another Emperor. Treat that recursive
        # branch as zero rather than recursively inventing an infinite option chain.
        if str(record.get("label") or "") == EMPEROR:
            return 0.0

        data = dict(record)
        if str(data.get("label") or "") == "The Fool":
            # Using Emperor makes Emperor the public last Tarot before generated
            # cards are used, so a generated Fool can copy Emperor.
            data["last_tarot_planet"] = "c_emperor"

        choice = LivePackChoice(area_index=0, address=0, data=data)
        action = BalatroAction(SELECT_PACK_CARD, target=choice)
        projected = deepcopy(state)
        projected.phase = "TAROT_PACK"
        projected.last_tarot_planet = "c_emperor"
        try:
            scored = self.pack_policy.score_action(projected, action)
        except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
            return 0.0
        return max(0.0, float(scored.total))

    def evaluate(self, state) -> tuple[float, tuple[str, ...]]:
        if not bool(getattr(state, "consumable_generation_pool_observed", False)):
            return 0.0, (
                "Emperor deferred: public Tarot generation pool was not observed",
            )

        capacity = max(0, int(getattr(state, "consumable_slots", 0) or 0))
        held = len(getattr(state, "consumables", ()) or ())
        generated_count = min(2, max(0, capacity - held))
        if generated_count <= 0:
            return 0.0, (
                f"Emperor unavailable: no free consumable slot ({held}/{capacity})",
            )

        pool = self._tarot_pool(state)
        if not pool:
            return 0.0, ("Emperor deferred: public Tarot generation pool is empty",)

        values = tuple(self._tarot_value(state, record) for record in pool)
        if generated_count == 1:
            expected = sum(values) / float(len(values))
            return expected, (
                "Emperor creates one Tarot because only one consumable slot is free",
                "generated Tarot value uses current public D9 Tarot authority",
                f"expected generated option value={expected:.6f}",
            )

        showman = bool(getattr(state, "consumable_generation_showman", False))
        if showman:
            maxima = [max(left, right) for left in values for right in values]
            expected = sum(maxima) / float(len(maxima))
            generation_note = "Showman permits the two generated Tarot draws to repeat"
        elif len(values) >= 2:
            maxima = [max(values[i], values[j]) for i, j in combinations(range(len(values)), 2)]
            expected = sum(maxima) / float(len(maxima))
            generation_note = "two generated Tarots use ordinary without-replacement duplicate exclusion"
        else:
            # After the only eligible Tarot is generated, get_current_pool becomes
            # empty and Balatro falls back to Strength for the second creation.
            strength_value = self._tarot_value(state, _STRENGTH_RECORD)
            expected = max(values[0], strength_value)
            generation_note = "second Tarot uses Balatro's Strength empty-pool fallback"

        return expected, (
            "Emperor creates two Tarots into two free consumable slots",
            generation_note,
            "only the better generated Tarot is valued; second-card additive value is omitted conservatively",
            f"expected generated option value={expected:.6f}",
        )


def install_emperor_pack_expectation_policy() -> None:
    if getattr(BalatroPackPolicy, "_emperor_pack_expectation_installed", False):
        return

    original_init = BalatroPackPolicy.__init__
    original_score_consumable = BalatroPackPolicy._score_consumable

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.emperor_expectation_evaluator = EmperorExpectationEvaluator(pack_policy=self)

    def score_consumable(self, state, action, choice):
        if choice.kind != "TAROT" or choice.label != EMPEROR:
            return original_score_consumable(self, state, action, choice)

        expected, notes = self.emperor_expectation_evaluator.evaluate(state)
        if expected <= 0.0:
            return PackActionScore(
                action,
                -1.0,
                ("Emperor does not beat opened-pack Skip=0", *notes),
            )
        return PackActionScore(
            action,
            float(expected),
            (
                "Emperor uses analytic public Tarot-generation expectation",
                *notes,
            ),
        )

    BalatroPackPolicy.__init__ = init
    BalatroPackPolicy._score_consumable = score_consumable
    BalatroPackPolicy.STOCHASTIC_MODELED_TAROTS = frozenset(
        set(BalatroPackPolicy.STOCHASTIC_MODELED_TAROTS) | {EMPEROR}
    )
    BalatroPackPolicy.STOCHASTIC_DEFERRED_TAROTS = frozenset(
        set(BalatroPackPolicy.STOCHASTIC_DEFERRED_TAROTS) - {EMPEROR}
    )
    BalatroPackPolicy._emperor_pack_expectation_installed = True
