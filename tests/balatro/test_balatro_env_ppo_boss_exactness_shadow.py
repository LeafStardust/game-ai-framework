from dataclasses import dataclass

from games.balatro.env.ppo_boss_exactness_shadow import _acceptance
from games.balatro.env.ppo_candidate_evaluation import fixed_candidate_policy_seed
from games.balatro.env.seeded_evaluation import FIXED_SEEDED_EPISODES
from games.balatro.live.strategy_hand_policy import _boss_projection_plans


@dataclass(frozen=True)
class _Plan:
    exact: bool


def test_boss_exactness_shadow_changes_only_unconfirmed_downgrade():
    exact = _Plan(exact=True)
    inexact = _Plan(exact=False)
    production = _boss_projection_plans(
        (exact, inexact), unconfirmed=True, preserve_exactness=False
    )
    assert production[0].exact is False
    assert production[1] is inexact
    shadow = _boss_projection_plans(
        (exact, inexact), unconfirmed=True, preserve_exactness=True
    )
    assert shadow == (exact, inexact)
    ordinary = _boss_projection_plans(
        (exact, inexact), unconfirmed=False, preserve_exactness=False
    )
    assert ordinary == (exact, inexact)


def test_boss_exactness_shadow_acceptance_is_frozen_and_paired():
    def arm(ante, *, status="LOSS"):
        return {
            "status": status,
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
