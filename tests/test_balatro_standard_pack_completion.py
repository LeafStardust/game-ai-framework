from games.balatro.live.external.live_memory_pack_terms import LivePackSelectionTerms
from games.balatro.live.injected.action_dispatcher import _pack_selection_complete
from games.balatro.live.injected.tag_pack_completion import (
    standard_pack_card_added,
    standard_pack_card_signature,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


def _card(
    rank,
    suit,
    *,
    enhancement=None,
    edition=None,
    seal=None,
):
    modifier = {}
    if enhancement is not None:
        modifier["enhancement"] = enhancement
    if edition is not None:
        modifier["edition"] = edition
    if seal is not None:
        modifier["seal"] = seal
    return {
        "value": {"rank": rank, "suit": suit},
        "modifier": modifier,
    }


def _snapshot(sequence, phase, owned_cards, *, complete=True):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=complete,
        payload={
            "owned_cards": {
                "count": len(owned_cards),
                "cards": list(owned_cards),
            }
        },
    )


def test_standard_pack_exact_signature_tracks_duplicate_multiplicity():
    selected = _card(
        "A",
        "Hearts",
        enhancement="m_lucky",
        edition="FOIL",
        seal="RED",
    )
    signature = standard_pack_card_signature(selected)
    assert signature is not None

    before = _snapshot(10, "STANDARD_PACK", [selected])
    after = _snapshot(11, "SHOP", [selected, selected])

    assert standard_pack_card_added(
        before,
        after,
        expected_signature=signature,
    )


def test_standard_pack_rejects_count_only_change_with_wrong_modifier():
    selected = _card(
        "A",
        "Hearts",
        enhancement="m_lucky",
        edition="FOIL",
        seal="RED",
    )
    wrong = _card(
        "A",
        "Hearts",
        enhancement="m_lucky",
        edition="POLYCHROME",
        seal="RED",
    )
    signature = standard_pack_card_signature(selected)
    assert signature is not None

    before = _snapshot(20, "STANDARD_PACK", [])
    after = _snapshot(21, "SHOP", [wrong])

    assert not standard_pack_card_added(
        before,
        after,
        expected_signature=signature,
    )


def test_multi_pick_standard_pack_requires_exact_added_card_before_replanning():
    selected = _card("K", "Spades", seal="BLUE")
    signature = standard_pack_card_signature(selected)
    assert signature is not None

    before = _snapshot(30, "STANDARD_PACK", [])
    settled = _snapshot(31, "STANDARD_PACK", [selected])
    wrong = _snapshot(31, "STANDARD_PACK", [_card("K", "Spades")])
    before_terms = LivePackSelectionTerms(
        choices_remaining=2,
        choice_addresses=(111, 222),
    )
    after_terms = LivePackSelectionTerms(
        choices_remaining=1,
        choice_addresses=(222,),
    )

    assert _pack_selection_complete(
        before,
        settled,
        before_terms,
        after_terms,
        selected_address=111,
        standard_card_signature=signature,
    )
    assert not _pack_selection_complete(
        before,
        wrong,
        before_terms,
        after_terms,
        selected_address=111,
        standard_card_signature=signature,
    )


def test_terminal_standard_pack_shop_return_requires_exact_added_card():
    selected = _card("7", "Clubs", enhancement="m_bonus")
    signature = standard_pack_card_signature(selected)
    assert signature is not None

    before = _snapshot(40, "STANDARD_PACK", [])
    settled = _snapshot(41, "SHOP", [selected])
    before_terms = LivePackSelectionTerms(
        choices_remaining=1,
        choice_addresses=(333,),
    )

    assert _pack_selection_complete(
        before,
        settled,
        before_terms,
        None,
        selected_address=333,
        standard_card_signature=signature,
    )
    assert not _pack_selection_complete(
        before,
        settled,
        before_terms,
        None,
        selected_address=333,
        standard_card_signature=None,
    )
