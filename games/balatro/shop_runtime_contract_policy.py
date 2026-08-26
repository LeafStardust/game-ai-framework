from __future__ import annotations

"""Final SHOP runtime boundaries for Red/White production.

SHOP arbitration composes D2 acquisition, D8 booster value, D11 rerolls, Build
Health and D14. Hypothetical transitions inside those authorities must not launch a
second whole-blind D1 search, and the retired named two-Joker bundle planner must not
override the canonical Bond/D14 result after arbitration has already completed.

This module contains no gameplay tier list, hidden-state prediction or numerical
retuning. It only prevents nested planner work and retires an obsolete parallel shop
authority.
"""

import games.balatro.build_health_policy as build_health_policy
from games.balatro.build_health_runtime import projected_state_with_jokers
from games.balatro.build_health_policy import PlaybookBuildHealthShopArbiter


_PROJECTION_FLAG = "_rw_internal_build_health_projection"


def install_shop_runtime_contract_policy() -> None:
    if getattr(PlaybookBuildHealthShopArbiter, "_rw_runtime_contract_installed", False):
        return

    def projected_health(state, jokers):
        projected = projected_state_with_jokers(state, jokers)
        # Internal-only marker. It is not serialized public state and carries no
        # gameplay information. The SHOP survival adapter uses it solely to avoid
        # recursively invoking bounded D1 inside a D2/D14 hypothetical branch.
        setattr(projected, _PROJECTION_FLAG, True)
        return build_health_policy._HEALTH.evaluate(projected)

    def no_legacy_named_bundle(self, state, result):
        del state
        # The canonical Bond/composition and D14 decision is already complete.
        # Do not re-open arbitration with the retired hard-coded pair catalogue.
        return result

    build_health_policy._projected_health = projected_health
    PlaybookBuildHealthShopArbiter._bundle_decision = no_legacy_named_bundle
    PlaybookBuildHealthShopArbiter._rw_runtime_contract_installed = True
