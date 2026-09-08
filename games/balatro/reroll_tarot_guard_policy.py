from __future__ import annotations

"""Bound D11 future-Tarot value from the public eligible Tarot pool.

Every public record is preflighted for model availability, then only a deterministic
bounded subset receives leaf valuation. No hypothetical future Tarot enters held-use
D9 mechanics; omitted probability mass remains literal zero.
"""

from dataclasses import dataclass
from types import SimpleNamespace

from games.balatro.live.consumable_factory import LiveConsumableFactory
from games.balatro.shop_reroll_policy import BuildAwareShopRerollPolicy
from games.balatro.unopened_consumable_outcome_value import (
    UnopenedConsumableOutcomeValueEvaluator,
)


_MAX_EXACT_PUBLIC_RECORDS = 12
_MAX_EVALUATED_RECORDS_LARGE_POOL = 8


@dataclass(frozen=True)
class RerollTarotExpectation:
    complete: bool
    expected_option_gain: float
    outcome_count: int
    rationale: tuple[str, ...] = ()


def _bounded_record_indices(record_count: int, *, exact: bool) -> tuple[int, ...]:
    count = max(0, int(record_count))
    if count == 0:
        return ()
    if exact or count <= _MAX_EVALUATED_RECORDS_LARGE_POOL:
        return tuple(range(count))
    budget = min(_MAX_EVALUATED_RECORDS_LARGE_POOL, count)
    if budget == 1:
        return (0,)
    return tuple(round(index * (count - 1) / (budget - 1)) for index in range(budget))


class _LeafHeldOptionAdapter:
    """Compatibility surface for bounded tests/callers; never enters D9."""

    def __init__(self, outcome_evaluator) -> None:
        self.outcome_evaluator = outcome_evaluator

    def evaluate(self, state, candidate):
        name = str(getattr(candidate, "name", getattr(candidate, "label", "")) or "")
        category = str(getattr(candidate, "category", "TAROT") or "TAROT").upper()
        result = self.outcome_evaluator.evaluate(
            state,
            {
                "label": name,
                "ability_name": name,
                "ability_set": category,
            },
            kind=category,
        )
        return SimpleNamespace(complete=True, expected_gain=max(0.0, float(result.value)))


class RerollTarotExpectationEvaluator:
    def __init__(self, *, outcome_evaluator=None, factory=None) -> None:
        self.outcome_evaluator = outcome_evaluator or UnopenedConsumableOutcomeValueEvaluator()
        self.factory = factory or LiveConsumableFactory()
        self.held_option = _LeafHeldOptionAdapter(self.outcome_evaluator)

    def evaluate(self, state, *, money: int, expected_price: int) -> RerollTarotExpectation:
        if not bool(getattr(state, "consumable_generation_pool_observed", False)):
            return self._incomplete(
                "future Tarot expectation unavailable: public consumable generation pool was not observed"
            )
        pools = getattr(state, "consumable_generation_pools", {}) or {}
        records = tuple(
            dict(record)
            for record in (pools.get("TAROT", ()) if isinstance(pools, dict) else ())
            if isinstance(record, dict)
        )
        if not records:
            return self._incomplete("future Tarot expectation unavailable: eligible Tarot pool is empty")

        # Preflight every public record before sampling so an unsupported record cannot
        # hide outside the evaluated subset and make the expectation falsely complete.
        candidates = []
        for record in records:
            candidate = self.factory.create(dict(record))
            if candidate is None:
                return self._incomplete(
                    "eligible future Tarot is not modeled: "
                    + str(record.get("label") or record.get("center") or "unknown"),
                    len(candidates),
                )
            candidate.price = int(expected_price)
            candidates.append(candidate)

        projected = state.copy()
        projected.money = max(0, int(money))
        exact = len(candidates) <= _MAX_EXACT_PUBLIC_RECORDS
        evaluated_indices = _bounded_record_indices(len(candidates), exact=exact)
        evaluated_sum = 0.0
        for index in evaluated_indices:
            try:
                expectation = self.held_option.evaluate(projected, candidates[index])
            except (AttributeError, KeyError, RuntimeError, TypeError, ValueError, ZeroDivisionError):
                continue
            if bool(getattr(expectation, "complete", False)):
                evaluated_sum += max(0.0, float(getattr(expectation, "expected_gain", 0.0)))

        expected = evaluated_sum / float(len(candidates))
        return RerollTarotExpectation(
            complete=True,
            expected_option_gain=expected,
            outcome_count=len(candidates),
            rationale=(
                "future Tarot uses current public eligible get_current_pool catalogue",
                f"eligible Tarot outcomes={len(candidates)}",
                f"bounded leaf outcomes evaluated={len(evaluated_indices)}/{len(candidates)}",
                "D11 future Tarot never invokes D9 policy authority",
                "unevaluated/deferred probability mass remains zero without renormalization",
                f"expected bounded option value={expected:.3f}",
                f"unseen Tarot expected-price prior=${int(expected_price)}",
                "future exact Tarot identity, RNG state, pseudoseed, and pool order are not observed",
            ),
        )

    @staticmethod
    def _incomplete(reason: str, outcome_count: int = 0) -> RerollTarotExpectation:
        return RerollTarotExpectation(
            complete=False,
            expected_option_gain=0.0,
            outcome_count=outcome_count,
            rationale=(reason, "future-Tarot reroll expectation fails closed"),
        )


def install_reroll_tarot_guard_policy() -> None:
    if getattr(BuildAwareShopRerollPolicy, "_tarot_public_expectation_installed", False):
        return

    original_init = BuildAwareShopRerollPolicy.__init__
    original_future_offer_score = BuildAwareShopRerollPolicy._future_offer_score

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.reroll_tarot_expectation = RerollTarotExpectationEvaluator()

    def future_offer_score(self, state, offer, *, money: int, thresholds):
        if str(getattr(offer, "family", "")).upper() != "TAROT":
            return original_future_offer_score(self, state, offer, money=money, thresholds=thresholds)

        hold = float(self.shop_policy.hold_bias)
        price = int(getattr(offer, "expected_price", 0) or 0)
        if price > int(money):
            return hold
        if len(state.consumables) >= int(state.consumable_slots):
            return hold

        expectation = self.reroll_tarot_expectation.evaluate(
            state,
            money=int(money),
            expected_price=price,
        )
        if not expectation.complete:
            return hold

        purchase_resource = self.shop_policy.resource_valuator.money_spend_cost(
            money=int(money),
            spend=price,
            price_weight=self.shop_policy.price_weight,
            interest_weight=self.shop_policy.interest_weight,
            reserve_target=self.shop_policy.reserve_target,
            reserve_weight=self.shop_policy.reserve_weight,
            vouchers=getattr(state, "vouchers", ()),
            jokers=getattr(state, "jokers", ()),
        )
        slot_cost = self.shop_policy.resource_valuator.slot_opportunity_cost(
            occupied=len(state.consumables),
            capacity=int(state.consumable_slots),
            last_slot_penalty=self.shop_policy.last_consumable_slot_penalty,
            penultimate_slot_penalty=0.0,
            resource="consumable",
        ).total
        gain = float(expectation.expected_option_gain) - float(purchase_resource.total) - float(slot_cost)
        return hold + max(0.0, gain)

    BuildAwareShopRerollPolicy.__init__ = init
    BuildAwareShopRerollPolicy._future_offer_score = future_offer_score
    BuildAwareShopRerollPolicy._tarot_public_expectation_installed = True
