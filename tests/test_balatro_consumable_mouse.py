import pytest

from games.balatro.card import BalatroCard
from games.balatro.live.external.consumable_escape_live_validation import (
    verify_sun_checkpoint,
)
from games.balatro.live.external.consumable_mouse import (
    ConsumableMouseLayout,
    ConsumableMouseLayoutError,
    ExternalSunMouseExecutor,
)
from games.balatro.live.external.save_observer import _normalize_item_area
from games.balatro.live.external.viewport import NormalizedPoint
from games.balatro.state import BalatroState
from games.balatro.tarots import create_tarot


def _sun(live_id=101, area_index=0):
    consumable = create_tarot("The Sun")
    consumable.live_id = live_id
    consumable.area_index = area_index
    return consumable


def _judgement(live_id=102, area_index=1):
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
        BalatroCard("9", "Spades", live_id=1),
        BalatroCard("9", "Hearts", live_id=2),
        BalatroCard("5", "Spades", live_id=3),
        BalatroCard("5", "Hearts", live_id=4),
    ]
    state.consumables = [_sun(), _judgement()]
    return state


def test_consumable_layout_round_trips(tmp_path):
    layout = ConsumableMouseLayout(
        slot_0=NormalizedPoint(0.10, 0.20),
        slot_1=NormalizedPoint(0.20, 0.20),
        use=NormalizedPoint(0.15, 0.35),
    )
    path = tmp_path / "consumables.json"

    layout.save(path)
    loaded = ConsumableMouseLayout.load(path)

    assert loaded == layout
    assert loaded.point_for_slot(0) == NormalizedPoint(0.10, 0.20)
    assert loaded.point_for_slot(1) == NormalizedPoint(0.20, 0.20)
    assert loaded.use_point() == NormalizedPoint(0.15, 0.35)


def test_consumable_layout_rejects_unknown_slot():
    layout = ConsumableMouseLayout()

    with pytest.raises(ConsumableMouseLayoutError):
        layout.point_for_slot(2)


def test_sun_executor_requires_authoritative_area_index():
    state = _state()
    sun = state.consumables[0]
    del sun.area_index

    with pytest.raises(ConsumableMouseLayoutError, match="area_index"):
        ExternalSunMouseExecutor._validate(state, sun, (0,))


def test_sun_executor_rejects_non_sun_consumable():
    state = _state()

    with pytest.raises(ConsumableMouseLayoutError, match="only The Sun"):
        ExternalSunMouseExecutor._validate(state, state.consumables[1], (0,))


def test_save_normalization_preserves_consumable_area_index():
    areas = {
        "consumeables": {
            "config": {"card_count": 2, "card_limit": 2},
            "cards": {
                1: {
                    "sort_id": 11,
                    "ability": {"name": "The Sun", "set": "Tarot"},
                },
                2: {
                    "sort_id": 12,
                    "ability": {"name": "Judgement", "set": "Tarot"},
                },
            },
        }
    }

    normalized = _normalize_item_area(
        areas,
        "consumeables",
        "consumables",
        preserve_index=True,
    )

    assert [item["area_index"] for item in normalized["cards"]] == [0, 1]
    assert [item["live_id"] for item in normalized["cards"]] == [11, 12]


def test_verify_sun_checkpoint_accepts_exact_suit_change():
    before = _state()
    after = before.copy()
    after.hand = [
        BalatroCard(card.rank, card.suit, card.enhancement, card.edition, card.seal, card.live_id)
        for card in before.hand
    ]
    after.hand[0].suit = "Hearts"
    after.hand[2].suit = "Hearts"
    after.consumables = [_judgement()]

    reason = verify_sun_checkpoint(
        before,
        after,
        target_live_ids=(1, 3),
        sun_live_id=101,
    )

    assert reason is None


def test_verify_sun_checkpoint_rejects_wrong_target_effect():
    before = _state()
    after = before.copy()
    after.hand = [
        BalatroCard(card.rank, card.suit, card.enhancement, card.edition, card.seal, card.live_id)
        for card in before.hand
    ]
    after.consumables = [_judgement()]

    reason = verify_sun_checkpoint(
        before,
        after,
        target_live_ids=(1,),
        sun_live_id=101,
    )

    assert reason == "The Sun target live_id 1 did not become Hearts"


def test_verify_sun_checkpoint_rejects_resource_change():
    before = _state()
    after = before.copy()
    after.hand = [
        BalatroCard(card.rank, card.suit, card.enhancement, card.edition, card.seal, card.live_id)
        for card in before.hand
    ]
    after.hand[0].suit = "Hearts"
    after.consumables = [_judgement()]
    after.hands_remaining = 2

    reason = verify_sun_checkpoint(
        before,
        after,
        target_live_ids=(1,),
        sun_live_id=101,
    )

    assert reason == "hands changed during The Sun use: 3 -> 2"
