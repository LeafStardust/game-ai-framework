from __future__ import annotations

from games.balatro.actions import SKIP_BOOSTER, BalatroAction
from games.balatro.live.external.live_memory_pack_terms import LivePackSelectionTerms
from games.balatro.live.injected.action_dispatcher import (
    LiveMemoryInjectedActionDispatcher,
    _pack_selection_complete,
)
from games.balatro.live.injected.tag_pack_completion import standard_pack_card_signature
from games.balatro.live.protocol import LiveBalatroSnapshot


def _standard_card():
    return {
        "value": {"rank": "A", "suit": "Hearts"},
        "modifier": {
            "enhancement": "m_bonus",
            "edition": "FOIL",
            "seal": "RED",
        },
    }


def _standard_signature():
    signature = standard_pack_card_signature(_standard_card())
    assert signature is not None
    return signature


def _snapshot(
    sequence: int,
    phase: str,
    *,
    card_count: int,
    include_selected_standard: bool = False,
) -> LiveBalatroSnapshot:
    cards = [
        {
            "live_id": index,
            "value": {"rank": "2", "suit": "Clubs"},
            "modifier": {},
        }
        for index in range(card_count)
    ]
    if include_selected_standard:
        if not cards:
            raise ValueError("selected Standard card requires at least one card")
        cards[-1] = {"live_id": card_count - 1, **_standard_card()}
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=True,
        payload={"owned_cards": {"cards": cards}},
    )


def _final_standard_terms() -> LivePackSelectionTerms:
    return LivePackSelectionTerms(
        choices_remaining=1,
        choice_addresses=(1234,),
    )


def test_final_standard_tag_pack_selection_accepts_blind_select_after_card_added():
    before = _snapshot(1, "STANDARD_PACK", card_count=52)
    after = _snapshot(
        2,
        "BLIND_SELECT",
        card_count=53,
        include_selected_standard=True,
    )

    assert _pack_selection_complete(
        before,
        after,
        _final_standard_terms(),
        None,
        selected_address=1234,
        standard_card_signature=_standard_signature(),
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
        standard_card_signature=_standard_signature(),
    )


def test_final_buffoon_tag_pack_selection_accepts_blind_select_terminal_phase():
    before = _snapshot(1, "BUFFOON_PACK", card_count=52)
    after = _snapshot(2, "BLIND_SELECT", card_count=52)

    assert _pack_selection_complete(
        before,
        after,
        _final_standard_terms(),
        None,
        selected_address=1234,
    )


def test_nonfinal_pack_selection_rejects_blind_select_terminal_phase():
    before = _snapshot(1, "BUFFOON_PACK", card_count=52)
    after = _snapshot(2, "BLIND_SELECT", card_count=52)
    terms = LivePackSelectionTerms(
        choices_remaining=2,
        choice_addresses=(1234, 5678),
    )

    assert not _pack_selection_complete(
        before,
        after,
        terms,
        None,
        selected_address=1234,
    )


def test_intermediate_pack_selection_stays_in_pack_and_decrements_choices():
    before = _snapshot(1, "BUFFOON_PACK", card_count=52)
    after = _snapshot(2, "BUFFOON_PACK", card_count=52)
    before_terms = LivePackSelectionTerms(
        choices_remaining=2,
        choice_addresses=(1234, 5678),
    )
    after_terms = LivePackSelectionTerms(
        choices_remaining=1,
        choice_addresses=(5678,),
    )

    assert _pack_selection_complete(
        before,
        after,
        before_terms,
        after_terms,
        selected_address=1234,
    )


def test_intermediate_pack_selection_rejects_shop_terminal_phase():
    before = _snapshot(1, "BUFFOON_PACK", card_count=52)
    after = _snapshot(2, "SHOP", card_count=52)
    terms = LivePackSelectionTerms(
        choices_remaining=2,
        choice_addresses=(1234, 5678),
    )

    assert not _pack_selection_complete(
        before,
        after,
        terms,
        None,
        selected_address=1234,
    )


def test_final_pack_selection_rejects_unrelated_terminal_phase():
    before = _snapshot(1, "BUFFOON_PACK", card_count=52)
    after = _snapshot(2, "ROUND_EVAL", card_count=52)

    assert not _pack_selection_complete(
        before,
        after,
        _final_standard_terms(),
        None,
        selected_address=1234,
    )


def test_final_shop_pack_selection_still_accepts_shop_terminal_phase():
    before = _snapshot(1, "STANDARD_PACK", card_count=52)
    after = _snapshot(
        2,
        "SHOP",
        card_count=53,
        include_selected_standard=True,
    )

    assert _pack_selection_complete(
        before,
        after,
        _final_standard_terms(),
        None,
        selected_address=1234,
        standard_card_signature=_standard_signature(),
    )


class _Observer:
    def __init__(self, snapshot: LiveBalatroSnapshot) -> None:
        self.snapshot = snapshot

    def observe(self) -> LiveBalatroSnapshot:
        return self.snapshot


class _Bridge:
    def __init__(self) -> None:
        self.skipped = False

    def skip_booster(self) -> None:
        self.skipped = True


def test_tag_opened_pack_skip_accepts_blind_select_terminal_phase():
    before = _snapshot(1, "BUFFOON_PACK", card_count=52)
    after = _snapshot(2, "BLIND_SELECT", card_count=52)
    bridge = _Bridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        _Observer(after),
        bridge=bridge,
        timeout=0,
        poll_interval=0,
    )

    result = dispatcher.dispatch(
        BalatroAction(SKIP_BOOSTER),
        snapshot=before,
    )

    assert bridge.skipped
    assert result.after == after
