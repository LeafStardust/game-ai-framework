from __future__ import annotations

"""Bound recursive SHOP expectations without inventing hidden value.

The runtime contract is deliberately structural rather than Joker/card-specific:

* unopened D8 Arcana may inspect a tightly bounded hypothetical visible outcome set,
  while omitted public probability mass retains value 0;
* unopened D8 Spectral never enters D9: only explicit non-recursive public values
  for Black Hole and The Soul are admitted, while every other hypothetical outcome
  retains value 0 until it is actually visible;
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
# Existing explicit B4 Spectral base value. Using the established constant rather
# than D9 keeps unopened SHOP expectation non-recursive.
_SHOP_BLACK_HOLE_VALUE = 4.0


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


def _spectral_unopened_public_value(state, record: dict) -> float:
    """Return a non-recursive public lower-bound value for unopened Spectral D8.

    Only effects with an already-explicit constant public value are admitted here.
    Everything else remains zero until the real opened-pack D9 decision exposes the
    identity and can evaluate its actual state/target semantics.
    """
    name = _record_name(record)
    if name == "BLACK HOLE":
        return _SHOP_BLACK_HOLE_VALUE
    if name == "THE SOUL":
        joker_slots = max(0, int(getattr(state, "joker_slots", 5) or 5))
        owned_jokers = len(getattr(state, "jokers", ()) or ())
        if owned_jokers >= joker_slots:
            return 0.0
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        early_bonus = max(
            0,
            BalatroPackPolicy.SOUL_EARLY_ANTE_CUTOFF - ante,
        ) * BalatroPackPolicy.SOUL_EARLY_ANTE_BONUS
        return float(BalatroPackPolicy.SOUL_BASE_VALUE) + float(early_bonus)
    return 0.0


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
        """Evaluate unopened SHOP Spectral value without entering D9 at all."""
        if not bool(getattr(state, "consumable_generation_pool_observed", False)):
            return 0.0, 0.0, (
                "Spectral expectation unavailable: public generation pools were not observed",
            )

        records = self._pool(state)
        if not records:
            return 0.0, 0.0, ("Spectral public generation pool is empty",)

        # This loop is intentionally over the full public pool because the operation
        # is now constant-time per record: no factory, target search, D9, D2, or D1.
        ordinary_values = tuple(
            _spectral_unopened_public_value(state, record)
            for record in records
        )
        ordinary_ev = sum(ordinary_values) / float(len(ordinary_values))
        ordinary_positive = (
            sum(1 for value in ordinary_values if value > 0.0)
            / float(len(ordinary_values))
        )

        special = None
        if bool(getattr(state, "black_hole_generation_available", False)):
            special = _BLACK_HOLE_RECORD
        elif bool(getattr(state, "soul_generation_available", False)):
            special = _SOUL_RECORD

        if special is None:
            option_ev = ordinary_ev
            positive = ordinary_positive
            special_note = "soulable special override unavailable in current public state"
        else:
            special_value = _spectral_unopened_public_value(state, special)
            option_ev = (
                (1.0 - _SOUL_PROBABILITY) * ordinary_ev
                + _SOUL_PROBABILITY * special_value
            )
            positive = (
                (1.0 - _SOUL_PROBABILITY) * ordinary_positive
                + _SOUL_PROBABILITY * (1.0 if special_value > 0.0 else 0.0)
            )
            special_note = (
                "soulable 0.3% special override uses the same non-recursive public value"
            )

        return option_ev, positive, (
            "Spectral one-offer EV uses current public eligible get_current_pool catalogue",
            "unopened Spectral SHOP expectation performs zero D9 calls",
            "Black Hole uses the established B4 Spectral base value=4.000",
            "The Soul uses its existing bounded Legendary-Joker option value",
            "all other hypothetical Spectral outcomes contribute zero until visible",
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
