import pytest

from games.balatro.live.external import (
    BalatroWindow,
    BalatroWindowLocator,
    BalatroWindowNotForeground,
    BalatroWindowNotFound,
    BalatroWindowTracker,
    WindowRect,
)


class FakeWindowProvider:

    def __init__(self, windows, foreground_handle=None):
        self.windows = {window.handle: window for window in windows}
        self.foreground_handle = foreground_handle

    def list_windows(self):
        return list(self.windows.values())

    def get_window(self, handle):
        return self.windows.get(handle)

    def get_foreground_handle(self):
        return self.foreground_handle


def window(handle, title, left=0, top=0, width=1280, height=720):
    return BalatroWindow(
        handle=handle,
        title=title,
        client_rect=WindowRect(left, top, width, height),
    )


def test_locator_prefers_exact_balatro_title():
    provider = FakeWindowProvider(
        [
            window(1, "Balatro helper", width=1920, height=1080),
            window(2, "Balatro", width=1280, height=720),
            window(3, "Discord"),
        ]
    )
    locator = BalatroWindowLocator(provider=provider)

    found = locator.find()

    assert found.handle == 2
    assert found.title == "Balatro"


def test_locator_refreshes_client_area():
    provider = FakeWindowProvider([window(1, "Balatro")])
    locator = BalatroWindowLocator(provider=provider)

    provider.windows[1] = window(
        1,
        "Balatro",
        left=100,
        top=50,
        width=1600,
        height=900,
    )
    refreshed = locator.refresh(1)

    assert refreshed.client_rect == WindowRect(100, 50, 1600, 900)


def test_locator_raises_when_balatro_is_not_visible():
    locator = BalatroWindowLocator(
        provider=FakeWindowProvider([window(1, "Notepad")])
    )

    with pytest.raises(BalatroWindowNotFound):
        locator.find()


def test_tracker_reacquires_balatro_when_handle_changes():
    provider = FakeWindowProvider([window(1, "Balatro")])
    tracker = BalatroWindowTracker(
        BalatroWindowLocator(provider=provider)
    )

    assert tracker.locate().handle == 1

    del provider.windows[1]
    provider.windows[7] = window(7, "Balatro", left=25, top=30)

    current = tracker.snapshot()

    assert current.handle == 7
    assert current.client_rect.left == 25
    assert current.client_rect.top == 30


def test_tracker_accepts_balatro_as_foreground():
    provider = FakeWindowProvider(
        [window(1, "Balatro")],
        foreground_handle=1,
    )
    tracker = BalatroWindowTracker(
        BalatroWindowLocator(provider=provider)
    )

    current = tracker.require_foreground()

    assert current.handle == 1


def test_tracker_rejects_balatro_when_another_window_is_foreground():
    provider = FakeWindowProvider(
        [window(1, "Balatro"), window(2, "PowerShell")],
        foreground_handle=2,
    )
    tracker = BalatroWindowTracker(
        BalatroWindowLocator(provider=provider)
    )

    with pytest.raises(BalatroWindowNotForeground):
        tracker.require_foreground()
