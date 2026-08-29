from __future__ import annotations

"""Replace fixed D8 Arcana priors with public generator expectation.

Balatro creates each Arcana offer from the current Tarot pool, except Omen Globe
changes each offer to 80% Tarot / 20% Spectral. Both branches are ``soulable``:
Tarot has a 0.3% Soul override when Soul is eligible; Spectral has the same 0.3%
special roll, with Black Hole taking final precedence when eligible and Soul taking
it otherwise. Ordinary pool identity remains hidden and is never inspected.

D8 uses a conservative one-offer expectation. Each evaluated visible outcome is
scored through the installed D9 ``BalatroPackPolicy`` against the opened-pack Skip=0
baseline. Small public pools are evaluated exactly. Large pools use a stable,
deterministically spread subset while retaining the full eligible-pool denominator;
omitted probability mass therefore remains literal zero instead of being
renormalized. Outcomes D9 cannot yet value safely (for example Emperor or unresolved
permanent-hand-size effects) likewise contribute zero. Best-of-3/5 and Mega
second-selection improvements are deliberately omitted.
"""

from copy import deepcopy

from games.balatro.actions import BUY_BOOSTER, SELECT_PACK_CARD, BalatroAction
from games.balatro.consumable_generation_pool_live_state_policy import (
    install_consumable_generation_pool_live_state_policy,
)
from games.balatro.live.pack import LivePackChoice
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.shop_booster_policy import (
    BUY,
    HOLD,
    BuildAwareShopBoosterPolicy,
    ShopBoosterRecommendation,
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

    # Stable spread across the complete public pool instead of taking only an
    # alphabetic/pool-prefix slice. Duplicate rounded indices are filled from the
    # remaining records deterministically.
    selected = {
        round(position * (record_count - 1) / float(target - 1))
        for position in range(target)
    }
    if len(selected) < target:
        selected.update(
            index
            for index in range(record_count)
            if index not in selected
        )
    return tuple(sorted(selected)[:target])


class ArcanaBoosterExpectationEvaluator:
    def __init__(self, *, pack_policy: BalatroPackPolicy | None = None) -> None:
        self.pack_policy = pack_policy or BalatroPackPolicy(skip_bias=0.0)

    @staticmethod
    def _pool(state, kind: str) -> tuple[dict, ...]:
        pools = getattr(state, "consumable_generation_pools", {}) or {}
        values = pools.get(kind.upper(), ()) if isinstance(pools, dict) else ()
        return tuple(dict(record) for record in values if isinstance(record, dict))

    def _visible_value(self, state, record: dict) -> float:
        data = dict(record)
        label = str(data.get("label") or "")
        center = str(data.get("center") or "").lower()

        # Emperor's D9 scorer evaluates the public Tarot pool it can generate. If
        # unopened Arcana expectation sends Emperor through that scorer, the same
        # Arcana-visible Tarot pool can re-enter Emperor expectation through generated
        # option valuation. D8's documented conservative contract already treats
        # unsafe recursive outcomes as literal zero; enforce that boundary here.
        if label == "The Emperor" or center == "c_emperor":
            return 0.0

        if label == "The Fool":
            last = getattr(state, "last_tarot_planet", None)
            if last:
                data["last_tarot_planet"] = str(last)

        choice = LivePackChoice(area_index=0, address=0, data=data)
        action = BalatroAction(SELECT_PACK_CARD, target=choice)
        opened_state = deepcopy(state)
        opened_state.phase = (
            "SPECTRAL_PACK"
            if choice.kind == "SPECTRAL"
            else "TAROT_PACK"
        )
        try:
            scored = self.pack_policy.score_action(opened_state, action)
        except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
            return 0.0
        # Opened-pack Skip is the sunk-cost zero baseline. Deferred/unavailable
        # outcomes therefore contribute zero to unopened option value.
        return max(0.0, float(scored.total))

    def _ordinary_pool_mean(
        self,
        state,
        kind: str,
    ) -> tuple[float, float, int, int]:
        records = self._pool(state, kind)
        record_count = len(records)
        if not records:
            return 0.0, 0.0, 0, 0

        exact = record_count <= _MAX_EXACT_PUBLIC_RECORDS
        indices = _bounded_record_indices(record_count, exact=exact)
        values = tuple(self._visible_value(state, records[index]) for index in indices)
        denominator = float(record_count)
        return (
            sum(values) / denominator,
            sum(1 for value in values if value > 0.0) / denominator,
            len(indices),
            record_count,
        )

    def _tarot_offer(self, state) -> tuple[float, float, int, int]:
        ordinary_ev, ordinary_positive, evaluated, total = self._ordinary_pool_mean(
            state,
            "TAROT",
        )
        if not bool(getattr(state, "soul_generation_available", False)):
            return ordinary_ev, ordinary_positive, evaluated, total
        soul_value = self._visible_value(state, _SOUL_RECORD)
        return (
            (1.0 - _SOUL_PROBABILITY) * ordinary_ev
            + _SOUL_PROBABILITY * soul_value,
            (1.0 - _SOUL_PROBABILITY) * ordinary_positive
            + _SOUL_PROBABILITY * (1.0 if soul_value > 0.0 else 0.0),
            evaluated,
            total,
        )

    def _spectral_offer(self, state) -> tuple[float, float, int, int]:
        ordinary_ev, ordinary_positive, evaluated, total = self._ordinary_pool_mean(
            state,
            "SPECTRAL",
        )
        special = None
        if bool(getattr(state, "black_hole_generation_available", False)):
            special = _BLACK_HOLE_RECORD
        elif bool(getattr(state, "soul_generation_available", False)):
            special = _SOUL_RECORD
        if special is None:
            return ordinary_ev, ordinary_positive, evaluated, total
        special_value = self._visible_value(state, special)
        return (
            (1.0 - _SOUL_PROBABILITY) * ordinary_ev
            + _SOUL_PROBABILITY * special_value,
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
        omen = bool(getattr(state, "omen_globe_active", False))
        tarot_bound_note = (
            f"Tarot visible outcomes evaluated={tarot_evaluated}/{tarot_total}; "
            "omitted large-pool probability mass remains zero"
        )
        if not omen:
            return tarot_ev, tarot_positive, (
                "Arcana one-offer EV uses current public eligible Tarot pool",
                tarot_bound_note,
                "soulable Tarot override modeled at exact 0.3% when eligible",
                f"one-offer positive-choice probability={tarot_positive:.6f}",
                f"one-offer sunk-cost option EV={tarot_ev:.6f}",
                "best-of-3/5 and Mega second-selection improvement omitted conservatively",
            )

        spectral_ev, spectral_positive, spectral_evaluated, spectral_total = (
            self._spectral_offer(state)
        )
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
            "Tarot/Spectral pools use current public get_current_pool eligibility",
            tarot_bound_note,
            (
                f"Spectral visible outcomes evaluated={spectral_evaluated}/{spectral_total}; "
                "omitted large-pool probability mass remains zero"
            ),
            "soulable 0.3% special override and Black Hole precedence are modeled",
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
        self._arcana_generator_expectation = ArcanaBoosterExpectationEvaluator(
            pack_policy=BalatroPackPolicy(skip_bias=0.0),
        )

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

        option_utility, per_offer_positive, expectation_notes = (
            self._arcana_generator_expectation.evaluate(state)
        )
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
