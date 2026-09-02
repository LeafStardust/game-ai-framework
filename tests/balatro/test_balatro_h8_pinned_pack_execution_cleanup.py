from __future__ import annotations

import inspect

import games.balatro  # noqa: F401 - import installs the production policy stack
import games.balatro.bond_prescription_policy as prescriptions
import games.balatro as balatro_package


def test_h8_production_d9_does_not_install_pinned_strategy_execution():
    assert not getattr(
        prescriptions,
        "_pinned_strategy_execution_installed",
        False,
    )


def test_h8_package_registration_does_not_reference_pinned_execution_installer():
    source = inspect.getsource(balatro_package)

    assert "install_pinned_strategy_execution_policy" not in source
    assert "pinned_strategy_execution_policy" not in source
