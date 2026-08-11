from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.live.external.hand_controller import ExternalHandController
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.state import BalatroState


class Observer:

    def __init__(self, snapshot):
        self.snapshot = snapshot

    def observe(self):
        return self.snapshot


class Translator:

    def __init__(self, states):
        self.states = states

    def translate(self, snapshot):
        return self.states[snapshot.sequence]


class ActionGenerator:

    def generate_actions(self, state):
        return [BalatroAction(PLAY_CARDS, cards=[state.hand[0]])]


class Agent:

    def act(self, state, actions):
        return actions[0]


class Executor:

    def __init__(self):
        self.calls = []

    def card_indices(self, state, action):
        return (0,)

    def dispatch(self, action, state):
        self.calls.append((action.name, state.score))
        return (0,)


class Synchronizer:

    def __init__(self, snapshots):
        self.snapshots = list(snapshots)
        self.calls = []

    def wait_for_change(self, snapshot, phases=None, *, require_complete=True):
        self.calls.append((snapshot.sequence, phases, require_complete))
        return self.snapshots.pop(0)


def _snapshot(sequence, phase):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=False,
        payload={},
    )


def _state(phase, *, score=0, hands=4, discards=4):
    state = BalatroState()
    state.phase = phase
    state.score = score
    state.hands_remaining = hands
    state.discards_remaining = discards
    if phase == "SELECTING_HAND":
        state.hand = [BalatroCard("A", "Spades", live_id=sequence_id(score, hands))]
    return state


def sequence_id(score, hands):
    return score * 10 + hands


def _controller(initial, following, states):
    executor = Executor()
    synchronizer = Synchronizer(following)
    controller = ExternalHandController(
        Observer(initial),
        executor,
        translator=Translator(states),
        action_generator=ActionGenerator(),
        agent=Agent(),
        synchronizer=synchronizer,
    )
    return controller, executor, synchronizer


def test_external_hand_controller_repeats_from_each_persisted_checkpoint():
    initial = _snapshot(1, "SELECTING_HAND")
    second = _snapshot(2, "SELECTING_HAND")
    final = _snapshot(3, "ROUND_EVAL")
    states = {
        1: _state("SELECTING_HAND", score=60, hands=3),
        2: _state("SELECTING_HAND", score=180, hands=2),
        3: _state("ROUND_EVAL", score=650, hands=1),
    }
    controller, executor, synchronizer = _controller(
        initial,
        [second, final],
        states,
    )

    result = controller.execute_until_phase_change(max_actions=8)

    assert len(result.steps) == 2
    assert executor.calls == [(PLAY_CARDS, 60), (PLAY_CARDS, 180)]
    assert synchronizer.calls == [
        (1, None, False),
        (2, None, False),
    ]
    assert result.final_state is states[3]
    assert result.stop_reason == "phase:ROUND_EVAL"


def test_external_hand_controller_stops_at_action_cap_without_projection():
    initial = _snapshot(1, "SELECTING_HAND")
    second = _snapshot(2, "SELECTING_HAND")
    states = {
        1: _state("SELECTING_HAND", score=60, hands=3),
        2: _state("SELECTING_HAND", score=120, hands=2),
    }
    controller, executor, synchronizer = _controller(initial, [second], states)

    result = controller.execute_until_phase_change(max_actions=1)

    assert len(result.steps) == 1
    assert executor.calls == [(PLAY_CARDS, 60)]
    assert synchronizer.calls == [(1, None, False)]
    assert result.final_state is states[2]
    assert result.stop_reason == "max_actions"


def test_external_hand_controller_does_nothing_outside_selecting_hand():
    initial = _snapshot(1, "ROUND_EVAL")
    states = {1: _state("ROUND_EVAL", score=650, hands=1)}
    controller, executor, synchronizer = _controller(initial, [], states)

    result = controller.execute_until_phase_change(max_actions=8)

    assert result.steps == ()
    assert executor.calls == []
    assert synchronizer.calls == []
    assert result.final_state is states[1]
    assert result.stop_reason == "phase:ROUND_EVAL"


def test_external_hand_controller_rejects_nonpositive_action_cap():
    initial = _snapshot(1, "SELECTING_HAND")
    states = {1: _state("SELECTING_HAND", score=60, hands=3)}
    controller, _, _ = _controller(initial, [], states)

    try:
        controller.execute_until_phase_change(max_actions=0)
    except ValueError as error:
        assert "at least 1" in str(error)
    else:
        raise AssertionError("nonpositive action cap should fail")
