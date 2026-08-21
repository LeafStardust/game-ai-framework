from games.balatro.build_component_roles import (
    BuildComponentRole,
    BuildComponentRoleClassifier,
)
from games.balatro.state import BalatroState


class JollyJoker:
    name = "Jolly Joker"


def test_runtime_component_roles_recover_strategy_tracker_when_not_forwarded():
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.ante = 2
    state.jokers = [JollyJoker()]
    state.joker_slots = 5

    component = BuildComponentRoleClassifier().classify(state)[0]

    assert component.role != BuildComponentRole.FILLER
    assert component.strategy_id == "pair"
