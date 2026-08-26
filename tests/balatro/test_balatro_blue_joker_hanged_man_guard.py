from types import SimpleNamespace

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER
from games.balatro.live.pack import LivePackActionGenerator, LivePackChoice


class BlueJoker:
    pass


def test_arcana_pack_keeps_hanged_man_candidate_with_blue_joker_owned() -> None:
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

    # Blue Joker no longer hard-vetoes Hanged Man. D6 evaluates the exact
    # +2-Chips-per-remaining-card opportunity cost against the thinning target.
    assert [action.name for action in actions] == [SELECT_PACK_CARD, SKIP_BOOSTER]
