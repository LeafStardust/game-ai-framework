from dataclasses import dataclass
from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import BlindType
from games.balatro.env.ppo_boss_progress_shadow import (
    _acceptance,
    select_boss_progress_shadow_decision,
)
from games.balatro.env.ppo_candidate_evaluation import fixed_candidate_policy_seed
from games.balatro.env.seeded_evaluation import FIXED_SEEDED_EPISODES
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.hand_action_policy import PACE_RECOVERY


def _plan(cards, name, indices, *, exact=True, score=100.0):
    return LiveBlindPlan(
        action=BalatroAction(name, cards=[cards[index] for index in indices]),
        value=LiveBlindPlanValue(
            clear_probability=0.0,
            expected_progress=0.0,
            expected_score=score,
            expected_hands_remaining=1.0,
            expected_discards_remaining=0.0,
        ),
        horizon=2,
        exact=exact,
        candidate_count=2,
    )


@dataclass(frozen=True)
class _Decision:
    mode: str
    action: BalatroAction
    selected_plan: LiveBlindPlan
    completed_search_plans: tuple[LiveBlindPlan, ...]
    rationale: tuple[str, ...] = ()


def test_boss_progress_shadow_selects_highest_exact_play_only_for_owned_shape():
    cards = tuple(object() for _ in range(4))
    discard = _plan(cards, DISCARD_CARDS, (0,))
    lower = _plan(cards, PLAY_CARDS, (1,), score=150.0)
    higher = _plan(cards, PLAY_CARDS, (2,), score=200.0)
    production = _Decision(
        mode=PACE_RECOVERY,
        action=discard.action,
        selected_plan=discard,
        completed_search_plans=(lower, higher),
    )
    state = SimpleNamespace(
        hand=list(cards), score=10, blind=SimpleNamespace(type=BlindType.BOSS)
    )
    selected = select_boss_progress_shadow_decision(state, production)
    assert selected.action is higher.action
    assert selected.selected_plan is higher

    zero = SimpleNamespace(
        hand=list(cards), score=0, blind=SimpleNamespace(type=BlindType.BOSS)
    )
    ordinary = SimpleNamespace(
        hand=list(cards), score=10, blind=SimpleNamespace(type=BlindType.BIG)
    )
    assert select_boss_progress_shadow_decision(zero, production) is production
    assert select_boss_progress_shadow_decision(ordinary, production) is production


def test_boss_progress_shadow_acceptance_is_frozen_and_paired():
    def arm(ante):
        return {
            "status": "LOSS",
            "metrics": {
                "ante_reached": ante,
                "terminal_requirement_progress": 0.9,
                "minimum_money": 1,
                "terminal_money": 2,
            },
        }

    episodes = []
    for spec in FIXED_SEEDED_EPISODES:
        episodes.append({
            "episode_index": spec.episode_index,
            "game_seed": spec.game_seed,
            "policy_seed": fixed_candidate_policy_seed(spec),
            "production": arm(1),
            "shadow": arm(2),
        })
    summary = _acceptance(episodes)
    assert summary["accepted"] is True
    assert all(summary["gates"].values())
