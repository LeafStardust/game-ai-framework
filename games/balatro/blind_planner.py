from games.balatro.planning import (
    BalatroGoalDirectedPlanner,
    BalatroPlan,
)


class BlindCompletionPlanner:

    def __init__(
        self,
        planner: BalatroGoalDirectedPlanner
    ):
        self.planner = planner

    def synthesize(
        self,
        max_depth: int = 3,
        beam_width: int = 5
    ) -> BalatroPlan | None:

        return self.planner.plan(
            lambda state: state.phase == "SHOP",
            max_depth=max_depth,
            beam_width=beam_width
        )
