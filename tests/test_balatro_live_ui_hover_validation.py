from games.balatro.live.external.live_ui_hover_validation import _active_hover_truths


def test_active_hover_ignores_hover_capability_flag():
    state = {
        "states.hover.can": True,
        "states.hover.is": False,
    }

    assert _active_hover_truths(state) == ()


def test_active_hover_accepts_current_hover_state():
    state = {
        "states.hover.can": True,
        "states.hover.is": True,
    }

    assert _active_hover_truths(state) == ("states.hover.is",)
