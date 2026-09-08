from __future__ import annotations

"""Install structural runtime bounds for SHOP expectation work.

Unopened Arcana/Spectral and future-Tarot expectations are now acyclic in their
base implementations, so this installer no longer monkeypatches D8 outcome scoring.
It retains the independent future-hand budget, same-state memoization, stochastic
held-option guard, bounded future-Joker budget, and late live runtime guards.
"""

from games.balatro.arcana_booster_expectation_policy import ArcanaBoosterExpectationEvaluator
from games.balatro.build.hand_size_opportunity import HandSizeOpportunityEvaluator
from games.balatro.held_consumable_option_policy import (
    HeldConsumableOptionEvaluator,
    HeldConsumableOptionExpectation,
)
from games.balatro.pack_policy import BalatroPackPolicy
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
    from games.balatro.live_competence_guard_policy import install_live_competence_guard_policy

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

    original_held_evaluate = HeldConsumableOptionEvaluator.evaluate

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
                    "actual held/opened use retains full D9 authority when it becomes the real decision",
                    "no future RNG state or generated option identity is predicted",
                ),
            )
        return original_held_evaluate(self, state, candidate)

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
