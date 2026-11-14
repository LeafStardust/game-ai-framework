from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import BlindType
from games.balatro.env.ppo_terminal_loss_census import (
    _classification,
    _decision_event,
    _summary,
)
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue


def _plan(cards, indices, *, exact, clear, score):
    return LiveBlindPlan(
        action=BalatroAction(PLAY_CARDS, cards=[cards[index] for index in indices]),
        value=LiveBlindPlanValue(
            clear_probability=clear,
            expected_progress=clear,
            expected_score=score,
            expected_hands_remaining=1.0,
            expected_discards_remaining=0.0,
        ),
        horizon=2,
        exact=exact,
        candidate_count=2,
    )


def test_terminal_loss_event_records_different_exact_clear_and_search_state():
    cards = tuple(object() for _ in range(3))
    selected = _plan(cards, (0,), exact=False, clear=1.0, score=100.0)
    exact = _plan(cards, (1,), exact=True, clear=1.0, score=200.0)
    state = SimpleNamespace(
        hand=list(cards),
        ante=1,
        round=3,
        boss_name="The Club",
        blind=SimpleNamespace(type=BlindType.BOSS, requirement=600),
        score=0,
        hands_remaining=2,
        discards_remaining=1,
    )
    attempt = SimpleNamespace(
        horizon=2,
        samples=10,
        nodes_evaluated=10,
        max_nodes=10,
        budget_exceeded=True,
        confirmation=False,
        best_exact=True,
        best_clear_probability=1.0,
        best_expected_score=200.0,
    )
    decision = SimpleNamespace(
        action=selected.action,
        selected_plan=selected,
        completed_search_plans=(selected, exact),
        search_attempts=(attempt,),
    )
    event = _decision_event(state, decision)
    assert event["different_exact_clear_plans"] == [{
        "action": {"name": PLAY_CARDS, "indices": [1]},
        "clear_probability": 1.0,
        "expected_score": 200.0,
        "horizon": 2,
        "exact": True,
    }]
    assert event["search_attempts"][0]["budget_exceeded"] is True
    assert _classification([event]) == "DIFFERENT_EXACT_CLEAR_AVAILABLE"


def test_terminal_loss_classification_is_mutually_exclusive_and_fail_closed():
    base = {
        "different_exact_clear_plans": [],
        "selected_plan": {"exact": True},
        "search_attempts": [],
    }
    assert _classification([base]) == "NO_EXACT_CLEAR_WITH_EXACT_SELECTION"
    inexact = {**base, "selected_plan": {"exact": False}}
    assert _classification([inexact]) == "NO_EXACT_CLEAR_WITH_INEXACT_SELECTION"
    exhausted = {**inexact, "search_attempts": [{"budget_exceeded": True}]}
    assert _classification([exhausted]) == "NO_EXACT_CLEAR_WITH_BUDGET_EXHAUSTION"


def test_terminal_loss_summary_selects_closest_then_earliest_representative():
    def episode(index, margin, label, blind_type="BOSS"):
        return {
            "episode_index": index,
            "game_seed": f"SEED{index}",
            "status": "LOSS",
            "classification": label,
            "metrics": {"terminal_chip_margin": margin},
            "terminal_blind": {"type": blind_type, "requirement": 600},
            "terminal_decisions": [{
                "different_exact_clear_plans": [],
                "search_attempts": [],
            }],
        }

    label = "NO_EXACT_CLEAR_WITH_EXACT_SELECTION"
    summary = _summary((episode(2, -10, label), episode(1, -10, label)))
    assert summary["loss_count"] == 2
    assert summary["canonical_representatives"] == [{
        "classification": label,
        "episode_index": 1,
        "game_seed": "SEED1",
        "terminal_chip_margin": -10,
    }]
