from __future__ import annotations

from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.state import BalatroState


def _snapshot(**payload):
    return LiveBalatroSnapshot(
        sequence=1,
        phase="SHOP",
        state_complete=True,
        payload=payload,
    )


def test_translator_hydrates_ectoplasm_penalty_natively():
    state = DefaultBalatroStateTranslator().translate(
        _snapshot(ectoplasm_hand_size_penalty=3)
    )

    assert state.ectoplasm_hand_size_penalty == 3
    assert not hasattr(DefaultBalatroStateTranslator, "_ectoplasm_live_state_installed")


def test_round_reset_discards_are_native_and_survive_copy():
    state = DefaultBalatroStateTranslator().translate(
        _snapshot(
            round_reset_discards_observed=True,
            round_reset_discards=4,
        )
    )

    assert state.round_reset_discards_observed is True
    assert state.round_reset_discards == 4

    copied = state.copy()
    assert copied.round_reset_discards_observed is True
    assert copied.round_reset_discards == 4
    assert not hasattr(DefaultBalatroStateTranslator, "_round_resource_live_state_installed")


def test_round_reset_defaults_are_owned_by_state_without_installers():
    state = BalatroState()

    assert state.round_reset_discards_observed is False
    assert state.round_reset_discards == 0
