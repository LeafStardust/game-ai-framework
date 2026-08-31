from types import SimpleNamespace

import games.balatro.live.hand_action_policy as hand_action_policy
from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.card_selector import CardSelector
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.hand_action_policy import (
    LiveHandActionDecisionEngine,
    LiveHandActionPolicy,
)
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.live.path_aware_hand_action_engine import PathAwareLiveHandActionDecisionEngine
from games.balatro.playbook import default_balatro_playbooks


class _FakeEvaluator:
    def project_play(self, state, action):
        return SimpleNamespace(
            expected_hand_score=float(action.target.get("immediate_score", 0.0))
        )

    def evaluate(self, state, action):
        return float(action.target.get("fallback_value", 0.0))


class _ImmediatePlanner:
    def __init__(self):
        self.evaluator = _FakeEvaluator()
        self.seen_allow_discards = None
        self.seen_depths = []
        self.nodes_evaluated = 0
        self.play = BalatroAction(
            PLAY_CARDS,
            cards=["play"],
            target={"immediate_score": 30.0, "fallback_value": 10.0},
        )
        self.discard = BalatroAction(
            DISCARD_CARDS,
            cards=["discard"],
            target={"fallback_value": 20.0},
        )

    def _require_state(self, state):
        return None

    def reset_search_stats(self):
        self.nodes_evaluated = 0

    def _candidate_actions(self, state, *, allow_discards):
        self.seen_allow_discards = allow_discards
        return [self.play, self.discard] if allow_discards else [self.play]

    def _estimate_action(self, state, action, depth):
        self.seen_depths.append(depth)
        self.nodes_evaluated += 1
        return SimpleNamespace(
            action=action,
            value=LiveBlindPlanValue(
                clear_probability=0.0,
                expected_progress=0.1,
                expected_score=20.0 if action.name == DISCARD_CARDS else 30.0,
                expected_hands_remaining=2.0,
                expected_discards_remaining=1.0,
            ),
            exact=True,
        )

    @staticmethod
    def _estimate_key(estimate):
        return (estimate.value.expected_score,)


def _state():
    return SimpleNamespace(
        phase="SELECTING_HAND",
        hand=["play", "discard"],
        score=0,
        blind=SimpleNamespace(requirement=300),
        hands_remaining=3,
        discards_remaining=2,
    )


def _plan(action_name, marker, *, immediate_score=0.0, fallback_value=0.0):
    return LiveBlindPlan(
        action=BalatroAction(
            action_name,
            cards=[marker],
            target={
                "immediate_score": immediate_score,
                "fallback_value": fallback_value,
            },
        ),
        value=LiveBlindPlanValue(
            clear_probability=0.0,
            expected_progress=0.1,
            expected_score=immediate_score,
            expected_hands_remaining=2.0,
            expected_discards_remaining=1.0,
        ),
        horizon=1,
        exact=True,
        candidate_count=2,
    )


def test_immediate_budget_fallback_is_depth_one_and_keeps_discards():
    planner = _ImmediatePlanner()
    engine = LiveHandActionDecisionEngine(
        planner=planner,
        policy=LiveHandActionPolicy(evaluator=planner.evaluator),
    )

    plans = engine._rank_immediate_plans(_state())

    assert planner.seen_allow_discards is True
    assert planner.seen_depths == [1, 1]
    assert {plan.action.name for plan in plans} == {PLAY_CARDS, DISCARD_CARDS}
    assert all(plan.horizon == 1 for plan in plans)


def test_final_fallback_goes_directly_to_immediate_beam(monkeypatch):
    evaluator = _FakeEvaluator()
    planner = SimpleNamespace(evaluator=evaluator)
    engine = LiveHandActionDecisionEngine(
        planner=planner,
        policy=LiveHandActionPolicy(evaluator=evaluator),
    )
    state = _state()
    play = _plan(PLAY_CARDS, "play", immediate_score=30.0, fallback_value=10.0)
    discard = _plan(DISCARD_CARDS, "discard", fallback_value=20.0)

    monkeypatch.setattr(
        hand_action_policy,
        "adaptive_blind_search_schedule",
        lambda **kwargs: (),
    )

    def recursive_fallback_must_not_run(*args, **kwargs):
        raise AssertionError("recursive D1 fallback should not run after adaptive search")

    monkeypatch.setattr(engine, "rank_plans", recursive_fallback_must_not_run)
    monkeypatch.setattr(engine, "_rank_immediate_plans", lambda current: [play, discard])

    decision = engine.decide(state)

    assert decision.action.name == DISCARD_CARDS
    assert decision.action.cards == ["discard"]


def test_live_schedule_uses_single_shallow_advisory_pass_under_safe_pace_policy():
    state = _state()
    full = PathAwareLiveHandActionDecisionEngine(max_horizon=5)
    sparse = PathAwareLiveHandActionDecisionEngine(
        max_horizon=5,
        search_schedule_mode="probe-deepest",
    )

    assert [config.horizon for config in full._search_schedule(state)] == [2]
    assert [config.horizon for config in sparse._search_schedule(state)] == [2]
    assert full._search_schedule(state)[0].max_nodes <= 750
    assert sparse._search_schedule(state)[0].max_nodes <= 750


def test_red_white_playbook_retains_calibrated_ceiling_even_when_live_policy_is_shallower():
    playbook = default_balatro_playbooks().get("RED", "WHITE")

    assert playbook.version == "1.0"
    assert playbook.strategy["planner"]["max_horizon"] == 5
    assert playbook.strategy["planner"]["max_search_nodes"] == 2500
    assert playbook.strategy["planner"]["max_search_seconds"] == 8.0
    assert playbook.strategy["planner"]["search_schedule_mode"] == "probe-deepest"


class _StructuralPlanner:
    def __init__(self):
        self.evaluator = LiveHandDecisionEvaluator()
        self.action_generator = CardSelector()

    @staticmethod
    def _require_state(state):
        del state


def _structural_state(*, hands=3):
    cards = [
        BalatroCard("Q", "Spades"),
        BalatroCard("Q", "Hearts"),
        BalatroCard("K", "Clubs"),
        BalatroCard("9", "Diamonds"),
        BalatroCard("5", "Spades"),
        BalatroCard("3", "Hearts"),
        BalatroCard("2", "Clubs"),
    ]
    return SimpleNamespace(
        phase="SELECTING_HAND",
        hand=cards,
        score=0,
        blind=SimpleNamespace(requirement=1000),
        hands_remaining=hands,
        discards_remaining=5,
    )


def test_timeout_fallback_discards_around_top_pair_instead_of_burning_hand():
    planner = _StructuralPlanner()
    engine = PathAwareLiveHandActionDecisionEngine(
        planner=planner,
        policy=LiveHandActionPolicy(evaluator=planner.evaluator),
    )
    state = _structural_state()

    decision = engine._structural_timeout_fallback(state, search_attempts=())

    assert decision.action.name == DISCARD_CARDS
    assert state.hand[0] not in decision.action.cards
    assert state.hand[1] not in decision.action.cards


def test_timeout_fallback_plays_made_pair_on_last_hand():
    planner = _StructuralPlanner()
    engine = PathAwareLiveHandActionDecisionEngine(
        planner=planner,
        policy=LiveHandActionPolicy(evaluator=planner.evaluator),
    )

    decision = engine._structural_timeout_fallback(
        _structural_state(hands=1),
        search_attempts=(),
    )

    assert decision.action.name == PLAY_CARDS
