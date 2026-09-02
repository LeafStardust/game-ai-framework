from __future__ import annotations

from pathlib import Path


_RETIRED_PRODUCTION_MODULES = (
    "r0_strategy_transition_policy",
    "pinned_strategy_transition_policy",
    "pinned_strategy_retention_policy",
    "forming_strategy_retention_policy",
    "pinned_strategy_shop_goal_policy",
    "pinned_strategy_execution_policy",
    "bond_prescription_policy",
    "strategy_authority_correction_policy",
    "bond_pivot_authority",
    "bond_power_engine_retention_policy",
)


def test_h14_retired_strategy_controllers_are_absent_from_production_registration():
    package_source = (
        Path(__file__).resolve().parents[2] / "games" / "balatro" / "__init__.py"
    ).read_text(encoding="utf-8")

    for module_name in _RETIRED_PRODUCTION_MODULES:
        assert module_name not in package_source


def test_h14_canonical_persistent_owner_integrations_remain_registered():
    package_source = (
        Path(__file__).resolve().parents[2] / "games" / "balatro" / "__init__.py"
    ).read_text(encoding="utf-8")

    assert "install_post_transaction_joker_value_policy()" in package_source
    assert "install_strategy_plan_pack_policy()" in package_source
    assert "install_strategy_resource_coherence_policy()" in package_source
    assert "install_stateful_joker_admission_policy()" in package_source
    assert "install_live_decision_quality_policy()" in package_source
