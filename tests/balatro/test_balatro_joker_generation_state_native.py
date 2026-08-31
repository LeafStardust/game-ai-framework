from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.state import BalatroState


def test_joker_generation_state_is_native_to_state_and_translator():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SHOP",
        state_complete=True,
        payload={
            "joker_generation_pool_observed": True,
            "joker_generation_pools": {
                "COMMON": [
                    {
                        "center": "j_joker",
                        "label": "Joker",
                        "ability_name": "Joker",
                        "ability_set": "JOKER",
                        "rarity": "COMMON",
                    }
                ]
            },
            "joker_generation_edition_rate": 2.5,
            "visible_poker_hands": ["High Card", "Pair"],
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert state.joker_generation_pool_observed is True
    assert state.joker_generation_pools["COMMON"][0]["center"] == "j_joker"
    assert state.joker_generation_edition_rate == 2.5
    assert state.visible_poker_hands == ("High Card", "Pair")

    copied = state.copy()
    assert copied.joker_generation_pool_observed is True
    assert copied.joker_generation_pools == state.joker_generation_pools
    assert copied.joker_generation_pools is not state.joker_generation_pools
    assert copied.joker_generation_pools["COMMON"] is not state.joker_generation_pools["COMMON"]
    assert copied.joker_generation_edition_rate == 2.5
    assert copied.visible_poker_hands == ("High Card", "Pair")

    assert not hasattr(DefaultBalatroStateTranslator, "_joker_generation_pool_live_state_installed")


def test_default_state_owns_joker_generation_fields_without_installer():
    state = BalatroState()

    assert state.joker_generation_pool_observed is False
    assert state.joker_generation_pools == {}
    assert state.joker_generation_edition_rate == 1.0
    assert state.visible_poker_hands == ()
