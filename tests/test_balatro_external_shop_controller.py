from types import SimpleNamespace

import pytest

from games.balatro.actions import BUY_JOKER, END_SHOP
from games.balatro.live.external.shop_controller import ExternalShopController
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.state import BalatroState


def _shop_state(*, money=10):
    state = BalatroState()
    state.phase = "SHOP"
    state.money = money
    state.joker_slots = 5
    state.shop_jokers = [
        SimpleNamespace(
            area_index=0,
            live_id=100,
            label="8 Ball",
            cost=5,
        )
    ]
    return state


def _checkpoint_state(*, money=5):
    state = BalatroState()
    state.phase = "BLIND_SELECT"
    state.money = money
    return state


def _snapshot(sequence, phase, state):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=False,
        payload={"translated_state": state},
    )


class Translator:

    def translate(self, snapshot):
        return snapshot.payload["translated_state"]


class Observer:

    def __init__(self, snapshot):
        self.snapshot = snapshot

    def observe(self):
        return self.snapshot

    def is_connected(self):
        return True


class Executor:

    def __init__(self):
        self.actions = []

    def dispatch(self, action, state, transaction=None):
        self.actions.append(action)
        if action.name != END_SHOP:
            transaction.apply(state, action)


class Synchronizer:

    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.calls = []

    def wait_for_change(self, snapshot, phases=None, *, require_complete=True):
        self.calls.append((snapshot, phases, require_complete))
        return self.snapshot


def _controller(*, persisted_money=5):
    initial_state = _shop_state()
    initial = _snapshot(1, "SHOP", initial_state)
    persisted = _snapshot(
        2,
        "BLIND_SELECT",
        _checkpoint_state(money=persisted_money),
    )
    executor = Executor()
    synchronizer = Synchronizer(persisted)
    controller = ExternalShopController(
        Observer(initial),
        executor,
        translator=Translator(),
        synchronizer=synchronizer,
    )
    return controller, executor, synchronizer


def test_external_shop_controller_projects_purchase_then_reconciles_checkpoint():
    controller, executor, synchronizer = _controller()
    session = controller.open()

    actions = controller.available_actions(session)
    assert [action.name for action in actions] == [BUY_JOKER, END_SHOP]

    controller.execute_purchase(session, actions[0])

    assert session.state.money == 5
    assert session.state.shop_jokers == []
    assert len(session.state.jokers) == 1
    assert session.transaction.expected_money == 5

    snapshot, state = controller.leave_shop(session)

    assert snapshot.phase == "BLIND_SELECT"
    assert state.money == 5
    assert session.closed is True
    assert [action.name for action in executor.actions] == [BUY_JOKER, END_SHOP]
    assert synchronizer.calls == [
        (session.snapshot, {"BLIND_SELECT"}, False)
    ]


def test_external_shop_controller_rejects_checkpoint_money_mismatch():
    controller, _, _ = _controller(persisted_money=10)
    session = controller.open()
    purchase = controller.available_actions(session)[0]
    controller.execute_purchase(session, purchase)

    with pytest.raises(RuntimeError, match="did not reconcile"):
        controller.leave_shop(session)

    assert session.closed is False


def test_external_shop_controller_rejects_non_shop_open():
    state = _checkpoint_state()
    controller = ExternalShopController(
        Observer(_snapshot(1, "BLIND_SELECT", state)),
        Executor(),
        translator=Translator(),
        synchronizer=Synchronizer(_snapshot(2, "BLIND_SELECT", state)),
    )

    with pytest.raises(ValueError, match="requires SHOP phase"):
        controller.open()


def test_external_shop_controller_rejects_reuse_after_close():
    controller, _, _ = _controller()
    session = controller.open()
    controller.leave_shop(session)

    with pytest.raises(RuntimeError, match="already closed"):
        controller.available_actions(session)
