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


def test_d1_child_beam_shortlists_before_expensive_projection():
    state = _state()
    planner = D1LiveBlindClearPlanner(
        play_width=6,
        discard_width=0,
        child_play_width=1,
        horizon=4,
    )
    plays = planner.action_generator.generate_play_actions(state)

    def retained_structure_must_not_run(_cards):
        raise AssertionError("child shortlist must not scan retained-hand structure")

    planner.evaluator._retained_structure_value = retained_structure_must_not_run
    shortlist = planner._shortlist_child_plays(
        state,
        plays,
        planner.child_play_width,
    )

    assert len(shortlist) == 5
    assert len(shortlist) < len(plays)
    assert {len(action.cards) for action in shortlist} == {1, 2, 3, 4, 5}

    # Recursive child beam construction happens only after at least one search
    # node has been consumed. Simulate that boundary directly.
    planner.nodes_evaluated = 1
    actions = planner._candidate_actions(
        state,
        allow_discards=False,
        play_width=planner.child_play_width,
        discard_width=0,
    )

    assert len(actions) == planner.child_play_width
    assert planner.play_projections_evaluated == len(shortlist)
    assert planner.play_projections_evaluated == 5
    assert planner.play_projections_evaluated < len(plays)
    assert planner._play_projection_cache == {}
