from __future__ import annotations

import games.balatro  # noqa: F401 - import installs the production policy stack
import games.balatro.bonds.composer as composer_module
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.shop_utility_scale import ShopUtilityScale


def test_h9_production_does_not_install_strategy_authority_correction_wrapper():
    assert not getattr(
        composer_module,
        "_strategy_authority_correction_installed",
        False,
    )


def test_h9_production_pack_and_shop_owners_have_no_forming_strategy_overlay():
    assert BalatroPackPolicy.score_action.__module__ != "games.balatro.strategy_authority_correction_policy"
    assert ShopUtilityScale.joker_gain.__module__ != "games.balatro.strategy_authority_correction_policy"
