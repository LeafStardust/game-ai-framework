from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, USE_CONSUMABLE, BalatroAction
from games.balatro.live.external.live_memory_autonomous_step_injected import (
    LiveMemoryInjectedSingleStepRunner,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


class _Observer:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def observe(self):
        return self.snapshot


class _Translator:
    def __init__(self, state):
        self.state = state

    def translate(self, snapshot):
        return self.state


class _TimingPolicy:
    def __init__(self, recommendations):
        self.recommendations = tuple(recommendations)
        self.calls = 0

    def recommend_inventory(self, state):
        self.calls += 1
        return self.recommendations


class _Recommendation:
    def __init__(self, *, should_use, action=None, consumable=None, target_indices=(), rationale=()):
        self.should_use = should_use
        self._action = action
        self.consumable = consumable
        self.target = (
            SimpleNamespace(target_indices=tuple(target_indices))
            if target_indices is not None
            else None
        )
        self.rationale = tuple(rationale)

    def to_action(self):
        return self._action


def _snapshot():
    return LiveBalatroSnapshot(
        sequence=10,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={},
    )


def _runner(state, timing_policy, *, hand_recommender):
    snapshot = _snapshot()
    return LiveMemoryInjectedSingleStepRunner(
        _Observer(snapshot),
        translator=_Translator(state),
        bridge=SimpleNamespace(),
        dispatcher=SimpleNamespace(),
        hand_recommender=hand_recommender,
        consumable_timing_policy=timing_policy,
        pack_choice_reader=lambda: (),
    )


def test_autonomous_hand_arbiter_deferred_clear_consumable_falls_through_to_d1():
    card = SimpleNamespace(live_id=101)
    consumable = SimpleNamespace(name="Strength", live_id=501)
    state = SimpleNamespace(hand=[card], consumables=[consumable])
    d1_action = BalatroAction(USE_CONSUMABLE, cards=[card], target=consumable)
    timing = _TimingPolicy(
        [
            _Recommendation(
                should_use=False,
                consumable=consumable,
                target_indices=(0,),
                rationale=(
                    "HOLD: guaranteed blind-clear consumable arbitration is delegated to D1",
                ),
            )
        ]
    )
    d1_calls = []

    def d1(state_value, snapshot_value):
        d1_calls.append((state_value, snapshot_value))
        return d1_action, ("d1-consumable-clear",)

    decision = _runner(
        state,
        timing,
        hand_recommender=d1,
    ).decide()

    assert timing.calls == 1
    assert len(d1_calls) == 1
    assert decision.action is d1_action
    assert decision.source == "D1 hand-action policy"
    assert decision.notes == ("d1-consumable-clear",)


def test_autonomous_hand_arbiter_nonclear_b6_use_still_preempts_d1():
    card = SimpleNamespace(live_id=101)
    consumable = SimpleNamespace(name="The Hermit", live_id=501)
    state = SimpleNamespace(hand=[card], consumables=[consumable])
    action = BalatroAction(USE_CONSUMABLE, target=consumable)
    timing = _TimingPolicy(
        [
            _Recommendation(
                should_use=True,
                action=action,
                consumable=consumable,
                target_indices=(),
                rationale=("USE: deterministic economy timing",),
            )
        ]
    )

    def d1_should_not_run(state, snapshot):
        raise AssertionError("D1 must not run for an ordinary non-clear B6 use")

    decision = _runner(
        state,
        timing,
        hand_recommender=d1_should_not_run,
    ).decide()

    assert timing.calls == 1
    assert decision.action is action
    assert decision.source == "B6 consumable timing policy"
    assert decision.notes[:3] == (
        "hand_decision=USE_CONSUMABLE",
        "consumable=The Hermit",
        "target_indices=()",
    )


def test_autonomous_hand_arbiter_hold_falls_through_to_unchanged_d1():
    card = SimpleNamespace(live_id=101)
    consumable = SimpleNamespace(name="Strength", live_id=501)
    state = SimpleNamespace(hand=[card], consumables=[consumable])
    timing = _TimingPolicy(
        [
            _Recommendation(
                should_use=False,
                consumable=consumable,
                target_indices=(0,),
                rationale=("HOLD: preserve consumable",),
            )
        ]
    )
    d1_action = BalatroAction(PLAY_CARDS, cards=[card])
    d1_calls = []

    def d1(state_value, snapshot_value):
        d1_calls.append((state_value, snapshot_value))
        return d1_action, ("d1-note",)

    decision = _runner(state, timing, hand_recommender=d1).decide()

    assert timing.calls == 1
    assert len(d1_calls) == 1
    assert decision.action is d1_action
    assert decision.source == "D1 hand-action policy"
    assert decision.notes == ("d1-note",)


def test_autonomous_hand_arbiter_empty_inventory_falls_through_to_d1():
    card = SimpleNamespace(live_id=101)
    state = SimpleNamespace(hand=[card], consumables=[])
    timing = _TimingPolicy([])
    d1_action = BalatroAction(PLAY_CARDS, cards=[card])

    decision = _runner(
        state,
        timing,
        hand_recommender=lambda state, snapshot: (d1_action, ()),
    ).decide()

    assert timing.calls == 1
    assert decision.action is d1_action
    assert decision.source == "D1 hand-action policy"
