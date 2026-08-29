from __future__ import annotations

"""Bound recursive SHOP expectations without inventing hidden value.

The runtime contract is deliberately structural rather than Joker/card-specific:

* unopened D8 Arcana/Spectral value may inspect a tightly bounded hypothetical
  visible outcome set, while omitted public probability mass retains value 0;
* stochastic/deferred D9 outcomes keep their real probability mass at value 0
  instead of recursively opening another expectation problem;
* SHOP acquisition value for a held Tarot/Spectral follows the same one-layer rule;
* future-hand option models use a small deterministic draw budget rather than up to
  128 exact hands or 24 sampled hands followed by full legal-play enumeration;
* duplicate same-family unopened-pack expectations are memoized per translated
  SHOP state;
* large future-Joker expectations retain a bounded build-transition budget;
* parent-driven D11 reroll comparison skips redundant BuildProfiler work inside
  D11 itself while standalone D11 keeps its reporting contract;
* the final SHOP runtime contract disables nested D1 Build Health projections and
  the retired named two-Joker bundle override.

Actual opened-pack D9 decisions, real D1 gameplay search, native legality and final
stale-state guards remain unchanged. Omitted probability is never renormalized, so
all shortcuts are conservative lower bounds and never synthetic optimism.
"""

from games.balatro.arcana_booster_expectation_policy import ArcanaBoosterExpectationEvaluator
from games.balatro.build.hand_size_opportunity import HandSizeOpportunityEvaluator
from games.balatro.build.judgement_expectation import _bounded_indices
from games.balatro.held_consumable_option_policy import (
    HeldConsumableOptionEvaluator,
    HeldConsumableOptionExpectation,
)
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.shop_runtime_contract_policy import install_shop_runtime_contract_policy
from games.balatro.spectral_booster_expectation_policy import (
    SpectralBoosterExpectationEvaluator,
    _BLACK_HOLE_RECORD,
    _SOUL_PROBABILITY,
    _SOUL_RECORD,
)
from games.balatro.standard_booster_expectation_policy import StandardBoosterExpectationEvaluator
import games.balatro.reroll_joker_expectation_policy as reroll_joker_expectation_policy


_D8_OMITTED_TAROTS = frozenset(
    str(name).strip().upper()
    for name in (
        set(BalatroPackPolicy.STOCHASTIC_MODELED_TAROTS)
        | set(BalatroPackPolicy.STOCHASTIC_DEFERRED_TAROTS)
    )
)
_D8_OMITTED_SPECTRALS = frozenset(
    str(name).strip().upper()
    for name in (
        set(BalatroPackPolicy.STOCHASTIC_MODELED_SPECTRALS)
        | set(BalatroPackPolicy.DEFERRED_SPECTRALS)
    )
)

_SHOP_FUTURE_HAND_EXACT_LIMIT = 16
_SHOP_FUTURE_HAND_SAMPLE_COUNT = 8
_SHOP_SPECTRAL_RECORD_BUDGET = 1


def _record_name(record: dict) -> str:
    return str(
        record.get("label")
        or record.get("ability_name")
        or record.get("name")
        or ""
    ).strip().upper()


def _memoize_same_state_evaluate(cls) -> None:
    if getattr(cls, "_rw_same_state_expectation_memo_installed", False):
        return
    original_evaluate = cls.evaluate

    def evaluate(self, state):
        cached_state = getattr(self, "_rw_cached_expectation_state", None)
        if cached_state is state:
            return getattr(self, "_rw_cached_expectation_result")
        result = original_evaluate(self, state)
        self._rw_cached_expectation_state = state
        self._rw_cached_expectation_result = result
        return result

    cls.evaluate = evaluate
    cls._rw_same_state_expectation_memo_installed = True


def _install_late_live_guards() -> None:
    from games.balatro.live_competence_guard_policy import (
        install_live_competence_guard_policy,
    )

    install_shop_runtime_contract_policy()
    install_live_competence_guard_policy()


def install_shop_expectation_runtime_bounds() -> None:
    if getattr(
        ArcanaBoosterExpectationEvaluator,
        "_rw_one_step_expectation_installed",
        False,
    ):
        _install_late_live_guards()
        return

    original_arcana_visible_value = ArcanaBoosterExpectationEvaluator._visible_value
    original_spectral_visible_value = SpectralBoosterExpectationEvaluator._visible_value
    original_held_evaluate = HeldConsumableOptionEvaluator.evaluate

    def arcana_visible_value(self, state, record: dict) -> float:
        name = _record_name(record)
        kind = str(record.get("ability_set") or record.get("set") or "TAROT").upper()
        omitted = (
            name in _D8_OMITTED_SPECTRALS
            if kind == "SPECTRAL"
            else name in _D8_OMITTED_TAROTS
        )
        if omitted:
            return 0.0
        return float(original_arcana_visible_value(self, state, record))

    def spectral_visible_value(self, state, record: dict) -> float:
        if _record_name(record) in _D8_OMITTED_SPECTRALS:
            return 0.0
        return float(original_spectral_visible_value(self, state, record))

    def spectral_evaluate(self, state):
        """Bound unopened SHOP Spectral value to at most two D9 calls.

        One deterministic ordinary public record is evaluated and the full ordinary
        pool remains the denominator. If Balatro's public state says the 0.3% Soul /
        Black Hole override is currently available, that single special branch is
        evaluated as one additional bounded call. Omitted ordinary mass stays zero.
        """
        if not bool(getattr(state, "consumable_generation_pool_observed", False)):
            return 0.0, 0.0, (
                "Spectral expectation unavailable: public generation pools were not observed",
            )

        records = self._pool(state)
        if not records:
            return 0.0, 0.0, ("Spectral public generation pool is empty",)

        selected = _bounded_indices(len(records), _SHOP_SPECTRAL_RECORD_BUDGET)
        value_sum = 0.0
        positive_count = 0
        for index in selected:
            value = float(self._visible_value(state, records[index]))
            value_sum += value
            if value > 0.0:
                positive_count += 1

        denominator = float(len(records))
        ordinary_ev = value_sum / denominator
        ordinary_positive = float(positive_count) / denominator

        special = None
        if bool(getattr(state, "black_hole_generation_available", False)):
            special = _BLACK_HOLE_RECORD
        elif bool(getattr(state, "soul_generation_available", False)):
            special = _SOUL_RECORD

        if special is None:
            option_ev = ordinary_ev
            positive = ordinary_positive
            special_note = "soulable special override unavailable in current public state"
            special_calls = 0
        else:
            special_value = float(self._visible_value(state, special))
            option_ev = (
                (1.0 - _SOUL_PROBABILITY) * ordinary_ev
                + _SOUL_PROBABILITY * special_value
            )
            positive = (
                (1.0 - _SOUL_PROBABILITY) * ordinary_positive
                + _SOUL_PROBABILITY * (1.0 if special_value > 0.0 else 0.0)
            )
            special_note = "soulable 0.3% special override evaluated as one bounded D9 branch"
            special_calls = 1

        return option_ev, positive, (
            "Spectral one-offer EV uses current public eligible get_current_pool catalogue",
            f"bounded ordinary D9 records evaluated={len(selected)}/{len(records)}",
            f"bounded special D9 records evaluated={special_calls}/1",
            "unevaluated public ordinary probability mass contributes zero",
            special_note,
            f"one-offer positive-choice probability={positive:.6f}",
            f"one-offer sunk-cost option EV={option_ev:.6f}",
            "actual opened-pack D9 remains authoritative after an identity is visible",
            "best-of-2/4 and Mega second-selection improvement omitted conservatively",
        )

    def held_evaluate(self, state, candidate):
        category = str(getattr(candidate, "category", "") or "").upper()
        name = str(getattr(candidate, "name", "") or "").strip().upper()
        omitted = (
            category == "TAROT" and name in _D8_OMITTED_TAROTS
        ) or (
            category == "SPECTRAL" and name in _D8_OMITTED_SPECTRALS
        )
        if omitted:
            return HeldConsumableOptionExpectation(
                complete=True,
                expected_gain=0.0,
                exact=False,
                rationale=(
                    "SHOP future-use option keeps stochastic/deferred second-layer probability at zero",
                    "actual held/opened use retains the full D9 model when it becomes the real decision",
                    "no future RNG state or generated option identity is predicted",
                ),
            )
        return original_held_evaluate(self, state, candidate)

    ArcanaBoosterExpectationEvaluator._visible_value = arcana_visible_value
    SpectralBoosterExpectationEvaluator._visible_value = spectral_visible_value
    SpectralBoosterExpectationEvaluator.evaluate = spectral_evaluate
    HeldConsumableOptionEvaluator.evaluate = held_evaluate

    for evaluator_cls in (
        ArcanaBoosterExpectationEvaluator,
        SpectralBoosterExpectationEvaluator,
        StandardBoosterExpectationEvaluator,
    ):
        _memoize_same_state_evaluate(evaluator_cls)

    HeldConsumableOptionEvaluator.EXACT_COMBINATION_LIMIT = _SHOP_FUTURE_HAND_EXACT_LIMIT
    HeldConsumableOptionEvaluator.SAMPLE_COUNT = _SHOP_FUTURE_HAND_SAMPLE_COUNT
    HandSizeOpportunityEvaluator.EXACT_COMBINATION_LIMIT = _SHOP_FUTURE_HAND_EXACT_LIMIT
    HandSizeOpportunityEvaluator.SAMPLE_COUNT = _SHOP_FUTURE_HAND_SAMPLE_COUNT

    reroll_joker_expectation_policy._MAX_RECORDS_PER_RARITY = 1
    reroll_joker_expectation_policy._MAX_D2_EVALUATIONS = 12

    _install_late_live_guards()

    ArcanaBoosterExpectationEvaluator._rw_one_step_expectation_installed = True
    SpectralBoosterExpectationEvaluator._rw_one_step_expectation_installed = True
    StandardBoosterExpectationEvaluator._rw_one_step_expectation_installed = True
    HeldConsumableOptionEvaluator._rw_one_step_expectation_installed = True
