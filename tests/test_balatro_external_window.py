import pytest

from games.balatro.live.external import (
    BalatroWindow,
    BalatroWindowLocator,
    BalatroWindowNotFound,
    BalatroWindowTracker,
    WindowRect,
)


class FakeWindowProvider:

    def __init__(self, windows):
        self.windows = {window.handle: window for window in windows}

    def list_windows(self):
        return list(self.windows.values())

    def get_window(self, handle):
        return self.windows.get(handle)


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
