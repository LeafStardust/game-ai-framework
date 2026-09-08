from games.balatro.actions import BalatroAction, END_ROUND
from games.balatro.environment import BalatroEnvironment
from games.balatro.planning import BalatroPlan
from games.balatro.tactics import TacticalPathCommitment


def test_tactical_commitment_returns_committed_action_when_valid():

    environment = BalatroEnvironment()
    action = BalatroAction(END_ROUND)
    plan = BalatroPlan(
        actions=[action],
        score=0.0,
        state=environment.state.copy()
    )

    commitment = TacticalPathCommitment()
    commitment.commit(plan)

    selected = commitment.next_action(environment)

    assert selected is not None
    assert selected.name == END_ROUND
    assert not commitment.active


def test_tactical_commitment_clears_invalid_path():

    environment = BalatroEnvironment()
    environment.state.phase = "SHOP"
    action = BalatroAction(END_ROUND)
    plan = BalatroPlan(
        actions=[action],
        score=0.0,
        state=environment.state.copy()
    )

    commitment = TacticalPathCommitment()
    commitment.commit(plan)

    assert commitment.next_action(environment) is None
    assert not commitment.active
