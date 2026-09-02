from __future__ import annotations

from pathlib import Path

from games.balatro.bond_prescription_policy import install_bond_prescription_policy
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.shop_utility_scale import ShopUtilityScale


def test_h6_bond_prescription_installer_is_compatibility_noop():
    before_pack = BalatroPackPolicy.score_action
    before_consumable = ShopUtilityScale.consumable_gain

    install_bond_prescription_policy()

    assert BalatroPackPolicy.score_action is before_pack
    assert ShopUtilityScale.consumable_gain is before_consumable
    assert not getattr(BalatroPackPolicy, "_bond_prescription_policy_installed", False)
    assert not getattr(ShopUtilityScale, "_bond_prescription_policy_installed", False)


def test_h6_production_package_does_not_install_bond_prescription_wrapper():
    package_source = (
        Path(__file__).resolve().parents[2] / "games" / "balatro" / "__init__.py"
    ).read_text(encoding="utf-8")

    assert "bond_prescription_policy" not in package_source
    assert "install_bond_prescription_policy" not in package_source


def test_h6_compatibility_shim_contains_no_manual_execution_bonus_tables():
    shim_source = (
        Path(__file__).resolve().parents[2]
        / "games"
        / "balatro"
        / "bond_prescription_policy.py"
    ).read_text(encoding="utf-8")

    rejected_tokens = (
        "prescription_bonus",
        "baron_mime_steel",
        "photograph_hanging_chad",
        "vampire_midas",
        "burnt_target_level",
        "low_rank_hack_retrigger",
        "_MAX_PACK_BONUS",
        "_MAX_SHOP_BONUS",
    )
    for token in rejected_tokens:
        assert token not in shim_source
