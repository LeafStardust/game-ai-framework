from types import SimpleNamespace

import pytest

from games.balatro.card import BalatroCard
from games.balatro.live.external.consumable_mouse import ConsumableMouseLayoutError
from games.balatro.live.external.judgement_live_validation import (
    _projection_status,
    verify_judgement_checkpoint,
)
from games.balatro.live.external.judgement_mouse import ExternalJudgementMouseExecutor
from games.balatro.state import BalatroState
from games.balatro.tarots import create_tarot


def _judgement(live_id=145, area_index=1):
    consumable = create_tarot("Judgement")
    consumable.live_id = live_id
    consumable.area_index = area_index
    return consumable


def _state():
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.score = 2064
    state.hands_remaining = 3
    state.discards_remaining = 0
    state.hand = [
        BalatroCard("J", "Spades", live_id=1),
        BalatroCard("10", "Clubs", live_id=2),
        BalatroCard("9", "Hearts", live_id=3),
    ]
    state.jokers = [object()]
    state.joker_slots = 5
    state.consumables = [_judgement()]
    return state


def _snapshot(*, consumables, jokers):
    return SimpleNamespace(
        payload={
            "consumables": {"cards": consumables},
            "jokers": {"cards": jokers},
        }
    )


def test_judgement_executor_accepts_available_joker_slot():
    state = _state()

    ExternalJudgementMouseExecutor._validate(state, state.consumables[0])


def test_judgement_executor_rejects_full_joker_slots():
    state = _state()
    state.jokers = [object() for _ in range(5)]

    with pytest.raises(ConsumableMouseLayoutError, match="no Joker slot"):
        ExternalJudgementMouseExecutor._validate(state, state.consumables[0])


def test_verify_judgement_checkpoint_accepts_one_new_joker():
    before = _state()
    after = before.copy()
    after.hand = [
        BalatroCard(
            card.rank,
            card.suit,
            card.enhancement,
            card.edition,
            card.seal,
            card.live_id,
        )
        for card in before.hand
    ]
    after.consumables = []

    before_snapshot = _snapshot(
        consumables=[{"live_id": 145, "label": "Judgement"}],
        jokers=[{"live_id": 10, "label": "Bootstraps"}],
    )
    after_snapshot = _snapshot(
        consumables=[],
        jokers=[
            {"live_id": 10, "label": "Bootstraps"},
            {"live_id": 11, "label": "Joker"},
        ],
    )

    reason, created = verify_judgement_checkpoint(
        before,
        after,
        before_snapshot,
        after_snapshot,
        judgement_live_id=145,
    )

    assert reason is None
    assert created == {"live_id": 11, "label": "Joker"}


def test_verify_judgement_checkpoint_rejects_missing_created_joker():
    before = _state()
    after = before.copy()
    after.hand = [
        BalatroCard(
            card.rank,
            card.suit,
            card.enhancement,
            card.edition,
            card.seal,
            card.live_id,
        )
        for card in before.hand
    ]
    after.consumables = []

    before_snapshot = _snapshot(
        consumables=[{"live_id": 145, "label": "Judgement"}],
        jokers=[{"live_id": 10, "label": "Bootstraps"}],
    )
    after_snapshot = _snapshot(
        consumables=[],
        jokers=[{"live_id": 10, "label": "Bootstraps"}],
    )

    reason, created = verify_judgement_checkpoint(
        before,
        after,
        before_snapshot,
        after_snapshot,
        judgement_live_id=145,
    )

    assert reason == "Joker count did not increase by exactly one: 1 -> 1"
    assert created is None


def test_verify_judgement_checkpoint_rejects_hand_mutation():
    before = _state()
    after = before.copy()
    after.hand = [
        BalatroCard(
            card.rank,
            card.suit,
            card.enhancement,
            card.edition,
            card.seal,
            card.live_id,
        )
        for card in before.hand
    ]
    after.hand[0].suit = "Hearts"
    after.consumables = []

    reason, created = verify_judgement_checkpoint(
        before,
        after,
        _snapshot(
            consumables=[{"live_id": 145, "label": "Judgement"}],
            jokers=[{"live_id": 10, "label": "Bootstraps"}],
        ),
        _snapshot(
            consumables=[],
            jokers=[
                {"live_id": 10, "label": "Bootstraps"},
                {"live_id": 11, "label": "Joker"},
            ],
        ),
        judgement_live_id=145,
    )

    assert reason == "hand card live_id 1 changed during Judgement use"
    assert created is None


def test_projection_status_accepts_bootstraps():
    supported, reason = _projection_status(
        {
            "live_id": 11,
            "label": "Bootstraps",
            "ability_name": "Bootstraps",
            "center": "j_bootstraps",
        }
    )

    assert supported is True
    assert "validated" in reason


def test_projection_status_blocks_unvalidated_framework_joker():
    supported, reason = _projection_status(
        {
            "live_id": 11,
            "label": "Acrobat",
            "ability_name": "Acrobat",
            "center": "j_acrobat",
        }
    )

    assert supported is False
    assert "not yet validated" in reason
