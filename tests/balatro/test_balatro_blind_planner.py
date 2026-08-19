from games.balatro.blind_planner import BlindCompletionPlanner
from games.balatro.card import BalatroCard
from games.balatro.environment import BalatroEnvironment
from games.balatro.evaluator import BalatroEvaluator
from games.balatro.planning import BalatroGoalDirectedPlanner


def test_blind_completion_planner_targets_shop_phase():

    environment = BalatroEnvironment()
    environment.state.hand = [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Hearts"),
        BalatroCard("Q", "Hearts"),
        BalatroCard("J", "Hearts"),
        BalatroCard("10", "Hearts"),
    ]
    environment.state.blind.requirement = 1

    planner = BlindCompletionPlanner(
        BalatroGoalDirectedPlanner(
            BalatroEvaluator(),
            environment
        )
    )

    plan = planner.synthesize(
        max_depth=1
    )

    assert plan is not None
    assert plan.state.phase == "SHOP"
