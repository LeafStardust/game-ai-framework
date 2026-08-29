from __future__ import annotations

"""Bound D11 future-Tarot value from the public eligible Tarot pool.

A reroll does not reveal the future Tarot identity. D11 therefore averages a bounded
acyclic leaf value over the current public generation pool. It never routes a
hypothetical unseen Tarot through held-option/D9 mechanics. Unsupported, stochastic,
or generative outcomes and omitted large-pool mass remain literal zero.
"""

from dataclasses import dataclass

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


class RerollTarotExpectationEvaluator:
    def __init__(self, *, outcome_evaluator=None) -> None:
        self.outcome_evaluator = outcome_evaluator or UnopenedConsumableOutcomeValueEvaluator()

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

        exact = len(records) <= _MAX_EXACT_PUBLIC_RECORDS
        evaluated_indices = _bounded_record_indices(len(records), exact=exact)
        evaluated_sum = 0.0
        for index in evaluated_indices:
            try:
                result = self.outcome_evaluator.evaluate(state, records[index], kind="TAROT")
            except (AttributeError, KeyError, RuntimeError, TypeError, ValueError, ZeroDivisionError):
                continue
            evaluated_sum += max(0.0, float(result.value))

        expected = evaluated_sum / float(len(records))
        return RerollTarotExpectation(
            complete=True,
            expected_option_gain=expected,
            outcome_count=len(records),
            rationale=(
                "future Tarot uses current public eligible get_current_pool catalogue",
                f"eligible Tarot outcomes={len(records)}",
                f"bounded leaf outcomes evaluated={len(evaluated_indices)}/{len(records)}",
                "D11 future Tarot never invokes held-option or D9 policy authority",
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
