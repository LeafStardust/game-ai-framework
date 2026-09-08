from games.balatro.card import BalatroCard
from games.balatro.environment import BalatroEnvironment
from games.balatro.evaluator import BalatroEvaluator
from games.balatro.planning import BalatroGoalDirectedPlanner


def test_goal_directed_planner_returns_path_toward_goal():

    environment = BalatroEnvironment()
    environment.state.hand = [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Clubs"),
        BalatroCard("Q", "Diamonds"),
        BalatroCard("J", "Spades"),
        BalatroCard("10", "Hearts"),
    ]

    planner = BalatroGoalDirectedPlanner(
        BalatroEvaluator(),
        environment
    )

    plan = planner.plan(
        lambda state: state.round >= 2,
        max_depth=1
    )

    assert plan is not None
    assert plan.actions
    assert plan.state.round >= 2
