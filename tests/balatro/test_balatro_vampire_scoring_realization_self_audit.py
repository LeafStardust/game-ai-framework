from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond


def _card(rank="2", enhancement=""):
    return SimpleNamespace(rank=rank, enhancement=enhancement)


def _dev():
    return BondDevelopment(
        bond_id="vampire",
        unlocked=True,
        contribution=22.0,
        rank=BondRank.R4,
        next_rank_threshold=30.0,
        contributions=(),
        realization=BondRealization.PARTIAL,
    )


def test_vampire_does_not_feed_from_non_scoring_enhanced_card_when_scoring_telemetry_is_present():
    enhanced = _card("9", "Gold")
    state = SimpleNamespace(
        jokers=[SimpleNamespace(name="Vampire")],
        hand=[enhanced],
        scoring_cards=[],
        owned_deck=[enhanced],
    )
    assert realize_bond(_dev(), state).realization == BondRealization.PARTIAL


def test_vampire_feeds_from_enhanced_scoring_card():
    enhanced = _card("9", "Gold")
    state = SimpleNamespace(
        jokers=[SimpleNamespace(name="Vampire")],
        hand=[enhanced],
        scoring_cards=[enhanced],
        owned_deck=[enhanced],
    )
    assert realize_bond(_dev(), state).realization == BondRealization.ACTIVE
