from games.balatro.card import BalatroCard
from games.balatro.live.injected.consumable_target_postcondition import (
    build_consumable_target_postcondition_for_consumable,
)
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.state import BalatroState
from games.balatro.tarots import HangedMan, Magician


def _card_record(card: BalatroCard, *, enhancement: str | None = None) -> dict:
    return {
        "live_id": card.live_id,
        "value": {
            "rank": card.rank,
            "suit": card.suit,
        },
        "modifier": {
            "enhancement": card.enhancement if enhancement is None else enhancement,
            "edition": card.edition,
            "seal": card.seal,
        },
    }


def _snapshot(*, hand: list[dict], owned_cards: list[dict]) -> LiveBalatroSnapshot:
    return LiveBalatroSnapshot(
        sequence=2,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "hand": {"cards": hand},
            "owned_cards": {"cards": owned_cards},
        },
    )


def test_hanged_man_verifies_destroyed_targets_leave_current_hand_not_owned_cards():
    state = BalatroState()
    first = BalatroCard("2", "Clubs", live_id="first")
    second = BalatroCard("3", "Diamonds", live_id="second")
    survivor = BalatroCard("A", "Spades", live_id="survivor")
    state.hand = [first, second, survivor]

    postcondition = build_consumable_target_postcondition_for_consumable(
        state,
        consumable=HangedMan(),
        target_indices=(0, 1),
    )

    assert postcondition is not None
    assert postcondition.expected_targets == ()
    assert postcondition.expected_hand_absent_live_ids == ("first", "second")
    assert postcondition.live_ids == ("first", "second")

    owned_records = [
        _card_record(first),
        _card_record(second),
        _card_record(survivor),
    ]
    after = _snapshot(
        hand=[_card_record(survivor)],
        owned_cards=owned_records,
    )
    assert postcondition.matches(after)

    still_in_hand = _snapshot(
        hand=[_card_record(first), _card_record(survivor)],
        owned_cards=owned_records,
    )
    assert not postcondition.matches(still_in_hand)

    hand_not_observed = LiveBalatroSnapshot(
        sequence=2,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={"owned_cards": {"cards": owned_records}},
    )
    assert not postcondition.matches(hand_not_observed)


def test_transformative_consumable_still_requires_exact_owned_card_mutation():
    state = BalatroState()
    target = BalatroCard("K", "Hearts", live_id="target")
    state.hand = [target]

    postcondition = build_consumable_target_postcondition_for_consumable(
        state,
        consumable=Magician(),
        target_indices=(0,),
    )

    assert postcondition is not None
    assert postcondition.expected_hand_absent_live_ids == ()
    assert postcondition.expected_targets == (
        ("target", ("K", "Hearts", "Lucky", None, None)),
    )

    unchanged = _snapshot(
        hand=[_card_record(target)],
        owned_cards=[_card_record(target)],
    )
    assert not postcondition.matches(unchanged)

    transformed = _snapshot(
        hand=[_card_record(target, enhancement="Lucky")],
        owned_cards=[_card_record(target, enhancement="Lucky")],
    )
    assert postcondition.matches(transformed)
