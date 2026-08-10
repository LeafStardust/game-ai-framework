from pathlib import Path
from types import SimpleNamespace

import pytest

from games.balatro.actions import (
    BalatroAction,
    BUY_BOOSTER,
    BUY_JOKER,
    END_SHOP,
    REFRESH_SHOP,
)
from games.balatro.live.external.capture import BalatroFrame
from games.balatro.live.external.mouse import BalatroMouseController
from games.balatro.live.external.save_observer import snapshot_from_save
from games.balatro.live.external.save_state import BalatroSaveSnapshot
from games.balatro.live.external.shop_mouse import (
    ExternalShopMouseExecutor,
    ShopClickSequence,
    ShopMouseLayout,
    ShopMouseLayoutError,
    ShopPointerStep,
)
from games.balatro.live.external.viewport import NormalizedPoint
from games.balatro.live.external.window import BalatroWindow, WindowRect
from games.balatro.live.shop_sync import (
    BufferedShopTransaction,
    UnsupportedBufferedShopAction,
)
from games.balatro.live.translator import DefaultBalatroStateTranslator
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


class Capture:

    def __init__(self, frame):
        self.frame = frame
        self.closed = False

    def capture(self):
        return self.frame

    def close(self):
        self.closed = True


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


def _sequence(*steps):
    return ShopClickSequence(tuple(steps))


def _click(x, y, delay=0.0):
    return ShopPointerStep("click", NormalizedPoint(x, y), delay)


def _move(x, y, delay=0.0):
    return ShopPointerStep("move", NormalizedPoint(x, y), delay)


def test_shop_mouse_layout_round_trips_json_shape(tmp_path):
    layout = ShopMouseLayout(
        main={
            1: _sequence(
                _move(0.5, 0.25, 0.1),
                _click(0.5, 0.5),
            )
        },
        vouchers={0: _sequence(_click(0.8, 0.4))},
        end_shop=_sequence(_click(0.9, 0.9)),
    )

    path = layout.save(tmp_path / "shop-mouse.json")
    loaded = ShopMouseLayout.load(path)

    assert loaded == layout


def test_shop_mouse_layout_routes_main_row_by_preserved_area_index():
    layout = ShopMouseLayout(
        main={1: _sequence(_click(0.5, 0.5))},
    )
    target = SimpleNamespace(area_index=1)

    assert layout.sequence_for(
        BalatroAction(BUY_JOKER, target=target)
    ) == layout.main[1]

    with pytest.raises(ShopMouseLayoutError):
        layout.sequence_for(
            BalatroAction(
                BUY_JOKER,
                target=SimpleNamespace(area_index=0),
            )
        )


def test_external_shop_mouse_executor_dispatches_and_projects_direct_purchase():
    provider = Provider()
    capture = Capture(_frame())
    mouse = BalatroMouseController(provider=provider, armed=True)
    layout = ShopMouseLayout(
        main={
            1: _sequence(
                _move(0.5, 0.25),
                _click(0.5, 0.5),
            )
        }
    )
    executor = ExternalShopMouseExecutor(
        layout,
        capture=capture,
        mouse=mouse,
    )

    joker = SimpleNamespace(
        area_index=1,
        live_id=640,
        label="Acrobat",
        cost=6,
    )
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 10
    state.shop_jokers = [joker]
    transaction = BufferedShopTransaction.begin(state)

    executor.dispatch(
        BalatroAction(BUY_JOKER, target=joker),
        state,
        transaction,
    )

    assert provider.events == [
        ("focus", 42),
        ("move", 300, 250),
        ("move", 300, 300),
        ("down",),
        ("up",),
    ]
    assert state.money == 4
    assert state.jokers == [joker]
    assert state.shop_jokers == []
    assert transaction.expected_money == 4


def test_external_shop_mouse_executor_preflights_before_mouse_input():
    provider = Provider()
    joker = SimpleNamespace(
        area_index=0,
        live_id=640,
        label="Acrobat",
        cost=20,
    )
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 10
    state.shop_jokers = [joker]
    transaction = BufferedShopTransaction.begin(state)
    executor = ExternalShopMouseExecutor(
        ShopMouseLayout(
            main={0: _sequence(_click(0.5, 0.5))},
        ),
        capture=Capture(_frame()),
        mouse=BalatroMouseController(provider=provider, armed=True),
    )

    with pytest.raises(ValueError, match="insufficient money"):
        executor.dispatch(
            BalatroAction(BUY_JOKER, target=joker),
            state,
            transaction,
        )

    assert provider.events == []
    assert state.money == 10


def test_external_shop_mouse_executor_dispatches_end_shop_without_projection():
    provider = Provider()
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 10
    executor = ExternalShopMouseExecutor(
        ShopMouseLayout(
            end_shop=_sequence(_click(0.9, 0.9)),
        ),
        capture=Capture(_frame()),
        mouse=BalatroMouseController(provider=provider, armed=True),
    )

    executor.dispatch(BalatroAction(END_SHOP), state)

    assert state.money == 10
    assert provider.events[-3:] == [
        ("move", 459, 379),
        ("down",),
        ("up",),
    ]


def test_external_shop_mouse_executor_rejects_random_state_actions():
    state = BalatroState()
    state.phase = "SHOP"
    executor = ExternalShopMouseExecutor(
        ShopMouseLayout(),
        capture=Capture(_frame()),
        mouse=BalatroMouseController(provider=Provider(), armed=True),
    )

    for action in (
        BalatroAction(BUY_BOOSTER, target=SimpleNamespace(area_index=0)),
        BalatroAction(REFRESH_SHOP),
    ):
        with pytest.raises(UnsupportedBufferedShopAction):
            executor.dispatch(action, state)


def test_save_shop_offers_preserve_visible_area_index_after_translation():
    save = BalatroSaveSnapshot(
        path=Path("save.jkr"),
        modified_ns=1,
        size=1,
        sha256="abc",
        data={
            "STATE": 5,
            "GAME": {
                "dollars": 10,
                "round_resets": {"ante": 1},
                "current_round": {},
            },
            "cardAreas": {
                "shop_jokers": {
                    "cards": {
                        1: {
                            "sort_id": 100,
                            "label": "8 Ball",
                            "save_fields": {"center": "j_8_ball"},
                            "ability": {"name": "8 Ball", "set": "Joker"},
                        },
                        2: {
                            "sort_id": 101,
                            "label": "Mercury",
                            "save_fields": {"center": "c_mercury"},
                            "ability": {"name": "Mercury", "set": "Planet"},
                        },
                    },
                    "config": {"card_count": 2, "card_limit": 2},
                }
            },
        },
    )

    snapshot = snapshot_from_save(save)

    assert [
        card["area_index"]
        for card in snapshot.payload["shop_jokers"]["cards"]
    ] == [0, 1]
    assert "area_index" not in snapshot.payload["jokers"]["cards"]

    state = DefaultBalatroStateTranslator().translate(snapshot)
    assert state.shop_jokers[0].label == "8 Ball"
    assert state.shop_jokers[0].area_index == 0
    assert state.shop_consumables[0].name == "Mercury"
    assert state.shop_consumables[0].area_index == 1
