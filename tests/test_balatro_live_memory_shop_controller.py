from types import SimpleNamespace

from games.balatro.actions import (
    BUY_BOOSTER,
    BUY_CONSUMABLE,
    END_SHOP,
    BalatroAction,
)
from games.balatro.live.external.live_memory_shop_controller import (
    LiveMemoryShopController,
    LiveMemoryShopView,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


class ActionGenerator:
    def __init__(self, actions):
        self.actions = list(actions)

    def generate_actions(self, state):
        assert state.phase == "SHOP"
        return list(self.actions)


class Policy:
    def rank_actions(self, state, actions):
        assert state.phase == "SHOP"
        # Controller must keep booster execution explicit rather than asking the
        # existing policy to score an action it does not support yet.
        assert all(action.name != BUY_BOOSTER for action in actions)
        return [SimpleNamespace(action=actions[0], total=1.0)]


class Dispatcher:
    def __init__(self):
        self.calls = []

    def dispatch(self, action, *, state, snapshot):
        self.calls.append((action, state, snapshot))
        return SimpleNamespace(action=action, before=snapshot, after=snapshot)

    def close(self):
        pass


def _view():
    return LiveMemoryShopView(
        LiveBalatroSnapshot(1, "SHOP", True, {"money": 10}),
        SimpleNamespace(phase="SHOP"),
    )


def test_recommended_action_uses_existing_policy_surface_without_boosters():
    consumable = BalatroAction(
        BUY_CONSUMABLE,
        target=SimpleNamespace(area_index=0),
    )
    booster = BalatroAction(
        BUY_BOOSTER,
        target=SimpleNamespace(area_index=1),
    )
    leave = BalatroAction(END_SHOP)
    controller = LiveMemoryShopController(
        observer=SimpleNamespace(),
        action_generator=ActionGenerator([consumable, booster, leave]),
        policy=Policy(),
        dispatcher=Dispatcher(),
    )

    assert controller.recommended_action(_view()) is consumable


def test_open_booster_routes_existing_generated_booster_to_live_dispatcher():
    booster = BalatroAction(
        BUY_BOOSTER,
        target=SimpleNamespace(area_index=2),
    )
    dispatcher = Dispatcher()
    controller = LiveMemoryShopController(
        observer=SimpleNamespace(),
        action_generator=ActionGenerator([booster, BalatroAction(END_SHOP)]),
        policy=Policy(),
        dispatcher=dispatcher,
    )
    view = _view()

    result = controller.open_booster(2, view)

    assert result.action is booster
    assert dispatcher.calls == [(booster, view.state, view.snapshot)]
