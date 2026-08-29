from __future__ import annotations

"""Opened-pack Emperor expectation from Balatro's public Tarot generation pool.

Emperor itself is a visible D9 choice, but the hypothetical Tarots it can generate
must not be sent back through D9. Generated outcomes therefore use the same bounded,
acyclic leaf valuation used by unopened D8 boosters. Unsupported/generative outcomes
contribute zero. The model remains a conservative lower bound.
"""

from itertools import combinations

from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore
from games.balatro.unopened_consumable_outcome_value import (
    UnopenedConsumableOutcomeValueEvaluator,
)


EMPEROR = "The Emperor"
_MAX_EXACT_PUBLIC_RECORDS = 12
_MAX_EVALUATED_RECORDS_LARGE_POOL = 8
_STRENGTH_RECORD = {
    "center": "c_strength",
    "label": "Strength",
    "ability_name": "Strength",
    "ability_set": "TAROT",
}


def _bounded_indices(record_count: int) -> tuple[int, ...]:
    if record_count <= 0:
        return ()
    if record_count <= _MAX_EXACT_PUBLIC_RECORDS:
        return tuple(range(record_count))
    target = min(record_count, _MAX_EVALUATED_RECORDS_LARGE_POOL)
    if target <= 1:
        return (0,)
    selected = {
        round(position * (record_count - 1) / float(target - 1))
        for position in range(target)
    }
    if len(selected) < target:
        selected.update(index for index in range(record_count) if index not in selected)
    return tuple(sorted(selected)[:target])


class EmperorExpectationEvaluator:
    def __init__(self, *, outcome_evaluator=None) -> None:
        self.outcome_evaluator = outcome_evaluator or UnopenedConsumableOutcomeValueEvaluator()

    @staticmethod
    def _tarot_pool(state) -> tuple[dict, ...]:
        pools = getattr(state, "consumable_generation_pools", {}) or {}
        values = pools.get("TAROT", ()) if isinstance(pools, dict) else ()
        return tuple(dict(record) for record in values if isinstance(record, dict))

    def _tarot_value(self, state, record: dict) -> float:
        data = dict(record)
        if str(data.get("label") or "") == "The Fool":
            data["last_tarot_planet"] = "c_emperor"
        try:
            result = self.outcome_evaluator.evaluate(state, data, kind="TAROT")
        except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
            return 0.0
        return max(0.0, float(result.value))

    def evaluate(self, state) -> tuple[float, tuple[str, ...]]:
        if not bool(getattr(state, "consumable_generation_pool_observed", False)):
            return 0.0, ("Emperor deferred: public Tarot generation pool was not observed",)

        capacity = max(0, int(getattr(state, "consumable_slots", 0) or 0))
        held = len(getattr(state, "consumables", ()) or ())
        generated_count = min(2, max(0, capacity - held))
        if generated_count <= 0:
            return 0.0, (f"Emperor unavailable: no free consumable slot ({held}/{capacity})",)

        pool = self._tarot_pool(state)
        if not pool:
            return 0.0, ("Emperor deferred: public Tarot generation pool is empty",)

        indices = _bounded_indices(len(pool))
        sampled_values = tuple(self._tarot_value(state, pool[index]) for index in indices)
        full_count = len(pool)
        if generated_count == 1:
            expected = sum(sampled_values) / float(full_count)
            return expected, (
                "Emperor creates one Tarot because only one consumable slot is free",
                "generated Tarot outcomes use bounded acyclic leaf valuation, not D9",
                f"Tarot outcomes evaluated={len(indices)}/{full_count}; omitted/deferred mass remains zero",
                f"expected generated option value={expected:.6f}",
            )

        # For a bounded subset, omitted public-pool outcomes are explicit zero values.
        values = list(sampled_values) + [0.0] * max(0, full_count - len(sampled_values))
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
            strength_value = self._tarot_value(state, _STRENGTH_RECORD)
            expected = max(values[0], strength_value)
            generation_note = "second Tarot uses Balatro's Strength empty-pool fallback"

        return expected, (
            "Emperor creates two Tarots into two free consumable slots",
            generation_note,
            "generated Tarot outcomes use bounded acyclic leaf valuation, not D9",
            f"Tarot outcomes evaluated={len(indices)}/{full_count}; omitted/deferred mass remains zero",
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
        self.emperor_expectation_evaluator = EmperorExpectationEvaluator()

    def score_consumable(self, state, action, choice):
        if choice.kind != "TAROT" or choice.label != EMPEROR:
            return original_score_consumable(self, state, action, choice)

        expected, notes = self.emperor_expectation_evaluator.evaluate(state)
        if expected <= 0.0:
            return PackActionScore(action, -1.0, ("Emperor does not beat opened-pack Skip=0", *notes))
        return PackActionScore(
            action,
            float(expected),
            ("Emperor uses bounded public Tarot-generation expectation", *notes),
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
