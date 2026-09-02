from __future__ import annotations

import inspect

import games.balatro
from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy


def test_h10_production_d2_has_no_generic_bond_pivot_controller():
    assert not getattr(
        PlaybookJokerAcquisitionPolicy,
        "_bond_pivot_authority_installed",
        False,
    )


def test_h10_package_registration_does_not_install_bond_pivot_controller():
    source = inspect.getsource(games.balatro)
    assert "install_bond_pivot_authority" not in source
