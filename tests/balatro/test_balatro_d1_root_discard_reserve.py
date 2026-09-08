from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner


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

    planner = LiveBlindClearPlanner(action_generator=Generator(), discard_width=2)
    planner.nodes_evaluated = 0
    planner.deadline = None
    state = SimpleNamespace(discards_remaining=4, hand=())

    monkeypatch.setattr(
        LiveBlindClearPlanner,
        "_cheap_discard_key",
        staticmethod(lambda state, action: (0.0, len(action.cards))),
    )

    candidates = planner._ensure_root_discard_reserve(
        state,
        [play],
        allow_discards=True,
        discard_limit=planner.discard_width,
    )

    assert candidates[0] is play
    assert any(action.name == DISCARD_CARDS for action in candidates)
    assert discard_wide in candidates


def test_existing_discard_evidence_is_not_duplicated():
    play = _action(PLAY_CARDS, 2)
    discard = _action(DISCARD_CARDS, 3)

    class Generator:
        def generate_discard_actions(self, state):
            del state
            raise AssertionError("existing discard evidence must be preserved as-is")

    planner = LiveBlindClearPlanner(action_generator=Generator(), discard_width=2)
    planner.nodes_evaluated = 0
    planner.deadline = None
    state = SimpleNamespace(discards_remaining=4)

    candidates = planner._ensure_root_discard_reserve(
        state,
        [play, discard],
        allow_discards=True,
        discard_limit=planner.discard_width,
    )

    assert candidates == [play, discard]


def test_active_hook_does_not_append_projected_root_discard_reserve(monkeypatch):
    play = _action(PLAY_CARDS, 2)

    class Generator:
        def generate_discard_actions(self, state):
            del state
            raise AssertionError("active Hook must not generate reserved root discards")

    planner = LiveBlindClearPlanner(action_generator=Generator(), discard_width=2)
    planner.nodes_evaluated = 0
    planner.deadline = None
    state = SimpleNamespace(
        boss_name="The Hook",
        discards_remaining=4,
    )
    monkeypatch.setattr(
        "games.balatro.live.blind_clear_planner._active_hook",
        lambda state: True,
    )

    candidates = planner._ensure_root_discard_reserve(
        state,
        [play],
        allow_discards=True,
        discard_limit=planner.discard_width,
    )

    assert candidates == [play]
