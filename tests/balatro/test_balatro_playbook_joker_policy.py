from games.balatro.build import (
    JokerBuildTransitionPlanner,
    JokerBuildValueEvaluator,
)
from games.balatro.joker import Joker, JokerContext
from games.balatro.joker_policy import JokerAcquisitionThresholds
from games.balatro.live.runtime.bond_autonomous_runner import (
    BondAwareLiveMemoryInjectedSingleStepRunner,
)
from games.balatro.playbook import default_balatro_playbooks
from games.balatro.playbook_joker_policy import PlaybookJokerAcquisitionPolicy
from games.balatro.state import BalatroState


class PlusMultJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is not None:
            context.score.mult += 8
        return context


def _red_white_state(*, ante: int = 1) -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.ante = ante
    state.money = 20
    state.joker_slots = 2
    return state


def _policy():
    evaluator = JokerBuildValueEvaluator()
    transition_planner = JokerBuildTransitionPlanner(evaluator=evaluator)
    return (
        PlaybookJokerAcquisitionPolicy(transition_planner),
        evaluator,
    )


def test_playbook_d2_policy_resolves_thresholds_from_current_state():
    policy, _ = _policy()
    state = _red_white_state()
    candidate = PlusMultJoker()
    candidate.cost = 0

    decision = policy.decide(state, candidate)
    expected = JokerAcquisitionThresholds.from_mapping(
        default_balatro_playbooks().for_state(state).thresholds_for("D2")
    )

    assert decision.thresholds == expected


def test_production_runner_shares_one_b3_evaluator_with_d2_and_shop_value():
    runner = BondAwareLiveMemoryInjectedSingleStepRunner(
        object(),
        bridge=object(),
        dispatcher=object(),
    )

    d2_policy = runner.shop_arbiter.joker_policy
    evaluator = d2_policy.transition_planner.evaluator

    assert runner.shop_policy.item_value_estimator.joker_build_value is evaluator
