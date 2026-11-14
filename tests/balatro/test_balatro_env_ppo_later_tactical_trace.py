from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.env.ppo_later_tactical_trace import (
    _distribution,
    _exact_counterfactual_plan,
    _representative,
)
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue


def _episode(index, requirement, margin, progress=0.5):
    return {
        "episode_index": index,
        "metrics": {
            "ante_reached": 1,
            "terminal_blind_requirement": requirement,
            "terminal_chip_margin": margin,
            "terminal_requirement_progress": progress,
        },
    }


def test_later_tactical_trace_selects_closest_post_first_loss_canonically():
    diagnostics = {
        "episodes": (
            _episode(0, 300.0, -1.0),
            _episode(1, 600.0, -12.0),
            _episode(2, 450.0, -12.0),
            _episode(3, 800.0, -30.0),
        )
    }
    assert _representative(diagnostics)["episode_index"] == 1


def test_later_tactical_distribution_is_sorted_and_exact():
    episodes = (
        _episode(0, 600.0, -1.0, 0.5),
        _episode(1, 450.0, -1.0, 0.75),
        _episode(2, 600.0, -1.0, 1.0),
    )
    assert _distribution(episodes) == [
        {
            "ante_reached": 1,
            "terminal_blind_requirement": 450.0,
            "episode_count": 1,
            "mean_terminal_requirement_progress": 0.75,
        },
        {
            "ante_reached": 1,
            "terminal_blind_requirement": 600.0,
            "episode_count": 2,
            "mean_terminal_requirement_progress": 0.75,
        },
    ]


def test_later_tactical_counterfactual_uses_only_different_exact_clear():
    cards = tuple(object() for _ in range(3))
    state = SimpleNamespace(hand=list(cards))

    def plan(indices, *, probability, score, exact):
        return LiveBlindPlan(
            action=BalatroAction(PLAY_CARDS, cards=[cards[index] for index in indices]),
            value=LiveBlindPlanValue(
                clear_probability=probability,
                expected_progress=probability,
                expected_score=score,
                expected_hands_remaining=1.0,
                expected_discards_remaining=0.0,
            ),
            horizon=2,
            exact=exact,
            candidate_count=3,
        )

    selected = plan((0,), probability=1.0, score=100.0, exact=False)
    lower = plan((1,), probability=1.0, score=200.0, exact=True)
    higher = plan((2,), probability=1.0, score=300.0, exact=True)
    production = SimpleNamespace(
        action=selected.action,
        completed_search_plans=(lower, higher),
    )
    assert _exact_counterfactual_plan(state, production) is higher
