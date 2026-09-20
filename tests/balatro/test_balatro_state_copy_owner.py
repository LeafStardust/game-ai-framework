from games.balatro.state import BalatroState


def test_balatro_state_copy_does_not_construct_a_discarded_pristine_deck(monkeypatch):
    state = BalatroState()

    def fail_if_called(_self):
        raise AssertionError("copy must not construct a replacement pristine deck")

    monkeypatch.setattr(BalatroState, "_create_deck", fail_if_called)

    copied = state.copy()

    assert copied is not state
    assert copied.blind is None
    assert copied.deck == state.deck
    assert copied.deck is not state.deck
