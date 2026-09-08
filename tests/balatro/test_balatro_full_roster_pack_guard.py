from types import SimpleNamespace

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.full_roster_pack_guard import _pack_joker_fits
from games.balatro.live.pack import LivePackChoice
from games.balatro.pack_policy import BalatroPackPolicy


def _state(*, joker_count: int, joker_slots: int):
    return SimpleNamespace(
        phase="BUFFOON_PACK",
        jokers=[SimpleNamespace() for _ in range(joker_count)],
        joker_slots=joker_slots,
    )


def _choice(*, edition=None):
    data = {"ability_set": "JOKER", "label": "Joker", "center": "j_joker"}
    if edition is not None:
        data["edition"] = edition
    return LivePackChoice(0, 1, data)


def test_nonnegative_pack_joker_does_not_fit_full_roster():
    assert not _pack_joker_fits(_state(joker_count=6, joker_slots=6), _choice())


def test_pack_joker_fits_when_authoritative_capacity_exists():
    assert _pack_joker_fits(_state(joker_count=5, joker_slots=6), _choice())


def test_negative_pack_joker_is_slot_neutral_for_policy_capacity():
    assert _pack_joker_fits(
        _state(joker_count=6, joker_slots=6),
        _choice(edition="NEGATIVE"),
    )


def test_base_pack_policy_ranks_illegal_full_roster_joker_below_skip():
    policy = BalatroPackPolicy(skip_bias=0.35)
    choice = _choice()
    select = BalatroAction(SELECT_PACK_CARD, target=choice)
    skip = BalatroAction(SKIP_BOOSTER)
    ranked = policy.rank_actions(_state(joker_count=6, joker_slots=6), [select, skip])

    assert ranked[0].action.name == SKIP_BOOSTER
    joker_score = next(item for item in ranked if item.action.name == SELECT_PACK_CARD)
    assert joker_score.total < 0.35
    assert any("capacity is full" in note for note in joker_score.notes)
