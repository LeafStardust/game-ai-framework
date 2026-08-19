from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER
from games.balatro.live.pack import LivePackActionGenerator, LivePackChoice
from games.balatro.state import BalatroState


def test_full_roster_buffoon_keeps_visible_jokers_for_replacement_planning():
    state = BalatroState()
    state.phase = "BUFFOON_PACK"
    state.joker_slots = 5
    state.jokers = [object() for _ in range(5)]
    choice = LivePackChoice(
        area_index=0,
        address=123,
        data={"ability_set": "JOKER", "label": "Jolly Joker"},
    )

    actions = LivePackActionGenerator().generate_actions(state, [choice])

    assert any(
        action.name == SELECT_PACK_CARD and action.target is choice
        for action in actions
    )
    assert any(action.name == SKIP_BOOSTER for action in actions)


def test_legacy_generator_can_still_hide_capacity_blocked_pack_jokers():
    state = BalatroState()
    state.phase = "BUFFOON_PACK"
    state.joker_slots = 5
    state.jokers = [object() for _ in range(5)]
    choice = LivePackChoice(
        area_index=0,
        address=123,
        data={"ability_set": "JOKER", "label": "Jolly Joker"},
    )

    actions = LivePackActionGenerator(
        include_capacity_blocked_jokers=False,
    ).generate_actions(state, [choice])

    assert all(action.name != SELECT_PACK_CARD for action in actions)
    assert any(action.name == SKIP_BOOSTER for action in actions)
