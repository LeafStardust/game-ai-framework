from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond


def _dev():
    return BondDevelopment(
        bond_id="hand_leveling",
        unlocked=True,
        contribution=10.0,
        rank=BondRank.R2,
        next_rank_threshold=15.0,
        contributions=(),
        target="HIGH_CARD",
        realization=BondRealization.PARTIAL,
    )


def test_hand_leveling_realizes_from_burnt_engine():
    state = SimpleNamespace(
        jokers=[SimpleNamespace(name="Burnt Joker")],
        vouchers=[],
        owned_deck=[],
        hand_levels={"HIGH_CARD": 1},
    )
    assert realize_bond(_dev(), state).realization == BondRealization.ACTIVE


def test_hand_leveling_realizes_from_non_burnt_infrastructure():
    state = SimpleNamespace(
        jokers=[SimpleNamespace(name="Space Joker")],
        vouchers=[SimpleNamespace(name="Telescope")],
        owned_deck=[],
        hand_levels={"HIGH_CARD": 1},
    )
    assert realize_bond(_dev(), state).realization == BondRealization.ACTIVE


def test_first_discard_telemetry_does_not_control_axis_realization():
    state = SimpleNamespace(
        jokers=[SimpleNamespace(name="Burnt Joker")],
        vouchers=[],
        owned_deck=[],
        hand_levels={"HIGH_CARD": 1},
        discards_left=0,
        discards_used_this_round=1,
        first_discard_available=False,
    )
    assert realize_bond(_dev(), state).realization == BondRealization.ACTIVE
