from types import SimpleNamespace

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER
from games.balatro.live.pack import LivePackActionGenerator, LivePackChoice


class BlueJoker:
    pass


def test_arcana_pack_does_not_offer_hanged_man_while_blue_joker_is_owned() -> None:
    state = SimpleNamespace(
        phase="TAROT_PACK",
        joker_slots=5,
        jokers=[BlueJoker()],
    )
    choice = LivePackChoice(
        area_index=0,
        address=100,
        data={
            "ability_set": "TAROT",
            "label": "The Hanged Man",
            "live_id": 200,
        },
    )

    actions = LivePackActionGenerator().generate_actions(state, [choice])

    assert [action.name for action in actions] == [SKIP_BOOSTER]
    assert all(action.name != SELECT_PACK_CARD for action in actions)
