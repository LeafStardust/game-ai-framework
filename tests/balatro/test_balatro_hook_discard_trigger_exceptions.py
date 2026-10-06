from __future__ import annotations

from games.balatro.card import BalatroCard
from games.balatro.jokers.blueprint import BlueprintJoker
from games.balatro.jokers.burnt_joker import BurntJoker
from games.balatro.jokers.green_joker import GreenJoker
from games.balatro.live.discard_projection import LiveDiscardJokerProjector
from games.balatro.state import BalatroState


def _state() -> BalatroState:
    state = BalatroState()
    state.discards_used = 0
    state.discard_pile = []
    return state


def test_player_discard_still_activates_burnt_joker_once() -> None:
    state = _state()
    state.jokers = [BurntJoker()]
    card = BalatroCard("A", "Spades", live_id="ace")

    projected = LiveDiscardJokerProjector().project(
        state,
        [card],
        consume_discard_use=True,
    )

    assert projected.discards_used == 1
    assert projected.hand_levels["HIGH_CARD"] == 2

    second = LiveDiscardJokerProjector().project(
        projected,
        [BalatroCard("K", "Hearts", live_id="king")],
        consume_discard_use=True,
    )
    assert second.hand_levels["HIGH_CARD"] == 2


def test_hook_forced_discard_does_not_activate_burnt_joker() -> None:
    state = _state()
    state.jokers = [BurntJoker()]

    projected = LiveDiscardJokerProjector().project(
        state,
        [BalatroCard("A", "Spades", live_id="ace")],
        consume_discard_use=False,
    )

    assert projected.discards_used == 0
    assert projected.hand_levels["HIGH_CARD"] == 1


def test_hook_forced_discard_does_not_activate_blueprint_copying_burnt() -> None:
    state = _state()
    state.jokers = [BlueprintJoker(), BurntJoker()]

    projected = LiveDiscardJokerProjector().project(
        state,
        [BalatroCard("A", "Spades", live_id="ace")],
        consume_discard_use=False,
    )

    assert projected.hand_levels["HIGH_CARD"] == 1


def test_hook_forced_discard_still_penalizes_green_joker_without_using_discard() -> None:
    state = _state()
    green = GreenJoker()
    green.mult = 4
    state.jokers = [green]

    projected = LiveDiscardJokerProjector().project(
        state,
        [BalatroCard("2", "Clubs", live_id="two")],
        consume_discard_use=False,
    )

    assert projected.discards_used == 0
    assert projected.jokers[0].mult == 3
    assert state.jokers[0].mult == 4


def test_discard_projection_helper_pipeline_preserves_order_and_isolation() -> None:
    class RecordingProjector(LiveDiscardJokerProjector):
        def __init__(self):
            super().__init__()
            self.calls = []

        def _copy_state_shell(self, state):
            self.calls.append("copy_state_shell")
            return super()._copy_state_shell(state)

        def _clone_joker_graph(self, branch_state, source_state):
            self.calls.append("clone_joker_graph")
            return super()._clone_joker_graph(branch_state, source_state)

        def _active_jokers(self, state, *, consume_discard_use=True):
            self.calls.append("active_jokers")
            return super()._active_jokers(
                state,
                consume_discard_use=consume_discard_use,
            )

        def _prepare_discard_context(
            self,
            branch_state,
            discarded,
            active,
            *,
            consume_discard_use,
        ):
            self.calls.append("prepare_context")
            return super()._prepare_discard_context(
                branch_state,
                discarded,
                active,
                consume_discard_use=consume_discard_use,
            )

        def _apply_active_jokers(self, active, context):
            self.calls.append("apply_jokers")
            return super()._apply_active_jokers(active, context)

        def _finalize_discard_side_effects(self, *args, **kwargs):
            self.calls.append("finalize_side_effects")
            return super()._finalize_discard_side_effects(*args, **kwargs)

    state = _state()
    green = GreenJoker()
    green.mult = 4
    state.jokers = [green]
    card = BalatroCard("2", "Clubs", live_id="two")
    projector = RecordingProjector()

    projected = projector.project(
        state,
        [card],
        consume_discard_use=False,
    )

    assert projector.calls == [
        "copy_state_shell",
        "clone_joker_graph",
        "active_jokers",
        "prepare_context",
        "apply_jokers",
        "finalize_side_effects",
    ]
    assert projected is not state
    assert projected.jokers[0] is not state.jokers[0]
    assert projected.jokers[0].mult == 3
    assert state.jokers[0].mult == 4
    assert projected.discard_pile == [card]
    assert projected.discards_used == 0
