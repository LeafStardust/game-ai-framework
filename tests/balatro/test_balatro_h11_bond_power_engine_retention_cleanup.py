from __future__ import annotations

import inspect

import games.balatro
from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy


def test_h11_production_d2_has_no_bond_power_engine_retention_controller():
    assert not getattr(
        PlaybookJokerAcquisitionPolicy,
        "_bond_power_engine_retention_installed",
        False,
    )


def test_h11_package_does_not_install_bond_power_engine_retention_wrapper():
    source = inspect.getsource(games.balatro)

    assert "install_bond_power_engine_retention_policy" not in source
