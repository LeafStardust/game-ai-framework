from dataclasses import dataclass
from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import BlindType
from games.balatro.env.ppo_boss_exact_shadow import (
    _acceptance,
    select_boss_exact_shadow_decision,
)
from games.balatro.env.ppo_candidate_evaluation import fixed_candidate_policy_seed
from games.balatro.env.seeded_evaluation import FIXED_SEEDED_EPISODES
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue


@dataclass(frozen=True)
class _Decision:
    action: BalatroAction
    selected_plan: LiveBlindPlan
    completed_search_plans: tuple[LiveBlindPlan, ...]
    rationale: tuple[str, ...] = ()


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


def test_boss_shadow_selects_only_different_exact_clear():
    cards = tuple(object() for _ in range(3))
    state = SimpleNamespace(hand=list(cards), blind=SimpleNamespace(type=BlindType.BOSS))
    production_plan = _plan(cards, (0,), exact=False, clear=1.0, score=100.0)
    lower = _plan(cards, (1,), exact=True, clear=1.0, score=150.0)
    exact = _plan(cards, (2,), exact=True, clear=1.0, score=200.0)
    production = _Decision(
        action=production_plan.action,
        selected_plan=production_plan,
        completed_search_plans=(lower, exact),
        rationale=(),
    )
    selected = select_boss_exact_shadow_decision(state, production)
    assert selected.action is exact.action
    assert selected.selected_plan is exact


def test_boss_shadow_preserves_nonboss_and_nonexact_production():
    cards = tuple(object() for _ in range(2))
    production_plan = _plan(cards, (0,), exact=False, clear=1.0, score=100.0)
    alternative = _plan(cards, (1,), exact=False, clear=1.0, score=200.0)
    same_action = _plan(cards, (0,), exact=True, clear=1.0, score=300.0)
    production = _Decision(
        action=production_plan.action,
        selected_plan=production_plan,
        completed_search_plans=(alternative,),
        rationale=(),
    )
    ordinary = SimpleNamespace(hand=list(cards), blind=SimpleNamespace(type=BlindType.SMALL))
    boss = SimpleNamespace(hand=list(cards), blind=SimpleNamespace(type=BlindType.BOSS))
    assert select_boss_exact_shadow_decision(ordinary, production) is production
    assert select_boss_exact_shadow_decision(boss, production) is production
    same_only = _Decision(
        action=production_plan.action,
        selected_plan=production_plan,
        completed_search_plans=(same_action,),
    )
    assert select_boss_exact_shadow_decision(boss, same_only) is same_only


def test_boss_shadow_acceptance_gates_are_paired_and_predeclared():
    def arm(*, ante, progress, cash, terminal, status="LOSS"):
        return {
            "status": status,
            "metrics": {
                "ante_reached": ante,
                "terminal_requirement_progress": progress,
                "minimum_money": cash,
                "terminal_money": terminal,
            },
        }

    episodes = []
    for spec in FIXED_SEEDED_EPISODES:
        episodes.append({
            "episode_index": spec.episode_index,
            "game_seed": spec.game_seed,
            "policy_seed": fixed_candidate_policy_seed(spec),
            "production": arm(ante=1, progress=0.9, cash=1, terminal=2),
            "shadow": arm(ante=2, progress=0.9, cash=1, terminal=2),
            "shadow_events": [],
        })
    episodes[1]["shadow_events"] = [{
        "blind_requirement": 600,
        "boss_name": "The Club",
        "exact": True,
        "clear_probability": 1.0,
    }]
    summary = _acceptance(episodes)
    assert summary["accepted"] is True
    assert all(summary["gates"].values())
