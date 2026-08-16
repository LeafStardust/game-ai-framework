from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner
from games.balatro.state import BalatroState


def _state() -> BalatroState:
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [
        BalatroCard("K", "Clubs", live_id=0),
        BalatroCard("10", "Diamonds", live_id=1),
        BalatroCard("9", "Clubs", live_id=2),
        BalatroCard("6", "Diamonds", live_id=3),
        BalatroCard("4", "Spades", live_id=4),
        BalatroCard("4", "Hearts", live_id=5),
        BalatroCard("3", "Clubs", live_id=6),
        BalatroCard("2", "Clubs", live_id=7),
    ]
    state.deck = []
    state.score = 0
    state.hands_remaining = 4
    state.discards_remaining = 4
    state.blind = Blind(BlindType.SMALL, 10000)
    state.jokers = []
    return state


def test_d1_candidate_beam_projects_each_play_once_per_search():
    state = _state()
    planner = D1LiveBlindClearPlanner(
        play_width=6,
        discard_width=0,
        horizon=2,
    )
    plays = planner.action_generator.generate_play_actions(state)
    calls: dict[tuple[int, tuple[int, ...]], int] = {}
    original = planner.evaluator.project_play

    def counted(current_state, action):
        key = (id(current_state), planner._action_identity(action))
        calls[key] = calls.get(key, 0) + 1
        return original(current_state, action)

    planner.evaluator.project_play = counted

    planner._candidate_actions(state, allow_discards=False)

    assert len(plays) > planner.play_width
    assert planner.play_projections_evaluated == len(plays)
    assert len(calls) == len(plays)
    assert set(calls.values()) == {1}
    assert planner._play_projection_cache == {}

    planner.reset_search_stats()
    assert planner.play_projections_evaluated == 0

    planner._candidate_actions(state, allow_discards=False)

    assert planner.play_projections_evaluated == len(plays)
    assert set(calls.values()) == {2}
    assert planner._play_projection_cache == {}


def test_d1_child_beam_never_enumerates_all_play_subsets():
    state = _state()
    planner = D1LiveBlindClearPlanner(
        play_width=6,
        discard_width=0,
        child_play_width=1,
        horizon=4,
    )
    exhaustive_count = len(planner.action_generator.generate_play_actions(state))

    def exhaustive_generation_must_not_run(_state):
        raise AssertionError("recursive child beam must not enumerate Play subsets")

    planner.action_generator.generate_play_actions = exhaustive_generation_must_not_run
    planner.nodes_evaluated = 1
    actions = planner._candidate_actions(
        state,
        allow_discards=False,
        play_width=planner.child_play_width,
        discard_width=0,
    )

    assert len(actions) == planner.child_play_width
    assert planner.play_projections_evaluated <= 3
    assert planner.play_projections_evaluated < exhaustive_count
    assert planner._play_projection_cache == {}


def test_d1_child_beam_never_enumerates_all_discard_subsets():
    state = _state()
    planner = D1LiveBlindClearPlanner(
        play_width=6,
        discard_width=1,
        child_play_width=1,
        child_discard_width=1,
        horizon=4,
    )

    def exhaustive_play_generation_must_not_run(_state):
        raise AssertionError("recursive child beam must not enumerate Play subsets")

    def exhaustive_discard_generation_must_not_run(_state):
        raise AssertionError("recursive child beam must not enumerate Discard subsets")

    planner.action_generator.generate_play_actions = exhaustive_play_generation_must_not_run
    planner.action_generator.generate_discard_actions = exhaustive_discard_generation_must_not_run
    planner.nodes_evaluated = 1
    actions = planner._candidate_actions(
        state,
        allow_discards=True,
        play_width=planner.child_play_width,
        discard_width=planner.child_discard_width,
    )

    assert sum(action.name == "PLAY_CARDS" for action in actions) == 1
    assert sum(action.name == "DISCARD_CARDS" for action in actions) == 1
