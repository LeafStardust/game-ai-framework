from __future__ import annotations

"""Bounded public-generator expectation for unopened Spectral boosters.

D8 values hypothetical outcomes through an acyclic leaf evaluator rather than the
visible-pack D9 authority. Unsupported, stochastic, or generative outcomes are zero.
Large public pools retain their full denominator so omitted mass is also zero.
"""

from games.balatro.actions import BUY_BOOSTER
from games.balatro.consumable_generation_pool_live_state_policy import (
    install_consumable_generation_pool_live_state_policy,
)
from games.balatro.ectoplasm_pack_expectation_policy import install_ectoplasm_pack_expectation_policy
from games.balatro.ouija_pack_expectation_policy import install_ouija_pack_expectation_policy
from games.balatro.shop_booster_policy import (
    BUY,
    HOLD,
    BuildAwareShopBoosterPolicy,
    ShopBoosterRecommendation,
)
from games.balatro.unopened_consumable_outcome_value import (
    UnopenedConsumableOutcomeValueEvaluator,
)


_SOUL_PROBABILITY = 0.003
_MAX_EXACT_PUBLIC_RECORDS = 12
_MAX_EVALUATED_RECORDS_LARGE_POOL = 8
_SOUL_RECORD = {
    "center": "c_soul",
    "label": "The Soul",
    "ability_name": "The Soul",
    "ability_set": "SPECTRAL",
}
_BLACK_HOLE_RECORD = {
    "center": "c_black_hole",
    "label": "Black Hole",
    "ability_name": "Black Hole",
    "ability_set": "SPECTRAL",
}


def _bounded_record_indices(record_count: int) -> tuple[int, ...]:
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


class SpectralBoosterExpectationEvaluator:
    def __init__(self, *, outcome_evaluator=None, pack_policy=None) -> None:
        # Compatibility-only parameter. D8 must never call the supplied D9 policy.
        del pack_policy
        self.outcome_evaluator = outcome_evaluator or UnopenedConsumableOutcomeValueEvaluator()

    @staticmethod
    def _pool(state) -> tuple[dict, ...]:
        pools = getattr(state, "consumable_generation_pools", {}) or {}
        values = pools.get("SPECTRAL", ()) if isinstance(pools, dict) else ()
        normalized = []
        for record in values:
            if not isinstance(record, dict):
                continue
            data = dict(record)
            data.setdefault("ability_set", "SPECTRAL")
            normalized.append(data)
        return tuple(normalized)

    def _visible_value(self, state, record: dict) -> float:
        try:
            result = self.outcome_evaluator.evaluate(state, record, kind="SPECTRAL")
        except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
            return 0.0
        return max(0.0, float(result.value))

    def evaluate(self, state) -> tuple[float, float, tuple[str, ...]]:
        if not bool(getattr(state, "consumable_generation_pool_observed", False)):
            return 0.0, 0.0, (
                "Spectral expectation unavailable: public generation pools were not observed",
            )

        records = self._pool(state)
        if not records:
            return 0.0, 0.0, ("Spectral public generation pool is empty",)

        indices = _bounded_record_indices(len(records))
        ordinary_values = tuple(self._visible_value(state, records[index]) for index in indices)
        denominator = float(len(records))
        ordinary_ev = sum(ordinary_values) / denominator
        ordinary_positive = sum(1 for value in ordinary_values if value > 0.0) / denominator

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
            special_value = self._visible_value(state, special)
            option_ev = (1.0 - _SOUL_PROBABILITY) * ordinary_ev + _SOUL_PROBABILITY * special_value
            positive = (
                (1.0 - _SOUL_PROBABILITY) * ordinary_positive
                + _SOUL_PROBABILITY * (1.0 if special_value > 0.0 else 0.0)
            )
            special_note = "soulable 0.3% special override modeled with Black Hole precedence"

        return option_ev, positive, (
            "Spectral one-offer EV uses current public eligible get_current_pool catalogue",
            f"Spectral outcomes evaluated={len(indices)}/{len(records)}; omitted/deferred mass remains zero",
            "unopened Spectral SHOP expectation performs zero D9 calls",
            "Black Hole uses the established B4 Spectral base value=4.000",
            "all other hypothetical Spectral outcomes contribute zero until visible",
            special_note,
            f"one-offer positive-choice probability={positive:.6f}",
            f"one-offer sunk-cost option EV={option_ev:.6f}",
            "actual opened-pack D9 remains authoritative after an identity is visible",
            "best-of-2/4 and Mega second-selection improvement omitted conservatively",
        )


def install_spectral_booster_expectation_policy() -> None:
    install_consumable_generation_pool_live_state_policy()
    install_ouija_pack_expectation_policy()
    install_ectoplasm_pack_expectation_policy()
    if getattr(BuildAwareShopBoosterPolicy, "_spectral_generator_expectation_installed", False):
        return

    original_init = BuildAwareShopBoosterPolicy.__init__
    original_recommend = BuildAwareShopBoosterPolicy.recommend

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self._spectral_generator_expectation = SpectralBoosterExpectationEvaluator()

    def recommend(self, state, action):
        family = self._family(action.target)
        if family != "SPECTRAL":
            return original_recommend(self, state, action)
        if state.phase != "SHOP":
            raise ValueError("D8 booster acquisition requires SHOP phase")
        if action.name != BUY_BOOSTER:
            raise ValueError("D8 booster acquisition requires BUY_BOOSTER action")

        variant = self._variant(action.target)
        price = self._price(action.target)
        if price > int(state.money):
            return ShopBoosterRecommendation(
                decision=HOLD,
                action=action,
                family=family,
                variant=variant,
                total=self.parent_hold_baseline,
                rationale=(f"Spectral pack costs ${price} but only ${state.money} is available",),
            )

        option_utility, per_offer_positive, expectation_notes = self._spectral_generator_expectation.evaluate(state)
        offer_count, selection_count = self.PACK_LAYOUTS[family][variant]
        resource_cost = self.resource_valuator.money_spend_cost(
            money=int(state.money),
            spend=price,
            price_weight=self.thresholds.price_weight,
            interest_weight=self.thresholds.interest_weight,
            reserve_target=self.thresholds.reserve_target,
            reserve_weight=self.thresholds.reserve_weight,
            vouchers=getattr(state, "vouchers", ()),
            jokers=getattr(state, "jokers", ()),
        )
        advantage = float(option_utility) - float(resource_cost.total)
        decision = BUY if option_utility > 0.0 and advantage > float(self.thresholds.minimum_buy_advantage) else HOLD
        return ShopBoosterRecommendation(
            decision=decision,
            action=action,
            family=family,
            variant=variant,
            total=float(self.parent_hold_baseline) + advantage,
            advantage_over_save=advantage,
            option_utility=float(option_utility),
            build_need_score=0.0,
            per_offer_hit_probability=float(per_offer_positive),
            at_least_one_hit_probability=float(per_offer_positive),
            offer_count=offer_count,
            selection_count=selection_count,
            runway_factor=self._runway_factor(max(1, int(getattr(state, "ante", 1) or 1))),
            price_penalty=resource_cost.direct,
            interest_penalty=resource_cost.interest,
            reserve_penalty=resource_cost.reserve,
            rationale=(
                f"booster family=SPECTRAL variant={variant}",
                *expectation_notes,
                f"visible layout offers={offer_count} selections={selection_count}",
                f"pack purchase resource cost={resource_cost.total:.3f}",
                f"D8 conservative Spectral advantage over SAVE=0 is {advantage:.3f}",
                "unopened Spectral identities and RNG state are not inspected",
            ),
        )

    BuildAwareShopBoosterPolicy.__init__ = init
    BuildAwareShopBoosterPolicy.recommend = recommend
    BuildAwareShopBoosterPolicy._spectral_generator_expectation_installed = True
