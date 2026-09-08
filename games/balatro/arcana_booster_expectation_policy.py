from __future__ import annotations

"""Bounded public-generator expectation for unopened Arcana boosters.

D8 evaluates the current public Tarot/Spectral generator catalogue without routing
hypothetical outcomes through D9. Each sampled outcome is valued by the acyclic
unopened-consumable leaf evaluator; unsupported, stochastic, or generative outcomes
contribute literal zero. Large public pools keep their full denominator, so omitted
records are also literal zero rather than renormalized probability mass.
"""

from games.balatro.actions import BUY_BOOSTER
from games.balatro.consumable_generation_pool_live_state_policy import (
    install_consumable_generation_pool_live_state_policy,
)
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
_OMEN_GLOBE_SPECTRAL_PROBABILITY = 0.20
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


def _bounded_record_indices(record_count: int, *, exact: bool) -> tuple[int, ...]:
    if record_count <= 0:
        return ()
    if exact or record_count <= _MAX_EVALUATED_RECORDS_LARGE_POOL:
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


class ArcanaBoosterExpectationEvaluator:
    def __init__(self, *, outcome_evaluator=None, pack_policy=None) -> None:
        # ``pack_policy`` is retained only as a compatibility argument for older
        # fixtures/callers. It is deliberately never stored or invoked: unopened D8
        # expectation must not re-enter D9.
        del pack_policy
        self.outcome_evaluator = outcome_evaluator or UnopenedConsumableOutcomeValueEvaluator()

    @staticmethod
    def _pool(state, kind: str) -> tuple[dict, ...]:
        pools = getattr(state, "consumable_generation_pools", {}) or {}
        values = pools.get(kind.upper(), ()) if isinstance(pools, dict) else ()
        normalized = []
        for record in values:
            if not isinstance(record, dict):
                continue
            data = dict(record)
            data.setdefault("ability_set", kind.upper())
            normalized.append(data)
        return tuple(normalized)

    def _visible_value(self, state, record: dict, *, kind: str | None = None) -> float:
        resolved_kind = str(kind or record.get("ability_set") or "TAROT").upper()
        try:
            result = self.outcome_evaluator.evaluate(state, record, kind=resolved_kind)
        except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
            return 0.0
        return max(0.0, float(result.value))

    def _ordinary_pool_mean(self, state, kind: str) -> tuple[float, float, int, int]:
        records = self._pool(state, kind)
        record_count = len(records)
        if not records:
            return 0.0, 0.0, 0, 0
        exact = record_count <= _MAX_EXACT_PUBLIC_RECORDS
        indices = _bounded_record_indices(record_count, exact=exact)
        # Keep this call signature positional for existing runtime-bound fixtures;
        # _pool already stamps ability_set so _visible_value can infer the family.
        values = tuple(self._visible_value(state, records[index]) for index in indices)
        denominator = float(record_count)
        return (
            sum(values) / denominator,
            sum(1 for value in values if value > 0.0) / denominator,
            len(indices),
            record_count,
        )

    def _tarot_offer(self, state) -> tuple[float, float, int, int]:
        ordinary_ev, ordinary_positive, evaluated, total = self._ordinary_pool_mean(state, "TAROT")
        if not bool(getattr(state, "soul_generation_available", False)):
            return ordinary_ev, ordinary_positive, evaluated, total
        soul_value = self._visible_value(state, _SOUL_RECORD)
        return (
            (1.0 - _SOUL_PROBABILITY) * ordinary_ev + _SOUL_PROBABILITY * soul_value,
            (1.0 - _SOUL_PROBABILITY) * ordinary_positive
            + _SOUL_PROBABILITY * (1.0 if soul_value > 0.0 else 0.0),
            evaluated,
            total,
        )

    def _spectral_offer(self, state) -> tuple[float, float, int, int]:
        ordinary_ev, ordinary_positive, evaluated, total = self._ordinary_pool_mean(state, "SPECTRAL")
        special = None
        if bool(getattr(state, "black_hole_generation_available", False)):
            special = _BLACK_HOLE_RECORD
        elif bool(getattr(state, "soul_generation_available", False)):
            special = _SOUL_RECORD
        if special is None:
            return ordinary_ev, ordinary_positive, evaluated, total
        special_value = self._visible_value(state, special)
        return (
            (1.0 - _SOUL_PROBABILITY) * ordinary_ev + _SOUL_PROBABILITY * special_value,
            (1.0 - _SOUL_PROBABILITY) * ordinary_positive
            + _SOUL_PROBABILITY * (1.0 if special_value > 0.0 else 0.0),
            evaluated,
            total,
        )

    def evaluate(self, state) -> tuple[float, float, tuple[str, ...]]:
        if not bool(getattr(state, "consumable_generation_pool_observed", False)):
            return 0.0, 0.0, (
                "Arcana expectation unavailable: public Tarot/Spectral generation pools were not observed",
            )

        tarot_ev, tarot_positive, tarot_evaluated, tarot_total = self._tarot_offer(state)
        tarot_bound_note = (
            f"Tarot outcomes evaluated={tarot_evaluated}/{tarot_total}; omitted/deferred mass remains zero"
        )
        if not bool(getattr(state, "omen_globe_active", False)):
            return tarot_ev, tarot_positive, (
                "Arcana one-offer EV uses current public eligible Tarot pool",
                "bounded acyclic unopened-consumable valuation performs zero D9 calls",
                tarot_bound_note,
                f"one-offer positive-choice probability={tarot_positive:.6f}",
                f"one-offer sunk-cost option EV={tarot_ev:.6f}",
                "best-of-3/5 and Mega second-selection improvement omitted conservatively",
            )

        spectral_ev, spectral_positive, spectral_evaluated, spectral_total = self._spectral_offer(state)
        option_ev = (
            (1.0 - _OMEN_GLOBE_SPECTRAL_PROBABILITY) * tarot_ev
            + _OMEN_GLOBE_SPECTRAL_PROBABILITY * spectral_ev
        )
        positive = (
            (1.0 - _OMEN_GLOBE_SPECTRAL_PROBABILITY) * tarot_positive
            + _OMEN_GLOBE_SPECTRAL_PROBABILITY * spectral_positive
        )
        return option_ev, positive, (
            "Omen Globe Arcana generator modeled as exact 80% Tarot / 20% Spectral per offer",
            tarot_bound_note,
            f"Spectral outcomes evaluated={spectral_evaluated}/{spectral_total}; omitted/deferred mass remains zero",
            "bounded acyclic unopened-consumable valuation performs zero D9 calls",
            f"one-offer positive-choice probability={positive:.6f}",
            f"one-offer sunk-cost option EV={option_ev:.6f}",
            "best-of-3/5 and Mega second-selection improvement omitted conservatively",
        )


def install_arcana_booster_expectation_policy() -> None:
    install_consumable_generation_pool_live_state_policy()
    if getattr(BuildAwareShopBoosterPolicy, "_arcana_generator_expectation_installed", False):
        return

    original_init = BuildAwareShopBoosterPolicy.__init__
    original_recommend = BuildAwareShopBoosterPolicy.recommend

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self._arcana_generator_expectation = ArcanaBoosterExpectationEvaluator()

    def recommend(self, state, action):
        family = self._family(action.target)
        if family != "ARCANA":
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
                rationale=(f"Arcana pack costs ${price} but only ${state.money} is available",),
            )

        option_utility, per_offer_positive, expectation_notes = self._arcana_generator_expectation.evaluate(state)
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
        decision = (
            BUY
            if option_utility > 0.0
            and advantage > float(self.thresholds.minimum_buy_advantage)
            else HOLD
        )
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
                f"booster family=ARCANA variant={variant}",
                *expectation_notes,
                f"visible layout offers={offer_count} selections={selection_count}",
                f"pack purchase resource cost={resource_cost.total:.3f}",
                f"D8 conservative Arcana advantage over SAVE=0 is {advantage:.3f}",
                "unopened Arcana identities and RNG state are not inspected",
            ),
        )

    BuildAwareShopBoosterPolicy.__init__ = init
    BuildAwareShopBoosterPolicy.recommend = recommend
    BuildAwareShopBoosterPolicy._arcana_generator_expectation_installed = True
