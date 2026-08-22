from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond


def _dev():
    return BondDevelopment(
        bond_id="burnt",
        unlocked=True,
        contribution=10.0,
        rank=BondRank.R2,
        next_rank_threshold=15.0,
        contributions=(),
        target="HIGH_CARD",
        realization=BondRealization.PARTIAL,
    )


def test_burnt_is_active_before_first_discard_when_discard_remains():
    state = SimpleNamespace(discards_left=2, discards_used_this_round=0, target_hand="HIGH_CARD")
    assert realize_bond(_dev(), state).realization == BondRealization.ACTIVE


def test_burnt_drops_to_partial_after_first_discard_even_if_more_discards_remain():
    state = SimpleNamespace(discards_left=2, discards_used_this_round=1, target_hand="HIGH_CARD")
    assert realize_bond(_dev(), state).realization == BondRealization.PARTIAL


def test_explicit_first_discard_signal_remains_authoritative():
    state = SimpleNamespace(
        discards_left=2,
        discards_used_this_round=1,
        first_discard_available=True,
        target_hand="HIGH_CARD",
    )
    assert realize_bond(_dev(), state).realization == BondRealization.ACTIVE
