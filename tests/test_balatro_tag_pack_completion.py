from __future__ import annotations

from games.balatro.live.external.live_memory_pack_terms import LivePackSelectionTerms
from games.balatro.live.injected.action_dispatcher import _pack_selection_complete
from games.balatro.live.protocol import LiveBalatroSnapshot


def _snapshot(sequence: int, phase: str, *, card_count: int) -> LiveBalatroSnapshot:
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=True,
        payload={"cards": {"cards": [{"live_id": index} for index in range(card_count)]}},
    )


def _final_standard_terms() -> LivePackSelectionTerms:
    return LivePackSelectionTerms(
        choices_remaining=1,
        choice_addresses=(1234,),
    )


def test_final_standard_tag_pack_selection_accepts_blind_select_after_card_added():
    before = _snapshot(1, "STANDARD_PACK", card_count=52)
    after = _snapshot(2, "BLIND_SELECT", card_count=53)

    assert _pack_selection_complete(
        before,
        after,
        _final_standard_terms(),
        None,
        selected_address=1234,
    )


def test_final_standard_tag_pack_selection_rejects_blind_select_without_card_added():
    before = _snapshot(1, "STANDARD_PACK", card_count=52)
    after = _snapshot(2, "BLIND_SELECT", card_count=52)

    assert not _pack_selection_complete(
        before,
        after,
        _final_standard_terms(),
        None,
        selected_address=1234,
    )


def test_final_shop_pack_selection_still_accepts_shop_terminal_phase():
    before = _snapshot(1, "STANDARD_PACK", card_count=52)
    after = _snapshot(2, "SHOP", card_count=53)

    assert _pack_selection_complete(
        before,
        after,
        _final_standard_terms(),
        None,
        selected_address=1234,
    )
