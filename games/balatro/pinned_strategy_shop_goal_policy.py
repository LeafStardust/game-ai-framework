from __future__ import annotations

"""Deprecated compatibility shim for the removed D14 pinned strategy wrapper.

Phase H moved Joker strategic value into the canonical H1 post-transaction
StrategyDelta path. Historical strategy-plan goals, pinned strategy IDs, Bond
candidates, and seek-feature prescriptions are no longer D14 scoring authority.
Keep the installer symbol temporarily so stale imports do not fail during migration
cleanup, but it must never monkey-patch ShopUtilityScale again.
"""


def install_pinned_strategy_shop_goal_policy() -> None:
    """Compatibility no-op; legacy pinned shop-goal authority is retired."""
    return None
