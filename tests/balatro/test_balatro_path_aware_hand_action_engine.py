from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.live.adaptive_search import AdaptiveRecommendationSummary
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.hand_action_policy import (
    PACE_PLAY,
    PACE_RECOVERY,
    LiveHandActionPolicy,
)
from games.balatro.live.path_aware_hand_action_engine import (
    PathAwareLiveHandActionDecisionEngine,
)
from games.balatro.live.runtime import bond_autonomous_runner


class _FakeEvaluator:
    def project_play(self, state, action):
        del state
        return SimpleNamespace(
            expected_hand_score=float(action.target["immediate_score"])
        )

    def evaluate(self, state, action):
        del state
        return float(action.target.get("fallback_value", 0.0))


def _state(cards):
    return SimpleNamespace(
        hand=list(cards),
        score=0,
        blind=SimpleNamespace(requirement=300),
        hands_remaining=3,
        discards_remaining=2,
    )


def _plan(
    action_name,
    card,
    *,
    immediate_score=0.0,
    fallback_value=0.0,
    expected_score=0.0,
    clear_probability=0.0,
    exact=True,
):
    action = BalatroAction(
        action_name,
        cards=[card],
        target={
            "immediate_score": immediate_score,
            "fallback_value": fallback_value,
        },
    )
    return LiveBlindPlan(
        action=action,
        value=LiveBlindPlanValue(
            clear_probability=clear_probability,
            expected_progress=0.0,
            expected_score=expected_score,
            expected_hands_remaining=2.0,
            expected_discards_remaining=1.0,
        ),
        horizon=1,
        exact=exact,
        candidate_count=3,
    )


def _summary(state, plan, *, horizon):
    selected_ids = {id(card) for card in plan.action.cards}
    indices = tuple(
        index
        for index, card in enumerate(state.hand)
        if id(card) in selected_ids
    )
    return AdaptiveRecommendationSummary(
        action=plan.action.name,
        indices=indices,
        clear_probability=0.20 + horizon * 0.01,
        expected_score=1000.0 + horizon,
        horizon=horizon,
        intensified=False,
    )


def _engine(policy):
    return PathAwareLiveHandActionDecisionEngine(policy=policy)


def test_production_runner_uses_path_aware_d1_engine():
    assert (
        bond_autonomous_runner.LiveHandActionDecisionEngine
        is PathAwareLiveHandActionDecisionEngine
    )


def test_stable_path_discard_overrides_different_one_step_recovery_discard():
    play_card = BalatroCard("A", "Spades")
    path_card = BalatroCard("2", "Hearts")
    heuristic_card = BalatroCard("3", "Clubs")
    state = _state([play_card, path_card, heuristic_card])

    play = _plan(
        PLAY_CARDS,
        play_card,
        immediate_score=50.0,
        fallback_value=20.0,
    )
    path_discard = _plan(
        DISCARD_CARDS,
        path_card,
        fallback_value=10.0,
    )
    heuristic_discard = _plan(
        DISCARD_CARDS,
        heuristic_card,
        fallback_value=100.0,
    )

    policy = LiveHandActionPolicy(evaluator=_FakeEvaluator())
    base_decision = policy.decide(
        state,
        [play, heuristic_discard],
        setup_discard_consensus=True,
    )
    assert base_decision.mode == PACE_RECOVERY
    assert base_decision.action is heuristic_discard.action

    engine = _engine(policy)
    engine._adaptive_root_history = [
        (_summary(state, path_discard, horizon=horizon), path_discard)
        for horizon in (5, 6, 7)
    ]

    decision = engine._apply_consensus_recovery(state, base_decision)

    assert decision.mode == PACE_RECOVERY
    assert decision.action is path_discard.action
    assert decision.selected_plan is path_discard
    assert decision.setup_discard_consensus is True
    assert any("preserve the modeled recovery path" in note for note in decision.rationale)


def test_path_discard_consensus_never_overrides_a_play_that_meets_pace():
    play_card = BalatroCard("A", "Spades")
    path_card = BalatroCard("2", "Hearts")
    state = _state([play_card, path_card])

    pace_play = _plan(
        PLAY_CARDS,
        play_card,
        immediate_score=110.0,
        fallback_value=20.0,
    )
    path_discard = _plan(
        DISCARD_CARDS,
        path_card,
        fallback_value=100.0,
    )

    policy = LiveHandActionPolicy(evaluator=_FakeEvaluator())
    base_decision = policy.decide(
        state,
        [pace_play, path_discard],
        setup_discard_consensus=True,
    )
    assert base_decision.mode == PACE_PLAY

    engine = _engine(policy)
    engine._adaptive_root_history = [
        (_summary(state, path_discard, horizon=horizon), path_discard)
        for horizon in (5, 6, 7)
    ]

    decision = engine._apply_consensus_recovery(state, base_decision)

    assert decision is base_decision
    assert decision.action is pace_play.action


def test_close_search_estimate_does_not_churn_pace_decision():
    play_card = BalatroCard("A", "Spades")
    other_card = BalatroCard("K", "Hearts")
    state = _state([play_card, other_card])
    fallback_play = _plan(
        PLAY_CARDS,
        play_card,
        expected_score=100.0,
        clear_probability=0.10,
    )
    search_play = _plan(
        PLAY_CARDS,
        other_card,
        expected_score=105.0,
        clear_probability=0.11,
    )
    policy = LiveHandActionPolicy(evaluator=_FakeEvaluator())
    base_decision = policy.decide(state, [fallback_play])
    engine = _engine(policy)
    engine._adaptive_root_history = [(_summary(state, search_play, horizon=2), search_play)]

    assert engine._apply_adaptive_authority(state, base_decision) is base_decision
