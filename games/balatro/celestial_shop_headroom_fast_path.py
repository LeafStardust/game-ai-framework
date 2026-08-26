from __future__ import annotations

"""Skip expensive Celestial expectation when an existing hard veto already decides HOLD.

The final Celestial D8 policy requires marginal hand-development headroom and the
ordinary D8 cash reserve before a pack can be bought. Those predicates depend only
on current public state. When either already fails, enumerating and literally
scoring the eligible Planet pool cannot change the final HOLD and can make a live
SHOP checkpoint appear hung.

The fast path still performs the ordinary cheap D8 parent calculation first in
place: build-need metadata, public layout probability, option utility, and the
shared RunResourceValuator money/interest/reserve accounting remain observable and
identical to the parent D8 contract. Only the later finite Planet expectation is
omitted when its result cannot alter the decision.

The broader SHOP runtime contract is intentionally *not* imported or installed from
this module. ``games.balatro.__init__`` installs this Celestial adapter while the
package is still initializing; recursively loading the wider D2/D8/D14 policy graph
from here can poison Python/pytest package collection. Production installs the
broader runtime contract from the supervisor entry point after package initialization
has completed.
"""

from games.balatro.planet_pack_fallback_policy import _celestial_headroom
from games.balatro.shop_booster_policy import (
    HOLD,
    BuildAwareShopBoosterPolicy,
    ShopBoosterRecommendation,
)


def _forced_celestial_hold(self, state, action, *, headroom_notes, hold_reason):
    """Reproduce the cheap parent D8 Celestial accounting without finite Planet EV."""
    family = "CELESTIAL"
    variant = self._variant(action.target)
    price = self._price(action.target)
    profile = self.build_profiler.profile(state)
    build_need_score, build_notes = self._build_need(state, profile, family=family)
    offer_count, selection_count = self.PACK_LAYOUTS[family][variant]
    runway_factor = self._runway_factor(profile.ante)
    per_offer_probability = self._clamp_probability(
        self._base_hit_probability(family)
        + build_need_score * self.thresholds.need_hit_probability_bonus
    )
    at_least_one = 1.0 - (1.0 - per_offer_probability) ** offer_count
    hit_value = (
        self._base_hit_value(family)
        + build_need_score * self.thresholds.need_value_weight
        + runway_factor * self.thresholds.runway_value_weight
    )
    selection_multiplier = 1.0 + max(0, selection_count - 1) * (
        self.thresholds.second_selection_value_fraction
    )
    option_utility = at_least_one * hit_value * selection_multiplier

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
    advantage = option_utility - resource_cost.total

    return ShopBoosterRecommendation(
        decision=HOLD,
        action=action,
        family=family,
        variant=variant,
        total=float(self.parent_hold_baseline) + advantage,
        advantage_over_save=advantage,
        option_utility=option_utility,
        build_need_score=build_need_score,
        per_offer_hit_probability=per_offer_probability,
        at_least_one_hit_probability=at_least_one,
        offer_count=offer_count,
        selection_count=selection_count,
        runway_factor=runway_factor,
        price_penalty=resource_cost.direct,
        interest_penalty=resource_cost.interest,
        reserve_penalty=resource_cost.reserve,
        rationale=(
            f"booster family={family} variant={variant}",
            *build_notes,
            f"visible pack layout offers={offer_count} selections={selection_count}",
            f"build need score={build_need_score:.3f}",
            f"per-offer useful-choice prior={per_offer_probability:.3f}",
            f"P(at least one useful visible offer)={at_least_one:.3f}",
            f"runway factor={runway_factor:.3f}",
            f"option EV={option_utility:.3f}",
            f"price penalty={resource_cost.direct:.3f}",
            f"interest penalty={resource_cost.interest:.3f}",
            f"reserve penalty={resource_cost.reserve:.3f}",
            *tuple(resource_cost.notes),
            *headroom_notes,
            hold_reason,
            "Celestial finite Planet expectation omitted because it cannot alter this HOLD",
            "ordinary D8 shared resource accounting remains authoritative",
            "no hidden pack contents, RNG state, or future choices are inspected",
        ),
    )


def install_celestial_shop_headroom_fast_path() -> None:
    if getattr(
        BuildAwareShopBoosterPolicy,
        "_celestial_headroom_fast_path_installed",
        False,
    ):
        return

    original_recommend = BuildAwareShopBoosterPolicy.recommend

    def recommend(self, state, action):
        family = self._family(action.target)
        if family != "CELESTIAL":
            return original_recommend(self, state, action)

        price = self._price(action.target)
        if price > int(state.money):
            # Preserve the existing unaffordable-path rationale and metadata.
            return original_recommend(self, state, action)

        headroom, headroom_notes = _celestial_headroom(state)
        reserve_target = int(self.thresholds.reserve_target)
        money_after = int(state.money) - int(price)

        if headroom <= 0:
            return _forced_celestial_hold(
                self,
                state,
                action,
                headroom_notes=headroom_notes,
                hold_reason="Celestial purchase held: no marginal hand-development headroom",
            )
        if money_after < reserve_target:
            return _forced_celestial_hold(
                self,
                state,
                action,
                headroom_notes=headroom_notes,
                hold_reason=(
                    "Celestial purchase held: purchase would "
                    f"leave ${money_after} below ${reserve_target} reserve"
                ),
            )

        return original_recommend(self, state, action)

    BuildAwareShopBoosterPolicy.recommend = recommend
    BuildAwareShopBoosterPolicy._celestial_headroom_fast_path_installed = True
