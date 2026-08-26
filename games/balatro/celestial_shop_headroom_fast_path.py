from __future__ import annotations

"""Skip expensive Celestial expectation when an existing hard veto already decides HOLD.

The final Celestial D8 policy requires marginal hand-development headroom and the
ordinary D8 cash reserve before a pack can be bought.  Those two predicates depend
only on current public state and are evaluated again after the finite Planet
expectation.  When either already fails, enumerating and literally scoring the
eligible Planet pool cannot change the result and can make a live SHOP checkpoint
appear hung.

This adapter installs after the existing Celestial wrappers and applies exactly the
same headroom/reserve veto first.  States that can still buy delegate unchanged to
the full finite expectation.  No hidden pack identity, RNG state, future draw order,
or additional heuristic is introduced.
"""

from games.balatro.planet_pack_fallback_policy import _celestial_headroom
from games.balatro.shop_booster_policy import (
    HOLD,
    BuildAwareShopBoosterPolicy,
    ShopBoosterRecommendation,
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
            hold_reason = "Celestial purchase held: no marginal hand-development headroom"
        elif money_after < reserve_target:
            hold_reason = (
                "Celestial purchase held: purchase would "
                f"leave ${money_after} below ${reserve_target} reserve"
            )
        else:
            return original_recommend(self, state, action)

        variant = self._variant(action.target)
        offer_count, selection_count = self.PACK_LAYOUTS[family][variant]
        return ShopBoosterRecommendation(
            decision=HOLD,
            action=action,
            family=family,
            variant=variant,
            total=float(self.parent_hold_baseline),
            advantage_over_save=0.0,
            option_utility=0.0,
            build_need_score=0.0,
            per_offer_hit_probability=0.0,
            at_least_one_hit_probability=0.0,
            offer_count=offer_count,
            selection_count=selection_count,
            runway_factor=self._runway_factor(
                max(1, int(getattr(state, "ante", 1) or 1))
            ),
            rationale=(
                "Celestial authoritative headroom/reserve veto evaluated before finite Planet expectation",
                *headroom_notes,
                hold_reason,
                "finite Planet expectation omitted because it cannot alter this HOLD",
                "no hidden pack contents, RNG state, or future choices are inspected",
            ),
        )

    BuildAwareShopBoosterPolicy.recommend = recommend
    BuildAwareShopBoosterPolicy._celestial_headroom_fast_path_installed = True
