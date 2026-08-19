from games.balatro.card import BalatroCard
from games.balatro.live.injected.consumable_target_postcondition import (
    build_consumable_target_postcondition_for_consumable,
)
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.spectrals import Aura
from games.balatro.state import BalatroState


def _snapshot(*, live_id=101, rank="K", edition="FOIL") -> LiveBalatroSnapshot:
    return LiveBalatroSnapshot(
        sequence=2,
        phase="SPECTRAL_PACK",
        state_complete=True,
        payload={
            "hand": {
                "cards": [
                    {
                        "live_id": live_id,
                        "value": {"rank": rank, "suit": "H"},
                        "modifier": {"edition": edition},
                    }
                ]
            }
        },
    )


def test_aura_postcondition_accepts_only_legal_edition_outcomes_on_same_live_card():
    state = BalatroState()
    state.phase = "SPECTRAL_PACK"
    state.hand = [BalatroCard("K", "Hearts", live_id=101)]

    postcondition = build_consumable_target_postcondition_for_consumable(
        state,
        consumable=Aura(),
        target_indices=(0,),
    )

    assert postcondition is not None
    assert postcondition.live_ids == (101,)
    assert postcondition.matches(_snapshot(edition="FOIL"))
    assert postcondition.matches(_snapshot(edition="HOLO"))
    assert postcondition.matches(_snapshot(edition="POLYCHROME"))
    assert not postcondition.matches(_snapshot(edition="NEGATIVE"))
    assert not postcondition.matches(_snapshot(rank="Q", edition="FOIL"))
    assert not postcondition.matches(_snapshot(live_id=202, edition="FOIL"))


def test_aura_postcondition_fails_closed_for_existing_edition_overwrite():
    state = BalatroState()
    state.phase = "SPECTRAL_PACK"
    state.hand = [BalatroCard("K", "Hearts", edition="Foil", live_id=101)]

    assert (
        build_consumable_target_postcondition_for_consumable(
            state,
            consumable=Aura(),
            target_indices=(0,),
        )
        is None
    )
