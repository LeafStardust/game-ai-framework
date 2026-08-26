from __future__ import annotations

"""Bound recursive unopened-shop expectations without inventing hidden value.

D8 unopened booster value is already a conservative one-offer lower bound. A
hypothetical Arcana/Spectral outcome that itself expands a stochastic or otherwise
deferred D9 model must not recursively solve that second planning problem during
the same SHOP arbitration. Actual opened-pack D9 decisions retain their full models.

Large future-Joker expectations are also kept on a small fully wrapped D2 budget.
Unevaluated public probability mass always contributes zero and is never
renormalized, so every runtime shortcut remains pessimistic rather than optimistic.
"""

from games.balatro.arcana_booster_expectation_policy import ArcanaBoosterExpectationEvaluator
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.spectral_booster_expectation_policy import SpectralBoosterExpectationEvaluator
from games.balatro.standard_booster_expectation_policy import StandardBoosterExpectationEvaluator
import games.balatro.reroll_joker_expectation_policy as reroll_joker_expectation_policy


_NESTED_GENERATED_RESOURCE_TAROTS = frozenset(
    {
        "THE EMPEROR",
        "THE HIGH PRIESTESS",
        "JUDGEMENT",
    }
)
_D8_DEFERRED_SPECTRALS = frozenset(
    str(name).strip().upper() for name in BalatroPackPolicy.DEFERRED_SPECTRALS
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
_D8_OMITTED_SPECTRALS = _D8_DEFERRED_SPECTRALS | _NESTED_GENERATED_RESOURCE_SPECTRALS


def _record_name(record: dict) -> str:
    return str(
        record.get("label")
        or record.get("ability_name")
        or record.get("name")
        or ""
    ).strip().upper()


def _memoize_same_state_evaluate(cls) -> None:
    """Reuse a family expectation when D14 scores duplicate packs in one state."""
    if getattr(cls, "_rw_same_state_expectation_memo_installed", False):
        return
    original_evaluate = cls.evaluate

    def evaluate(self, state):
        cached_state = getattr(self, "_rw_cached_expectation_state", None)
        if cached_state is state:
            return getattr(self, "_rw_cached_expectation_result")
        result = original_evaluate(self, state)
        # Retaining the state reference prevents Python id reuse and naturally
        # invalidates the cache on the next translated BalatroState object.
        self._rw_cached_expectation_state = state
        self._rw_cached_expectation_result = result
        return result

    cls.evaluate = evaluate
    cls._rw_same_state_expectation_memo_installed = True


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
        omitted = (
            name in _NESTED_GENERATED_RESOURCE_TAROTS
            if kind != "SPECTRAL"
            else name in _D8_OMITTED_SPECTRALS
        )
        if omitted:
            # Keep this outcome's real probability mass in the outer mean but do
            # not recursively solve a second stochastic/deferred D9 problem.
            return 0.0
        return float(original_arcana_visible_value(self, state, record))

    def spectral_visible_value(self, state, record: dict) -> float:
        if _record_name(record) in _D8_OMITTED_SPECTRALS:
            return 0.0
        return float(original_spectral_visible_value(self, state, record))

    ArcanaBoosterExpectationEvaluator._visible_value = arcana_visible_value
    SpectralBoosterExpectationEvaluator._visible_value = spectral_visible_value

    # D14 may expose two packs from the same family. Their unopened one-offer
    # expectation depends on the shared current state, not the individual pack
    # identity or price, so compute it once per translated state object.
    for evaluator_cls in (
        ArcanaBoosterExpectationEvaluator,
        SpectralBoosterExpectationEvaluator,
        StandardBoosterExpectationEvaluator,
    ):
        _memoize_same_state_evaluate(evaluator_cls)

    # A 116-Joker live catalogue made even the earlier 48-call bound too slow when
    # recomputed beside Arcana/Buffoon. Small pools remain exact; large pools keep
    # one deterministic public record per rarity and at most twelve fully wrapped
    # D2 calls. Omitted mass still contributes literal zero.
    reroll_joker_expectation_policy._MAX_RECORDS_PER_RARITY = 1
    reroll_joker_expectation_policy._MAX_D2_EVALUATIONS = 12

    ArcanaBoosterExpectationEvaluator._rw_one_step_expectation_installed = True
    SpectralBoosterExpectationEvaluator._rw_one_step_expectation_installed = True
    StandardBoosterExpectationEvaluator._rw_one_step_expectation_installed = True
