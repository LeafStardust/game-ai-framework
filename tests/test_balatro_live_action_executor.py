import pytest

from games.balatro.actions import (
    BalatroAction,
    DISCARD_CARDS,
    PLAY_CARDS,
)
from games.balatro.card import BalatroCard
from games.balatro.live import (
    DefaultBalatroActionExecutor,
    LiveBalatroSnapshot,
)


def test_action_executor_maps_selected_card_indices():
    executor = DefaultBalatroActionExecutor()
    snapshot = LiveBalatroSnapshot(
        sequence=12,
        phase="SELECTING_HAND",
        state_complete=True,
    )
    cards = [
        BalatroCard("A", "Spades", live_id=0),
        BalatroCard("K", "Hearts", live_id=2),
    ]

    command = executor.command_for(
        BalatroAction(
            PLAY_CARDS,
            cards=cards,
        ),
        snapshot,
    )

    assert command.sequence == 12
    assert command.action == PLAY_CARDS
    assert command.payload == {
        "cards": [0, 2]
    }


def test_action_executor_maps_discard_action():
    executor = DefaultBalatroActionExecutor()
    snapshot = LiveBalatroSnapshot(
        sequence=3,
        phase="SELECTING_HAND",
        state_complete=True,
    )
    card = BalatroCard(
        "2",
        "Clubs",
        live_id=1,
    )

    command = executor.command_for(
        BalatroAction(
            DISCARD_CARDS,
            cards=[card],
        ),
        snapshot,
    )

    assert command.action == DISCARD_CARDS
    assert command.payload["cards"] == [1]


def test_action_executor_accepts_zero_index():
    executor = DefaultBalatroActionExecutor()
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
    )

    command = executor.command_for(
        BalatroAction(
            PLAY_CARDS,
            cards=[BalatroCard("A", "Spades", live_id=0)],
        ),
        snapshot,
    )

    assert command.payload["cards"] == [0]


def test_action_executor_requires_live_object_ids():
    executor = DefaultBalatroActionExecutor()
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
    )

    with pytest.raises(ValueError):
        executor.command_for(
            BalatroAction(
                PLAY_CARDS,
                cards=[BalatroCard("A", "Spades")],
            ),
            snapshot,
        )
