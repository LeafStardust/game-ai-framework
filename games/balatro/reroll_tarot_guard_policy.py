from __future__ import annotations

"""Remove D11's synthetic future-Tarot gross utility from production.

The current B4 held-consumable model intentionally reports structural build-path
units, not run-winning/shop utility. Treating its output—or the historical fixed
``3.2`` Tarot prior—as directly comparable with literal D2/D14 Joker value would
reintroduce the cross-family unit defect. Until a complete held-Tarot option model
exists, the future Tarot branch is therefore worth only the END_SHOP baseline.
"""

from games.balatro.shop_reroll_policy import BuildAwareShopRerollPolicy


def install_reroll_tarot_guard_policy() -> None:
    if getattr(BuildAwareShopRerollPolicy, "_tarot_fail_closed_installed", False):
        return

    original_future_offer_score = BuildAwareShopRerollPolicy._future_offer_score

    def future_offer_score(self, state, offer, *, money: int, thresholds):
        if str(getattr(offer, "family", "")).upper() == "TAROT":
            return float(self.shop_policy.hold_bias)
        return original_future_offer_score(
            self,
            state,
            offer,
            money=money,
            thresholds=thresholds,
        )

    BuildAwareShopRerollPolicy._future_offer_score = future_offer_score
    BuildAwareShopRerollPolicy._tarot_fail_closed_installed = True
