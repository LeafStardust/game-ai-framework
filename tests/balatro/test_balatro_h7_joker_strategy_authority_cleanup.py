from __future__ import annotations

import games.balatro  # noqa: F401 - import installs the production policy stack
import games.balatro.joker_policy as joker_policy
from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy


def test_h7_production_d2_keeps_canonical_strategy_delta_owner_unwrapped():
    transition = joker_policy._bond_transition_bonus

    assert transition.__module__ == "games.balatro.joker_policy"
    assert transition.__name__ == "_bond_transition_bonus"
    assert not getattr(joker_policy, "_pinned_strategy_transition_installed", False)


def test_h7_production_d2_has_no_pinned_or_forming_strategy_retention_controller():
    assert not getattr(
        PlaybookJokerAcquisitionPolicy,
        "_pinned_strategy_retention_installed",
        False,
    )
    assert not getattr(
        PlaybookJokerAcquisitionPolicy,
        "_forming_strategy_retention_installed",
        False,
    )
