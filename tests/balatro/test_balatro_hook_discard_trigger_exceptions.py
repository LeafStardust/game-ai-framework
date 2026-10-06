from __future__ import annotations

from games.balatro.card import BalatroCard
from games.balatro.env.parity import canonical_public_state_signature
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.jokers.blueprint import BlueprintJoker
from games.balatro.jokers.burnt_joker import BurntJoker
from games.balatro.jokers.faceless_joker import FacelessJoker
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


def test_empty_active_path_skips_hand_evaluation_but_keeps_discard_effects() -> None:
    class ExplodingHandEvaluator:
        @staticmethod
        def evaluate(cards, *, rules):
            raise AssertionError("empty-active discard must not evaluate a hand")

    for consume_discard_use, expected_uses in ((True, 1), (False, 0)):
        state = _state()
        state.consumable_slots = 1
        card = BalatroCard("2", "Clubs", seal="Purple", live_id="two")

        projected = LiveDiscardJokerProjector(
            hand_evaluator=ExplodingHandEvaluator()
        ).project(
            state,
            [card],
            consume_discard_use=consume_discard_use,
        )

        assert projected.discards_used == expected_uses
        assert projected.discard_pile == [card]
        assert len(projected.consumables) == 1
        assert projected.consumables[0].category == "TAROT"
        assert state.discards_used == 0
        assert state.discard_pile == []
        assert state.consumables == []


def test_active_and_copy_discard_jokers_keep_full_context_pipeline() -> None:
    class CountingHandEvaluator:
        def __init__(self):
            self.calls = 0
            self.delegate = HandEvaluator()

        def evaluate(self, cards, *, rules):
            self.calls += 1
            return self.delegate.evaluate(cards, rules=rules)

    cards = [
        BalatroCard("J", "Spades", live_id="jack"),
        BalatroCard("Q", "Hearts", live_id="queen"),
        BalatroCard("K", "Clubs", live_id="king"),
    ]
    state = _state()
    state.jokers = [BlueprintJoker(), FacelessJoker()]
    evaluator = CountingHandEvaluator()

    projected = LiveDiscardJokerProjector(hand_evaluator=evaluator).project(
        state,
        cards,
    )

    assert evaluator.calls == 1
    assert projected.money == 10
    assert state.money == 0


def test_empty_active_fast_path_matches_full_context_projection_exactly() -> None:
    class FullContextProjector(LiveDiscardJokerProjector):
        def project(self, state, cards, *, consume_discard_use=True):
            branch_state = self._copy_state_shell(state)
            self._clone_joker_graph(branch_state, state)
            discarded = list(cards or [])
            active = self._active_jokers(
                branch_state,
                consume_discard_use=consume_discard_use,
            )
            context, discards_used = self._prepare_discard_context(
                branch_state,
                discarded,
                active,
                consume_discard_use=consume_discard_use,
            )
            context = self._apply_active_jokers(active, context)
            self._finalize_discard_side_effects(
                branch_state,
                discarded,
                context,
                consume_discard_use=consume_discard_use,
                discards_used=discards_used,
            )
            return branch_state

    state = _state()
    state.jokers = [BurntJoker()]
    state.consumable_slots = 1
    card = BalatroCard("2", "Clubs", seal="Purple", live_id="two")

    inherited = FullContextProjector().project(
        state,
        [card],
        consume_discard_use=False,
    )
    optimized = LiveDiscardJokerProjector().project(
        state,
        [card],
        consume_discard_use=False,
    )

    assert canonical_public_state_signature(optimized) == (
        canonical_public_state_signature(inherited)
    )
    assert optimized.jokers[0] is not state.jokers[0]
    assert inherited.jokers[0] is not state.jokers[0]
