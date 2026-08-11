from types import SimpleNamespace

import pytest

from games.balatro.actions import BUY_JOKER, END_SHOP
from games.balatro.live.external.capture import BalatroFrame
from games.balatro.live.external.mouse import BalatroMouseController
from games.balatro.live.external.shop_mouse import (
    ExternalShopMouseExecutor,
    ShopClickSequence,
    ShopMouseLayout,
    ShopPointerStep,
)
from games.balatro.live.external.shop_mouse_live_validation import select_action
from games.balatro.live.external.viewport import NormalizedPoint
from games.balatro.live.external.window import BalatroWindow, WindowRect
from games.balatro.live.shop_sync import BufferedShopTransaction
from games.balatro.state import BalatroState


class Provider:

    def __init__(self):
        self.events = []

    def focus(self, handle):
        self.events.append(("focus", handle))

    def move_to(self, x, y):
        self.events.append(("move", x, y))

    def left_down(self):
        self.events.append(("down",))

    def left_up(self):
        self.events.append(("up",))


def _state():
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 10
    state.shop_jokers = [
        SimpleNamespace(area_index=0, label="8 Ball", cost=5),
    ]
    state.shop_consumables = [
        SimpleNamespace(area_index=1, name="Mercury", price=3),
    ]
    state.shop_vouchers = [
        SimpleNamespace(area_index=0, label="Hieroglyph", price=10),
    ]
    return state


def _frame():
    return BalatroFrame(
        sequence=1,
        timestamp=0.0,
        window=BalatroWindow(
            handle=42,
            title="Balatro",
            client_rect=WindowRect(100, 200, 400, 200),
        ),
        width=400,
        height=200,
        bgra=bytes(400 * 200 * 4),
    )


def test_one_shot_selector_targets_exact_visible_slot():
    state = _state()

    action = select_action(state, "buy-joker", 0)

    assert action.name == BUY_JOKER
    assert action.target is state.shop_jokers[0]


def test_one_shot_selector_rejects_wrong_or_missing_slot():
    state = _state()

    with pytest.raises(ValueError, match="visible slot 1"):
        select_action(state, "buy-joker", 1)

    with pytest.raises(ValueError, match="requires --slot"):
        select_action(state, "buy-joker", None)


def test_one_shot_selector_allows_end_shop_without_slot():
    action = select_action(_state(), "end-shop", None)

    assert action.name == END_SHOP
    assert action.target is None


class Tracker:

    def __init__(self, window):
        self.window = window

    def snapshot(self):
        return self.window


class ForegroundCapture:

    def __init__(self, frame, provider):
        self.frame = frame
        self.provider = provider
        self.tracker = Tracker(frame.window)

    def capture(self):
        assert self.provider.events[0] == ("focus", 42)
        return self.frame

    def close(self):
        pass


def test_real_capture_path_focuses_balatro_before_foreground_capture():
    provider = Provider()
    frame = _frame()
    executor = ExternalShopMouseExecutor(
        ShopMouseLayout(
            end_shop=ShopClickSequence(
                (ShopPointerStep("click", NormalizedPoint(0.5, 0.5)),)
            )
        ),
        capture=ForegroundCapture(frame, provider),
        mouse=BalatroMouseController(provider=provider, armed=True),
        focus_settle_delay=0,
    )

    executor.dispatch(
        select_action(_state(), "end-shop", None),
        _state(),
    )

    assert provider.events[0] == ("focus", 42)


def test_single_step_diagnostic_click_does_not_project_purchase():
    provider = Provider()
    frame = _frame()
    state = _state()
    action = select_action(state, "buy-joker", 0)
    transaction = BufferedShopTransaction.begin(state)
    executor = ExternalShopMouseExecutor(
        ShopMouseLayout(
            main={
                0: ShopClickSequence(
                    (
                        ShopPointerStep("click", NormalizedPoint(0.4, 0.4)),
                        ShopPointerStep("click", NormalizedPoint(0.4, 0.5)),
                    )
                )
            }
        ),
        capture=ForegroundCapture(frame, provider),
        mouse=BalatroMouseController(provider=provider, armed=True),
        focus_settle_delay=0,
        between_click_delay=0,
    )

    executor.dispatch(
        action,
        state,
        transaction,
        only_step=1,
    )

    assert state.money == 10
    assert state.jokers == []
    assert state.shop_jokers == [action.target]
    assert transaction.purchases == []
    assert provider.events[-3:] == [
        ("move", 260, 280),
        ("down",),
        ("up",),
    ]
