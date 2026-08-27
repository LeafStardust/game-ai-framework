from __future__ import annotations

"""Compatibility retirement for historical Build-Health shop post-arbiters.

Visible two-Joker Bond planning now lives directly in ``BuildAwareShopArbiter`` and
competes in D14's canonical normalized candidate set. This installer remains only
because ``build_health_policy`` still contains historical bundle/reroll callback
slots that are resolved dynamically at runtime. Both are forced to identity here so
Build Health contributes D2 evidence without becoming a second global shop arbiter.
"""

from games.balatro.shop_arbiter import BuildAwareShopArbiter


def _retire_legacy_post_arbiter(state, result, *args):
    """Keep historical Build-Health post-arbiter rescues out of production."""
    del state, args
    return result


def install_bond_visible_shop_bundle_policy() -> None:
    if getattr(BuildAwareShopArbiter, "_bond_visible_shop_bundle_installed", False):
        return

    import games.balatro.build_health_policy as build_health_policy

    build_health_policy._bundle_decision = _retire_legacy_post_arbiter
    build_health_policy._health_reroll_decision = _retire_legacy_post_arbiter
    BuildAwareShopArbiter._bond_visible_shop_bundle_installed = True
