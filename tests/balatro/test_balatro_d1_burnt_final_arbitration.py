from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.live.adaptive_search import AdaptiveRecommendationSummary
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.path_aware_hand_action_engine import (
    PathAwareLiveHandActionDecisionEngine,
)
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


class _FakeEvaluator:
    def project_play(self, state, action):
        del state, action
        return SimpleNamespace(
            expected_hand_score=10.0,
            clear_probability=0.0,
            outcomes=(),
        )

    def evaluate(self, state, action):
        del state, action
        return 0.0


def _state(cards, *, burnt_strategy_fact: bool):
    return SimpleNamespace(
        hand=list(cards),
        score=0,
        blind=SimpleNamespace(requirement=300),
        hands_remaining=3,
        discards_remaining=2,
        discards_used=0,
        burnt_strategy_fact=burnt_strategy_fact,
        boss_name=None,
        blind_type="SMALL",
    )


def _plan(action_name, card, *, clear_probability=0.0, expected_score=0.0):
    action = BalatroAction(action_name, cards=[card])
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
        exact=True,
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
        clear_probability=float(plan.value.clear_probability),
        expected_score=float(plan.value.expected_score),
        horizon=horizon,
        intensified=False,
    )


def _policy(monkeypatch, burnt_target_card):
    policy = StrategyAwareLiveHandActionPolicy(evaluator=_FakeEvaluator())
    monkeypatch.setattr(policy, "_hand_bond_intents", lambda state: ())
    monkeypatch.setattr(policy, "_preservation", lambda plan: 0.0)
    monkeypatch.setattr(policy, "_vagabond_generation_active", lambda state: False)
    monkeypatch.setattr(
        policy,
        "_green_preserved_decision",
        lambda state, plans, decision: decision,
    )
    monkeypatch.setattr(policy.build_evaluator, "prepare", lambda state: None)
    monkeypatch.setattr(policy.build_evaluator, "reset_cache", lambda: None)
    monkeypatch.setattr(
        policy,
        "_strategy_fit",
        lambda state, action: (
            (2.5, ("Burnt target first-discard development",))
            if state.burnt_strategy_fact
            and action.name == DISCARD_CARDS
            and tuple(action.cards) == (burnt_target_card,)
            else (0.0, ())
        ),
    )
    return policy


def test_burnt_fact_changes_final_d1_discard_and_survives_consensus(monkeypatch):
    play_card = BalatroCard("A", "Spades")
    generic_card = BalatroCard("3", "Clubs")
    burnt_target_card = BalatroCard("8", "Hearts")
    cards = [play_card, generic_card, burnt_target_card]

    play = _plan(PLAY_CARDS, play_card)
    generic = _plan(DISCARD_CARDS, generic_card)
    burnt_target = _plan(DISCARD_CARDS, burnt_target_card)
    plans = [play, generic, burnt_target]

    policy = _policy(monkeypatch, burnt_target_card)
    engine = PathAwareLiveHandActionDecisionEngine(policy=policy)

    with_burnt = _state(cards, burnt_strategy_fact=True)
    with_burnt_decision = policy.decide(
        with_burnt,
        plans,
        setup_discard_consensus=True,
    )
    assert with_burnt_decision.action is burnt_target.action

    engine._adaptive_root_history = [
        (_summary(with_burnt, generic, horizon=horizon), generic)
        for horizon in (5, 6, 7)
    ]
    with_burnt_final = engine._apply_consensus_recovery(
        with_burnt,
        with_burnt_decision,
    )
    assert with_burnt_final.action is burnt_target.action
    assert any(
        "canonical build/Bond ordering retained" in note
        for note in with_burnt_final.rationale
    )

    without_burnt = _state(cards, burnt_strategy_fact=False)
    without_burnt_decision = policy.decide(
        without_burnt,
        plans,
        setup_discard_consensus=True,
    )
    assert without_burnt_decision.action is generic.action

    engine._adaptive_root_history = [
        (_summary(without_burnt, generic, horizon=horizon), generic)
        for horizon in (5, 6, 7)
    ]
    without_burnt_final = engine._apply_consensus_recovery(
        without_burnt,
        without_burnt_decision,
    )
    assert without_burnt_final.action is generic.action


def test_materially_safer_discard_overrides_burnt_development(monkeypatch):
    play_card = BalatroCard("A", "Spades")
    safe_card = BalatroCard("3", "Clubs")
    burnt_target_card = BalatroCard("8", "Hearts")
    state = _state(
        [play_card, safe_card, burnt_target_card],
        burnt_strategy_fact=True,
    )

    play = _plan(PLAY_CARDS, play_card)
    safe = _plan(DISCARD_CARDS, safe_card, clear_probability=0.30, expected_score=90.0)
    burnt_target = _plan(
        DISCARD_CARDS,
        burnt_target_card,
        clear_probability=0.10,
        expected_score=50.0,
    )

    policy = _policy(monkeypatch, burnt_target_card)
    decision = policy.decide(
        state,
        [play, burnt_target, safe],
        setup_discard_consensus=True,
    )

    assert decision.action is safe.action
    assert decision.selected_plan is safe
