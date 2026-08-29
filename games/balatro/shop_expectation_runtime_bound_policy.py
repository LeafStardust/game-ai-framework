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
* parent-driven D11 reroll comparison does not recompute diagnostic BuildProfiler
  state after D14 has already supplied the authoritative visible-score floor;
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
from games.balatro.shop_reroll_policy import BuildAwareShopRerollPolicy
from games.balatro.shop_runtime_contract_policy import install_shop_runtime_contract_policy
from games.balatro.spectral_booster_expectation_policy import SpectralBoosterExpectationEvaluator
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
_SHOP_SPECTRAL_SPECIAL_PROBABILITY = 0.003


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
    # Import only when this late production/runtime installer is executed. Keeping
    # the competence guard out of package-level import surfaces avoids the partially
    # initialized games.balatro collection failure repaired in the same branch.
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
    original_reroll_unmet_requirements = BuildAwareShopRerollPolicy._unmet_requirements

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
        """One-record conservative lower bound for unopened SHOP Spectral value.

        The full public eligible catalogue remains the probability denominator, but
        only one deterministic spread record is sent through D9. Every omitted
        ordinary outcome contributes literal zero. If a 0.3% soulable special is
        currently available, that special branch is also conservatively valued at
        zero in unopened SHOP expectation; the actual opened-pack D9 decision remains
        exact when the identity becomes visible.
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

        special_available = bool(
            getattr(state, "black_hole_generation_available", False)
            or getattr(state, "soul_generation_available", False)
        )
        if special_available:
            ordinary_mass = 1.0 - _SHOP_SPECTRAL_SPECIAL_PROBABILITY
            option_ev = ordinary_mass * ordinary_ev
            positive = ordinary_mass * ordinary_positive
            special_note = (
                "soulable 0.3% special branch omitted conservatively at value zero in SHOP"
            )
        else:
            option_ev = ordinary_ev
            positive = ordinary_positive
            special_note = "soulable special override unavailable in current public state"

        return option_ev, positive, (
            "Spectral SHOP expectation uses the authoritative public eligible catalogue",
            f"bounded D9 records evaluated={len(selected)}/{len(records)}",
            "unevaluated public ordinary probability mass contributes zero",
            special_note,
            f"one-offer positive-choice probability={positive:.6f}",
            f"one-offer sunk-cost option EV={option_ev:.6f}",
            "actual opened-pack D9 remains authoritative after an identity is visible",
            "best-of-2/4 and Mega second-selection improvement omitted conservatively",
        )

    def reroll_unmet_requirements(self, state):
        # In the live D14 path these requirements are diagnostic metadata only; they
        # do not participate in reroll EV, legality, stop-loss, or parent comparison.
        # Re-running the fully wrapped BuildProfiler here produced a 181-second
        # outlier after D14 had already computed the authoritative visible floor.
        # Runtime D11 therefore omits this redundant diagnostic pass entirely.
        del self, state
        return ()

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
    BuildAwareShopRerollPolicy._unmet_requirements = reroll_unmet_requirements
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
    BuildAwareShopRerollPolicy._rw_runtime_unmet_requirements_omitted = True
