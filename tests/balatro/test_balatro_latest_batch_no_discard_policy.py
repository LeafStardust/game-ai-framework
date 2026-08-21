from types import SimpleNamespace

from games.balatro.latest_batch_no_discard_policy import (
    realized_banner_delayed_no_discard,
)


def _joker(name):
    return SimpleNamespace(name=name, label=name)


def test_banner_delayed_is_realized_no_discard_package():
    state = SimpleNamespace(
        jokers=[_joker("Banner"), _joker("Delayed Gratification")],
    )
    assert realized_banner_delayed_no_discard(state) is True


def test_banner_without_delayed_does_not_force_no_discard_preservation():
    state = SimpleNamespace(jokers=[_joker("Banner"), _joker("Scholar")])
    assert realized_banner_delayed_no_discard(state) is False


def test_delayed_without_banner_does_not_force_no_discard_preservation():
    state = SimpleNamespace(jokers=[_joker("Delayed Gratification"), _joker("Sly Joker")])
    assert realized_banner_delayed_no_discard(state) is False
