"""Compatibility boundary for the retired categorical shop-playstyle layer.

The old module name remains importable because the production runner and several
mechanical policies still share the shop estimator through this import path.
Strategic direction no longer comes from categorical playstyle intent here;
Bond/StrategyPlan layers own that authority.  This class therefore delegates to
the canonical default shop estimator without adding any playstyle bonuses,
penalties, locking, or persistence.
"""

from __future__ import annotations

from games.balatro.shop_policy import DefaultShopItemValueEstimator


class BuildAwareShopItemValueEstimator(DefaultShopItemValueEstimator):
    """Legacy import-compatible name with no categorical playstyle authority."""

    pass
