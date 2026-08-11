from types import SimpleNamespace

import pytest

from games.balatro.actions import BUY_CONSUMABLE, BUY_JOKER, END_SHOP
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


def _two_item_shop_state(*, money=10):
    state = _shop_state(money=money)
    state.shop_consumables = [
        SimpleNamespace(
            area_index=1,
            live_id=101,
            label="The Sun",
            cost=3,
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


class ReflowLocator:

    def __init__(self):
        self.actions = []

    def dispatch(self, action, state, transaction, *, only_step=None):
        self.actions.append(action)
        transaction.apply(state, action)


class Synchronizer:

    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.calls = []

    def wait_for_change(self, snapshot, phases=None, *, require_complete=True):
        self.calls.append((snapshot, phases, require_complete))
        return self.snapshot


class PreferPurchasePolicy:

    def __init__(self):
        self.calls = []

    def rank_actions(self, state, actions):
        self.calls.append((state.money, tuple(action.name for action in actions)))
        ordered = sorted(
            actions,
            key=lambda action: action.name != END_SHOP,
            reverse=True,
        )
        return [SimpleNamespace(action=action) for action in ordered]


class PreferLeavePolicy:

    def rank_actions(self, state, actions):
        ordered = sorted(
            actions,
            key=lambda action: action.name == END_SHOP,
            reverse=True,
        )
        return [SimpleNamespace(action=action) for action in ordered]


def _controller(*, persisted_money=5, policy=None):
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
        policy=policy,
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
    controller, _, _ = _controller(persisted_money=10)
    session = controller.open()
    controller.leave_shop(session)

    with pytest.raises(RuntimeError, match="already closed"):
        controller.available_actions(session)


def test_external_shop_controller_recommends_from_current_projected_state():
    policy = PreferPurchasePolicy()
    controller, _, _ = _controller(policy=policy)
    session = controller.open()

    recommended = controller.recommended_action(session)
    assert recommended.name == BUY_JOKER

    controller.execute_purchase(session, recommended)

    recommended_after_purchase = controller.recommended_action(session)
    assert recommended_after_purchase.name == END_SHOP
    assert policy.calls == [
        (10, (BUY_JOKER, END_SHOP)),
        (5, (END_SHOP,)),
    ]


def test_external_shop_controller_executes_exactly_one_recommended_purchase():
    policy = PreferPurchasePolicy()
    controller, executor, _ = _controller(policy=policy)
    session = controller.open()

    executed = controller.execute_recommended_purchase(session)

    assert executed.name == BUY_JOKER
    assert [action.name for action in executor.actions] == [BUY_JOKER]
    assert session.state.money == 5
    assert len(session.state.jokers) == 1
    assert controller.recommended_action(session).name == END_SHOP


def test_external_shop_controller_uses_fresh_geometry_for_second_main_purchase():
    initial_state = _two_item_shop_state()
    initial = _snapshot(1, "SHOP", initial_state)
    executor = Executor()
    reflow = ReflowLocator()
    controller = ExternalShopController(
        Observer(initial),
        executor,
        translator=Translator(),
        synchronizer=Synchronizer(
            _snapshot(2, "BLIND_SELECT", _checkpoint_state(money=2))
        ),
        reflow_locator=reflow,
    )
    session = controller.open()

    actions = controller.available_actions(session)
    joker = next(action for action in actions if action.name == BUY_JOKER)
    controller.execute_purchase(session, joker)

    actions = controller.available_actions(session)
    consumable = next(action for action in actions if action.name == BUY_CONSUMABLE)
    controller.execute_purchase(session, consumable)

    assert [action.name for action in executor.actions] == [BUY_JOKER]
    assert [action.name for action in reflow.actions] == [BUY_CONSUMABLE]
    assert session.state.money == 2
    assert session.state.shop_jokers == []
    assert session.state.shop_consumables == []
    assert len(session.transaction.purchases) == 2


def test_external_shop_controller_does_not_execute_when_policy_recommends_leave():
    controller, executor, _ = _controller(policy=PreferLeavePolicy())
    session = controller.open()

    with pytest.raises(RuntimeError, match="recommends END_SHOP"):
        controller.execute_recommended_purchase(session)

    assert executor.actions == []
    assert session.state.money == 10
