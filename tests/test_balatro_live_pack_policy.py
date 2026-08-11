from games.balatro.actions import BalatroAction, SELECT_PACK_CARD, SKIP_BOOSTER
from games.balatro.live.pack import LivePackActionGenerator, LivePackChoice
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.state import BalatroState


def _state(phase="BUFFOON_PACK"):
    state = BalatroState()
    state.phase = phase
    state.joker_slots = 5
    state.jokers = []
    return state


def test_generic_joker_choice_beats_skip():
    choice = LivePackChoice(
        area_index=0,
        address=100,
        data={
            "area_index": 0,
            "label": "Golden Joker",
            "ability_name": "Golden Joker",
            "ability_set": "Joker",
            "live_id": 1,
        },
    )
    actions = [
        BalatroAction(SELECT_PACK_CARD, target=choice),
        BalatroAction(SKIP_BOOSTER),
    ]

    ranked = BalatroPackPolicy().rank_actions(_state(), actions)

    assert ranked[0].action.name == SELECT_PACK_CARD
    assert ranked[0].action.target.area_index == 0


def test_vanilla_playing_card_can_lose_to_skip():
    choice = LivePackChoice(
        area_index=0,
        address=101,
        data={
            "area_index": 0,
            "label": None,
            "ability_set": "PLAYING_CARD",
            "live_id": 2,
            "value": {"rank": "2", "suit": "Hearts"},
            "modifier": {},
        },
    )

    ranked = BalatroPackPolicy().rank_actions(
        _state("STANDARD_PACK"),
        [BalatroAction(SELECT_PACK_CARD, target=choice), BalatroAction(SKIP_BOOSTER)],
    )

    assert ranked[0].action.name == SKIP_BOOSTER


def test_enhanced_playing_card_beats_skip():
    choice = LivePackChoice(
        area_index=0,
        address=102,
        data={
            "area_index": 0,
            "ability_set": "PLAYING_CARD",
            "live_id": 3,
            "value": {"rank": "8", "suit": "Hearts"},
            "modifier": {"enhancement": "m_gold"},
        },
    )

    ranked = BalatroPackPolicy().rank_actions(
        _state("STANDARD_PACK"),
        [BalatroAction(SELECT_PACK_CARD, target=choice), BalatroAction(SKIP_BOOSTER)],
    )

    assert ranked[0].action.name == SELECT_PACK_CARD


def test_full_joker_slots_remove_buffoon_choices():
    state = _state()
    state.jokers = [object()] * state.joker_slots
    choice = LivePackChoice(
        area_index=0,
        address=103,
        data={
            "area_index": 0,
            "label": "Banner",
            "ability_set": "Joker",
            "live_id": 4,
        },
    )

    actions = LivePackActionGenerator().generate_actions(state, [choice])

    assert [action.name for action in actions] == [SKIP_BOOSTER]


def test_targeted_tarot_is_ranked_below_skip_until_followup_is_supported():
    choice = LivePackChoice(
        area_index=0,
        address=104,
        data={
            "area_index": 0,
            "label": "The Chariot",
            "ability_name": "The Chariot",
            "ability_set": "Tarot",
            "live_id": 5,
        },
    )

    ranked = BalatroPackPolicy().rank_actions(
        _state("TAROT_PACK"),
        [BalatroAction(SELECT_PACK_CARD, target=choice), BalatroAction(SKIP_BOOSTER)],
    )

    assert ranked[0].action.name == SKIP_BOOSTER
