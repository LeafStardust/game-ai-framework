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


def test_action_executor_maps_selected_card_ids():
    executor = DefaultBalatroActionExecutor()
    snapshot = LiveBalatroSnapshot(
        sequence=12,
        phase="ROUND_START",
        state_complete=True,
    )
    cards = [
        BalatroCard("A", "Spades", live_id="card-a"),
        BalatroCard("K", "Hearts", live_id="card-k"),
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
        "cards": ["card-a", "card-k"]
    }


def test_action_executor_maps_discard_action():
    executor = DefaultBalatroActionExecutor()
    snapshot = LiveBalatroSnapshot(
        sequence=3,
        phase="ROUND_START",
        state_complete=True,
    )
    card = BalatroCard(
        "2",
        "Clubs",
        live_id="card-2",
    )

    command = executor.command_for(
        BalatroAction(
            DISCARD_CARDS,
            cards=[card],
        ),
        snapshot,
    )

    assert command.action == DISCARD_CARDS
    assert command.payload["cards"] == ["card-2"]


def test_action_executor_requires_live_object_ids():
    executor = DefaultBalatroActionExecutor()
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="ROUND_START",
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
