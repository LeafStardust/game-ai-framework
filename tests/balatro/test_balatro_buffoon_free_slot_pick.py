from types import SimpleNamespace

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER
from games.balatro.live.pack import LivePackActionGenerator, LivePackChoice


def _joker_choice(index: int, label: str) -> LivePackChoice:
    return LivePackChoice(
        area_index=index,
        address=1000 + index,
        data={
            "ability_set": "JOKER",
            "label": label,
            "live_id": 2000 + index,
        },
    )


def test_buffoon_pack_with_free_joker_slot_keeps_skip_for_d2_hold() -> None:
    state = SimpleNamespace(
        phase="BUFFOON_PACK",
        joker_slots=5,
        jokers=[object(), object(), object(), object()],
    )
    choices = [
        _joker_choice(0, "Scholar"),
        _joker_choice(1, "Jolly Joker"),
    ]

    actions = LivePackActionGenerator().generate_actions(state, choices)

    assert [action.name for action in actions] == [
        SELECT_PACK_CARD,
        SELECT_PACK_CARD,
        SKIP_BOOSTER,
    ]


def test_buffoon_pack_exposes_full_roster_replacement_candidate_and_skip() -> None:
    state = SimpleNamespace(
        phase="BUFFOON_PACK",
        joker_slots=5,
        jokers=[object(), object(), object(), object(), object()],
    )
    choices = [_joker_choice(0, "Scholar")]

    actions = LivePackActionGenerator().generate_actions(state, choices)

    assert [action.name for action in actions] == [SELECT_PACK_CARD, SKIP_BOOSTER]


def test_buffoon_pack_can_hide_capacity_blocked_candidates_for_legacy_callers() -> None:
    state = SimpleNamespace(
        phase="BUFFOON_PACK",
        joker_slots=5,
        jokers=[object(), object(), object(), object(), object()],
    )
    choices = [_joker_choice(0, "Scholar")]

    actions = LivePackActionGenerator(
        include_capacity_blocked_jokers=False,
    ).generate_actions(state, choices)

    assert [action.name for action in actions] == [SKIP_BOOSTER]
