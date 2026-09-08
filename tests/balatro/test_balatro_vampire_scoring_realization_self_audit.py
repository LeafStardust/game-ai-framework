from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond


def _card(rank="2", enhancement=""):
    return SimpleNamespace(rank=rank, enhancement=enhancement)


def _dev():
    return BondDevelopment(
        bond_id="enhancement_consumption",
        unlocked=True,
        contribution=22.0,
        rank=BondRank.R4,
        next_rank_threshold=30.0,
        contributions=(),
        realization=BondRealization.PARTIAL,
    )


def test_enhancement_consumption_is_active_with_consumer_and_owned_feedstock():
    enhanced = _card("9", "Gold")
    state = SimpleNamespace(
        jokers=[SimpleNamespace(name="Vampire")],
        hand=[enhanced],
        scoring_cards=[],
        owned_deck=[enhanced],
    )
    assert realize_bond(_dev(), state).realization == BondRealization.ACTIVE


def test_enhancement_consumption_remains_active_when_feedstock_is_scoring_now():
    enhanced = _card("9", "Gold")
    state = SimpleNamespace(
        jokers=[SimpleNamespace(name="Vampire")],
        hand=[enhanced],
        scoring_cards=[enhanced],
        owned_deck=[enhanced],
    )
    assert realize_bond(_dev(), state).realization == BondRealization.ACTIVE
