from types import SimpleNamespace

from games.balatro.build import (
    JokerBuildTransitionPlanner,
    JokerBuildValueEvaluator,
)
from games.balatro.joker import Joker, JokerContext
from games.balatro.joker_policy import (
    BUY,
    HOLD,
    JokerAcquisitionDecision,
    JokerAcquisitionThresholds,
)
from games.balatro.live.runtime.bond_autonomous_runner import (
    BondAwareLiveMemoryInjectedSingleStepRunner,
)
from games.balatro.playbook import default_balatro_playbooks
from games.balatro.playbook_joker_policy import PlaybookJokerAcquisitionPolicy
from games.balatro.playbook.red_white.joker_policy import (
    PlaybookJokerAcquisitionPolicy as CanonicalPlaybookJokerAcquisitionPolicy,
    _discard_conflict_indices,
    _enforce_discard_resource_conflict,
)
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


def test_production_import_uses_the_canonical_wrapped_d2_class():
    assert PlaybookJokerAcquisitionPolicy is CanonicalPlaybookJokerAcquisitionPolicy


def test_burglar_blocks_trading_card_future_bond_value():
    state = _red_white_state()
    state.jokers = [SimpleNamespace(name="Burglar")]
    candidate = SimpleNamespace(name="Trading Card")
    core_decision = JokerAcquisitionDecision(
        action=BUY,
        candidate="Trading Card",
        selected=None,
        options=(),
        thresholds=JokerAcquisitionThresholds(),
        rationale=("core D2 awarded future deck-thinning Bond value",),
    )

    decision = _enforce_discard_resource_conflict(
        state,
        candidate,
        core_decision,
    )

    assert decision.action == HOLD
    assert any("Burglar removes the activation/count window" in note for note in decision.rationale)
    assert any("future Bond potential cannot justify" in note for note in decision.rationale)


def test_burglar_conflicts_with_every_owned_discard_trigger():
    discard_jokers = (
        "Burnt Joker",
        "Castle",
        "Faceless Joker",
        "Hit the Road",
        "Mail-In Rebate",
        "Trading Card",
        "Yorick",
    )
    state = _red_white_state()
    state.jokers = [SimpleNamespace(name=name) for name in discard_jokers]

    assert _discard_conflict_indices(
        state,
        SimpleNamespace(name="Burglar"),
    ) == tuple(range(len(discard_jokers)))


def test_burglar_conflicts_with_discard_count_payoffs_and_sources():
    state = _red_white_state()
    state.jokers = [
        SimpleNamespace(name="Banner"),
        SimpleNamespace(name="Delayed Gratification"),
        SimpleNamespace(name="Drunkard"),
        SimpleNamespace(name="Merry Andy"),
    ]

    assert _discard_conflict_indices(
        state,
        SimpleNamespace(name="Burglar"),
    ) == (0, 1, 2, 3)


def test_discard_trigger_conflicts_with_owned_burglar():
    state = _red_white_state()
    state.jokers = [SimpleNamespace(name="Burglar")]

    for name in ("Mail-In Rebate", "Trading Card", "Hit the Road", "Yorick"):
        assert _discard_conflict_indices(
            state,
            SimpleNamespace(name=name),
        ) == (0,)
