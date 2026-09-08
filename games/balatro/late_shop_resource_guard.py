from __future__ import annotations

"""Late-shop reserve guard for marginal side-development boosters.

The 2026-08-23 five-run batch included an Ante-6 shop that spent its final $6 on a
Jumbo Celestial Pack immediately after dismantling its realized power engine.  The
pack barely cleared D8 admission while Build Health already reported 100 survival
and a scaling deficit.  In that state liquid cash for Joker search is more valuable
than a marginal side pack.
"""

from dataclasses import replace

from games.balatro.build_health_runtime import RuntimeBuildHealthEvaluator
from games.balatro.shop_booster_policy import HOLD, BuildAwareShopBoosterPolicy


_HEALTH = RuntimeBuildHealthEvaluator()
_LATE_SIDE_FAMILIES = frozenset({"STANDARD", "ARCANA", "CELESTIAL"})


def install_late_shop_resource_guard() -> None:
    if getattr(BuildAwareShopBoosterPolicy, "_late_shop_resource_guard_installed", False):
        return

    original_recommend = BuildAwareShopBoosterPolicy.recommend

    def recommend(self, state, action):
        result = original_recommend(self, state, action)
        if not result.should_buy:
            return result

        ante = max(1, int(getattr(state, "ante", 1) or 1))
        family = str(getattr(result, "family", "") or "").upper()
        if ante < 5 or family not in _LATE_SIDE_FAMILIES:
            return result

        price = self._price(action.target)
        money = max(0, int(getattr(state, "money", 0) or 0))
        money_after = money - price
        if money_after >= 10:
            return result

        health = _HEALTH.evaluate(state)
        survival = float(getattr(health, "survival", 0.0) or 0.0)
        # In immediate danger, an admitted pack may still be the only available
        # rescue line. When current survival is already comfortable, do not drain
        # the last search reserve for a merely marginal side-development pack.
        if survival < 85.0:
            return result

        advantage = float(getattr(result, "total", 0.0) or 0.0)
        if advantage >= 2.0:
            return result

        return replace(
            result,
            decision=HOLD,
            total=float(self.parent_hold_baseline),
            rationale=(
                *result.rationale,
                "late-shop reserve guard: comfortable immediate survival does not justify draining liquid cash for a marginal side-development pack",
                f"Ante {ante}; family={family}; cash ${money} -> ${money_after}; survival={survival:.1f}; admitted advantage={advantage:.3f}",
                "retain at least $10 for direct Joker search/replacement unless the pack is materially stronger or immediate survival is endangered",
            ),
        )

    BuildAwareShopBoosterPolicy.recommend = recommend
    BuildAwareShopBoosterPolicy._late_shop_resource_guard_installed = True
