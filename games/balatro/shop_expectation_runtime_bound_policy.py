from __future__ import annotations

"""Bound recursive unopened-shop expectations without inventing hidden value.

D8 unopened booster value is already a conservative one-offer lower bound.  A
hypothetical Arcana/Spectral outcome that itself generates another random option
pool must not recursively expand that second pool during the same SHOP arbitration.
Actual opened-pack D9 decisions retain their full generated-resource models.

Large future-Joker expectations are also kept on a small fully wrapped D2 budget.
Unevaluated public probability mass always contributes zero and is never
renormalized, so every runtime shortcut remains pessimistic rather than optimistic.
"""

from games.balatro.arcana_booster_expectation_policy import ArcanaBoosterExpectationEvaluator
from games.balatro.spectral_booster_expectation_policy import SpectralBoosterExpectationEvaluator
import games.balatro.reroll_joker_expectation_policy as reroll_joker_expectation_policy


_NESTED_GENERATED_RESOURCE_TAROTS = frozenset(
    {
        "THE EMPEROR",
        "THE HIGH PRIESTESS",
        "JUDGEMENT",
    }
)
_NESTED_GENERATED_RESOURCE_SPECTRALS = frozenset(
    {
        "FAMILIAR",
        "GRIM",
        "INCANTATION",
        "WRAITH",
        "THE SOUL",
    }
)


def _record_name(record: dict) -> str:
    return str(
        record.get("label")
        or record.get("ability_name")
        or record.get("name")
        or ""
    ).strip().upper()


def install_shop_expectation_runtime_bounds() -> None:
    if getattr(
        ArcanaBoosterExpectationEvaluator,
        "_rw_one_step_expectation_installed",
        False,
    ):
        return

    original_arcana_visible_value = ArcanaBoosterExpectationEvaluator._visible_value
    original_spectral_visible_value = SpectralBoosterExpectationEvaluator._visible_value

    def arcana_visible_value(self, state, record: dict) -> float:
        name = _record_name(record)
        kind = str(record.get("ability_set") or record.get("set") or "TAROT").upper()
        nested = (
            name in _NESTED_GENERATED_RESOURCE_TAROTS
            if kind != "SPECTRAL"
            else name in _NESTED_GENERATED_RESOURCE_SPECTRALS
        )
        if nested:
            # Keep this outcome's real probability mass in the outer mean but do
            # not recursively synthesize a second random option pool.
            return 0.0
        return float(original_arcana_visible_value(self, state, record))

    def spectral_visible_value(self, state, record: dict) -> float:
        if _record_name(record) in _NESTED_GENERATED_RESOURCE_SPECTRALS:
            return 0.0
        return float(original_spectral_visible_value(self, state, record))

    ArcanaBoosterExpectationEvaluator._visible_value = arcana_visible_value
    SpectralBoosterExpectationEvaluator._visible_value = spectral_visible_value

    # A 116-Joker live catalogue made even the earlier 48-call bound too slow when
    # recomputed beside Arcana/Buffoon.  Small pools remain exact; large pools keep
    # one deterministic public record per rarity and at most twelve fully wrapped
    # D2 calls.  Omitted mass still contributes literal zero.
    reroll_joker_expectation_policy._MAX_RECORDS_PER_RARITY = 1
    reroll_joker_expectation_policy._MAX_D2_EVALUATIONS = 12

    ArcanaBoosterExpectationEvaluator._rw_one_step_expectation_installed = True
    SpectralBoosterExpectationEvaluator._rw_one_step_expectation_installed = True
