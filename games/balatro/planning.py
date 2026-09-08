from collections.abc import Callable
from dataclasses import dataclass

from framework.core.action import Action
from framework.core.state import GameState
from framework.decision.evaluator import Evaluator

from games.balatro.environment import BalatroEnvironment


@dataclass
class BalatroPlan:
    actions: list[Action]
    score: float
    state: GameState


class BalatroGoalDirectedPlanner:

    def __init__(
        self,
        evaluator: Evaluator,
        environment: BalatroEnvironment
    ):
        self.evaluator = evaluator
        self.environment = environment

    def plan(
        self,
        goal: Callable[[GameState], bool],
        max_depth: int = 2,
        beam_width: int = 5
    ) -> BalatroPlan | None:

        if goal(self.environment.state):
            return BalatroPlan(
                actions=[],
                score=0.0,
                state=self.environment.state.copy()
            )

        frontier = [
            (
                self.environment.copy(),
                [],
                0.0
            )
        ]

        for _ in range(max_depth):
            candidates = []

            for environment, path, path_score in frontier:
                for action in environment.get_actions():
                    next_environment = environment.copy()
                    next_environment.execute_action(
                        action.copy()
                    )
                    next_state = next_environment.get_state()
                    score = path_score + self.evaluator.evaluate(
                        next_state,
                        action
                    )
                    next_path = path + [action]

                    if goal(next_state):
                        return BalatroPlan(
                            actions=next_path,
                            score=score,
                            state=next_state
                        )

                    candidates.append(
                        (
                            next_environment,
                            next_path,
                            score
                        )
                    )

            candidates.sort(
                key=lambda candidate: candidate[2],
                reverse=True
            )
            frontier = candidates[:beam_width]

            if not frontier:
                break

        if not frontier:
            return None

        environment, path, score = max(
            frontier,
            key=lambda candidate: candidate[2]
        )

        return BalatroPlan(
            actions=path,
            score=score,
            state=environment.get_state()
        )
