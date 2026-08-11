from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.live.external.capture import BalatroFrame
from games.balatro.live.external.hand_mouse import (
    ExternalHandMouseExecutor,
    HandMouseLayout,
    HandMouseLayoutError,
)
from games.balatro.live.external.mouse import BalatroMouseController
from games.balatro.live.external.viewport import NormalizedPoint, NormalizedRect, PixelRect
from games.balatro.live.external.window import BalatroWindow, WindowRect
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


class Tracker:

    def __init__(self, window):
        self.window = window

    def snapshot(self):
        return self.window


class Capture:

    def __init__(self, frame, provider):
        self.frame = frame
        self.provider = provider
        self.tracker = Tracker(frame.window)

    def capture(self):
        assert self.provider.events[0] == ("focus", 42)
        return self.frame

    def close(self):
        pass


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


def _location(x):
    rect = NormalizedRect(x - 0.02, 0.68, 0.04, 0.08)
    return SimpleNamespace(
        center=NormalizedPoint(x, 0.72),
        normalized_rect=rect,
        local_rect=PixelRect(0, 0, 10, 20),
        density=1.0,
    )


def test_hand_mouse_layout_round_trips(tmp_path):
    path = tmp_path / "hand.json"
    layout = HandMouseLayout(
        play_hand=NormalizedPoint(0.4, 0.9),
        discard=NormalizedPoint(0.6, 0.9),
    )

    layout.save(path)
    loaded = HandMouseLayout.load(path)

    assert loaded == layout
    assert loaded.point_for("play-hand") == NormalizedPoint(0.4, 0.9)
    assert loaded.point_for("discard") == NormalizedPoint(0.6, 0.9)


def test_card_indices_use_current_hand_identity_with_duplicate_cards():
    first = BalatroCard("10", "Spades", live_id=11)
    duplicate = BalatroCard("10", "Spades", live_id=12)
    queen = BalatroCard("Q", "Hearts", live_id=13)
    state = BalatroState()
    state.hand = [first, duplicate, queen]

    action = BalatroAction(PLAY_CARDS, cards=[duplicate, queen])

    assert ExternalHandMouseExecutor.card_indices(state, action) == (1, 2)


def test_hand_executor_clicks_selected_cards_then_play_button():
    provider = Provider()
    state = BalatroState()
    state.hand = [
        BalatroCard("A", "Spades", live_id=1),
        BalatroCard("K", "Spades", live_id=2),
        BalatroCard("Q", "Spades", live_id=3),
    ]
    action = BalatroAction(PLAY_CARDS, cards=[state.hand[0], state.hand[2]])
    locations = [_location(0.25), _location(0.5), _location(0.75)]

    executor = ExternalHandMouseExecutor(
        HandMouseLayout(
            play_hand=NormalizedPoint(0.4, 0.9),
            discard=NormalizedPoint(0.6, 0.9),
        ),
        capture=Capture(_frame(), provider),
        mouse=BalatroMouseController(provider=provider, armed=True, hover_delay=0),
        card_locator=lambda region: locations,
        focus_settle_delay=0,
        between_card_delay=0,
        before_action_delay=0,
    )

    indices = executor.dispatch(action, state)

    assert indices == (0, 2)
    assert provider.events == [
        ("focus", 42),
        ("move", 200, 343),
        ("down",),
        ("up",),
        ("move", 399, 343),
        ("down",),
        ("up",),
        ("move", 260, 379),
        ("down",),
        ("up",),
    ]


def test_hand_executor_uses_discard_button_for_discard_action():
    provider = Provider()
    state = BalatroState()
    state.hand = [BalatroCard("2", "Clubs", live_id=1)]
    action = BalatroAction(DISCARD_CARDS, cards=[state.hand[0]])

    executor = ExternalHandMouseExecutor(
        HandMouseLayout(
            play_hand=NormalizedPoint(0.4, 0.9),
            discard=NormalizedPoint(0.6, 0.9),
        ),
        capture=Capture(_frame(), provider),
        mouse=BalatroMouseController(provider=provider, armed=True, hover_delay=0),
        card_locator=lambda region: [_location(0.5)],
        focus_settle_delay=0,
        between_card_delay=0,
        before_action_delay=0,
    )

    executor.dispatch(action, state)

    assert provider.events[-3:] == [
        ("move", 339, 379),
        ("down",),
        ("up",),
    ]


def test_hand_executor_rejects_unsupported_action():
    provider = Provider()
    executor = ExternalHandMouseExecutor(
        HandMouseLayout(
            play_hand=NormalizedPoint(0.4, 0.9),
            discard=NormalizedPoint(0.6, 0.9),
        ),
        capture=Capture(_frame(), provider),
        mouse=BalatroMouseController(provider=provider, armed=True, hover_delay=0),
    )
    state = BalatroState()

    try:
        executor.dispatch(BalatroAction("END_SHOP"), state)
    except HandMouseLayoutError as error:
        assert "cannot dispatch" in str(error)
    else:
        raise AssertionError("unsupported hand action should fail")
