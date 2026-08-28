from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.d1_root_discard_reserve_policy import (
    _candidate_actions_with_root_discard_reserve,
)


def _action(name, width):
    return SimpleNamespace(name=name, cards=tuple(object() for _ in range(width)))


def test_initial_root_appends_legal_discard_when_underlying_beam_is_play_only(monkeypatch):
    play = _action(PLAY_CARDS, 2)
    discard_one = _action(DISCARD_CARDS, 1)
    discard_wide = _action(DISCARD_CARDS, 5)

    class Generator:
        def generate_discard_actions(self, state):
            del state
            return [discard_one, discard_wide]

    planner = SimpleNamespace(
        nodes_evaluated=0,
        discard_width=2,
        deadline=None,
        action_generator=Generator(),
    )
    state = SimpleNamespace(discards_remaining=4, hand=())

    monkeypatch.setattr(
        "games.balatro.d1_root_discard_reserve_policy._cheap_discard_key",
        lambda state, action: (0.0, len(action.cards)),
    )

    def underlying(self, state, *, allow_discards, play_width=None, discard_width=None):
        del self, state, allow_discards, play_width, discard_width
        return [play]

    candidates = _candidate_actions_with_root_discard_reserve(
        underlying,
        planner,
        state,
        allow_discards=True,
    )

    assert candidates[0] is play
    assert any(action.name == DISCARD_CARDS for action in candidates)
    assert discard_wide in candidates


def test_existing_discard_evidence_is_not_duplicated():
    play = _action(PLAY_CARDS, 2)
    discard = _action(DISCARD_CARDS, 3)
    planner = SimpleNamespace(
        nodes_evaluated=0,
        discard_width=2,
        deadline=None,
        action_generator=SimpleNamespace(
            generate_discard_actions=lambda state: (_ for _ in ()).throw(
                AssertionError("existing discard evidence must be preserved as-is")
            )
        ),
    )
    state = SimpleNamespace(discards_remaining=4)

    def underlying(self, state, *, allow_discards, play_width=None, discard_width=None):
        del self, state, allow_discards, play_width, discard_width
        return [play, discard]

    candidates = _candidate_actions_with_root_discard_reserve(
        underlying,
        planner,
        state,
        allow_discards=True,
    )

    assert candidates == [play, discard]


def test_active_hook_does_not_append_projected_root_discard_reserve(monkeypatch):
    play = _action(PLAY_CARDS, 2)

    planner = SimpleNamespace(
        nodes_evaluated=0,
        discard_width=2,
        deadline=None,
        action_generator=SimpleNamespace(
            generate_discard_actions=lambda state: (_ for _ in ()).throw(
                AssertionError("active Hook must not generate reserved root discards")
            )
        ),
    )
    state = SimpleNamespace(
        boss_name="The Hook",
        discards_remaining=4,
    )
    monkeypatch.setattr(
        "games.balatro.d1_root_discard_reserve_policy._active_hook",
        lambda state: True,
    )

    def underlying(self, state, *, allow_discards, play_width=None, discard_width=None):
        del self, state, allow_discards, play_width, discard_width
        return [play]

    candidates = _candidate_actions_with_root_discard_reserve(
        underlying,
        planner,
        state,
        allow_discards=True,
    )

    assert candidates == [play]
