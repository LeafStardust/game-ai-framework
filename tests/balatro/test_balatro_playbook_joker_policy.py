from types import SimpleNamespace
from unittest.mock import patch

from games.balatro.build import (
    BalatroBuildProfiler,
    JokerBuildTransitionPlanner,
    JokerBuildValueEvaluator,
)
from games.balatro.build.profile import BalatroPlaystyleIntentTracker
from games.balatro.card import BalatroCard
from games.balatro.bonds.strategy_semantics import StrategyCommitment
from games.balatro.joker import Joker, JokerContext
from games.balatro.joker_policy import JokerAcquisitionThresholds
from games.balatro.jokers.baron import BaronJoker
from games.balatro.jokers.business_card import BusinessCardJoker
from games.balatro.jokers.mime import MimeJoker
from games.balatro.jokers.ride_the_bus import RideTheBusJoker
from games.balatro.live.runtime.playstyle_autonomous_runner import (
    PlaystyleAwareLiveMemoryInjectedSingleStepRunner,
)
from games.balatro.playbook import default_balatro_playbooks
from games.balatro.playbook_joker_policy import (
    PlaybookJokerAcquisitionPolicy,
    _strategy_completion_bonus,
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
    profiler = BalatroBuildProfiler()
    tracker = BalatroPlaystyleIntentTracker()
    evaluator = JokerBuildValueEvaluator(
        profiler=profiler,
        intent_tracker=tracker,
    )
    transition_planner = JokerBuildTransitionPlanner(evaluator=evaluator)
    return (
        PlaybookJokerAcquisitionPolicy(transition_planner),
        evaluator,
        profiler,
        tracker,
    )


def test_playbook_d2_policy_resolves_thresholds_from_current_state():
    policy, _, _, _ = _policy()
    state = _red_white_state()
    candidate = PlusMultJoker()
    candidate.cost = 0

    decision = policy.decide(state, candidate)
    expected = JokerAcquisitionThresholds.from_mapping(
        default_balatro_playbooks().for_state(state).thresholds_for("D2")
    )

    assert decision.thresholds == expected


def test_d2_reuses_locked_run_scoped_playstyle_intent_after_build_changes():
    policy, evaluator, _, tracker = _policy()
    state = _red_white_state(ante=4)
    state.jokers = [RideTheBusJoker()]
    candidate = PlusMultJoker()
    candidate.cost = 0

    policy.decide(state, candidate)
    assert not tracker.locked

    state.ante = 5
    policy.decide(state, candidate)
    assert tracker.locked

    state.jokers = [BusinessCardJoker()]
    conflicting = evaluator.evaluate(state, BusinessCardJoker())

    assert conflicting.playstyle_locked is True
    assert conflicting.playstyle_fit < 0.0
    assert any("mode=LOCKED" in note for note in conflicting.rationale)


def test_production_runner_shares_one_b3_evaluator_with_d2_and_shop_value():
    runner = PlaystyleAwareLiveMemoryInjectedSingleStepRunner(
        object(),
        bridge=object(),
        dispatcher=object(),
    )

    d2_policy = runner.shop_arbiter.joker_policy
    evaluator = d2_policy.transition_planner.evaluator

    assert evaluator.profiler is runner.playstyle_profiler
    assert evaluator.intent_tracker is runner.playstyle_intent_tracker
    assert runner.shop_policy.item_value_estimator.joker_build_value is evaluator


def test_d2_rewards_missing_component_that_advances_current_forming_strategy():
    state = _red_white_state()
    state.jokers = [BaronJoker()]
    state.deck = [
        BalatroCard("K", "Hearts", enhancement="Steel"),
        BalatroCard("K", "Spades", enhancement="Steel"),
        BalatroCard("K", "Clubs"),
        BalatroCard("K", "Diamonds"),
    ]

    bonus, rationale = _strategy_completion_bonus(state, MimeJoker())

    assert bonus > 0.0
    assert any("strategy=baron_mime_steel" in note for note in rationale)
    assert any("missing components=" in note for note in rationale)


def test_d2_rewards_resolving_same_strategy_missing_feature_without_other_progress():
    state = _red_white_state()
    before_plan = SimpleNamespace(
        strategy_id="semantic_engine",
        commitment=StrategyCommitment.FORMING,
        completion=0.25,
        missing_components=(),
        missing_features=("economy",),
    )
    after_plan = SimpleNamespace(
        strategy_id="semantic_engine",
        commitment=StrategyCommitment.FORMING,
        completion=0.25,
        missing_components=(),
        missing_features=(),
    )
    before_composition = SimpleNamespace(strategy_plan=before_plan)
    after_composition = SimpleNamespace(strategy_plan=after_plan)

    with patch(
        "games.balatro.playbook.red_white.joker_policy.evaluate_bond_composition",
        side_effect=[((), before_composition), ((), after_composition)],
    ):
        bonus, rationale = _strategy_completion_bonus(state, PlusMultJoker())

    assert bonus == 0.5
    assert any("missing features=1->0 resolved=1" in note for note in rationale)


def test_d2_does_not_reward_unrelated_candidate_as_strategy_completion():
    state = _red_white_state()
    state.jokers = [BaronJoker()]
    state.deck = [
        BalatroCard("K", "Hearts", enhancement="Steel"),
        BalatroCard("K", "Spades", enhancement="Steel"),
        BalatroCard("K", "Clubs"),
        BalatroCard("K", "Diamonds"),
    ]

    bonus, rationale = _strategy_completion_bonus(state, PlusMultJoker())

    assert bonus == 0.0
    assert rationale == ()
