from pathlib import Path

import games.balatro


_RETIRED_MODULES = (
    "five_run_followup_policy.py",
    "five_run_optimization_policy.py",
    "five_run_release_candidate_policy.py",
    "five_run_validation_policy.py",
    "latest_five_run_calibration_policy.py",
    "latest_five_run_resource_metrics.py",
    "latest_zero_five_survival_policy.py",
    "shop_regression_policy.py",
    "playbook_consumable_policy.py",
    "pack_playstyle.py",
    "shop_playstyle.py",
    "live/hand_playstyle.py",
    "live/runtime/playstyle_autonomous_runner.py",
    "live/build_intent_log.py",
    "latest_075105_correction_policy.py",
    "latest_batch_no_discard_policy.py",
    "live_quality_regression_policy.py",
    "v1_0_0_policy.py",
    "v1_0_0_luchador_policy.py",
)

_RETIRED_RUNTIME_TOKENS = (
    "install_five_run_followup_policy",
    "install_five_run_optimization_policy",
    "install_five_run_release_candidate_policy",
    "install_five_run_validation_policy",
    "install_latest_five_run_calibration_policy",
    "install_latest_five_run_resource_metrics",
    "install_latest_zero_five_survival_policy",
    "install_shop_regression_policy",
    "install_noncash_cash_deployment_policy",
)

_REQUIRED_BOND_RUNTIME_TOKENS = (
    "install_bond_pivot_authority",
    "install_bond_power_engine_retention_policy",
    "install_bond_prescription_policy",
    "install_bond_shop_health_policy",
    "install_strategy_plan_pack_policy",
    "install_strategy_resource_coherence_policy",
    "install_pinned_strategy_execution_policy",
)


def test_retired_strategy_and_batch_modules_are_physically_absent():
    package_dir = Path(games.balatro.__file__).resolve().parent
    for filename in _RETIRED_MODULES:
        assert not (package_dir / filename).exists(), filename


def test_production_composition_root_has_only_current_strategy_authority():
    source = Path(games.balatro.__file__).read_text(encoding="utf-8")
    for token in _RETIRED_RUNTIME_TOKENS:
        assert token not in source
    for token in _REQUIRED_BOND_RUNTIME_TOKENS:
        assert token in source
