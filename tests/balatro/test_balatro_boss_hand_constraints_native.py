from types import SimpleNamespace

import games.balatro  # noqa: F401 - initialize production registration
from games.balatro.actions import BalatroAction, DISCARD_CARDS, PLAY_CARDS
from games.balatro.boss_hand_constraint_policy import install_boss_hand_constraint_policy
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.boss_hand_constraints import (
    constrain_boss_hand_plans,
    mouth_zero_score_play_recovery,
)
from games.balatro.live.hand_action_policy import PACE_RECOVERY
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy
from games.balatro.state import BalatroState


def _card(rank, suit="Spades"):
    return SimpleNamespace(rank=rank, suit=suit, enhancement=None, seal=None)


def _value(*, clear=0.0, progress=0.0, score=0.0, hands=1.0, discards=0.0):
    return LiveBlindPlanValue(
        clear_probability=clear,
        expected_progress=progress,
        expected_score=score,
        expected_hands_remaining=hands,
        expected_discards_remaining=discards,
        expected_consumables=0.0,
    )


def _plan(action, *, clear=0.0, progress=0.0, score=0.0, exact=True):
    return LiveBlindPlan(
        action=action,
        value=_value(clear=clear, progress=progress, score=score),
        horizon=2,
        exact=exact,
        candidate_count=3,
    )


def _boss_state(name):
    state = BalatroState()
    state.boss_name = name
    state.jokers = []
    state.hand = []
    return state


def test_eye_native_constraint_removes_already_used_play_type_but_keeps_discards():
    policy = StrategyAwareLiveHandActionPolicy()
    state = _boss_state("The Eye")
    state.boss_blind_hands = {"PAIR"}
    state.boss_blind_state_observed = True

    pair = _plan(BalatroAction(PLAY_CARDS, cards=[_card("A"), _card("A")]))
    high = _plan(BalatroAction(PLAY_CARDS, cards=[_card("K")]))
    discard = _plan(BalatroAction(DISCARD_CARDS, cards=[_card("2")]))

    constrained = constrain_boss_hand_plans(policy, state, (pair, high, discard))

    assert pair not in constrained
    assert high in constrained
    assert discard in constrained


def test_mouth_native_constraint_keeps_locked_play_type_and_discards_only():
    policy = StrategyAwareLiveHandActionPolicy()
    state = _boss_state("The Mouth")
    state.boss_blind_only_hand = "PAIR"

    pair = _plan(BalatroAction(PLAY_CARDS, cards=[_card("Q"), _card("Q")]))
    high = _plan(BalatroAction(PLAY_CARDS, cards=[_card("K")]))
    discard = _plan(BalatroAction(DISCARD_CARDS, cards=[_card("3")]))

    constrained = constrain_boss_hand_plans(policy, state, (pair, high, discard))

    assert pair in constrained
    assert high not in constrained
    assert discard in constrained


def test_mouth_native_constraint_forces_discard_only_when_no_locked_play_exists():
    policy = StrategyAwareLiveHandActionPolicy()
    state = _boss_state("The Mouth")
    state.boss_blind_only_hand = "PAIR"

    high = _plan(BalatroAction(PLAY_CARDS, cards=[_card("K")]))
    discard = _plan(BalatroAction(DISCARD_CARDS, cards=[_card("3")]))

    constrained = constrain_boss_hand_plans(policy, state, (high, discard))

    assert constrained == (discard,)


def test_mouth_zero_score_recovery_prefers_widest_structure_equivalent_play():
    policy = StrategyAwareLiveHandActionPolicy()
    policy._structure_fit = lambda cards, hand_type, rules=None: 1.0
    state = _boss_state("The Mouth")
    state.boss_blind_only_hand = "PAIR"
    state.discards_remaining = 0
    state.hand = [_card("A"), _card("K"), _card("Q"), _card("J")]

    narrow = _plan(BalatroAction(PLAY_CARDS, cards=[state.hand[0]]))
    wide = _plan(BalatroAction(PLAY_CARDS, cards=state.hand[:3]))

    recovery = mouth_zero_score_play_recovery(
        policy,
        state,
        (narrow, wide),
        "PAIR",
    )

    assert recovery == (wide,)


def test_native_mouth_discard_only_recovery_returns_legal_discard_from_policy_decide():
    policy = StrategyAwareLiveHandActionPolicy()
    policy._hand_bond_intents = lambda state: []
    policy._within_type_key = lambda plan: (0.0,)
    policy._pace_target = lambda state: 100.0
    policy.evaluator = SimpleNamespace(evaluate=lambda state, action: 5.0)
    policy.build_evaluator = SimpleNamespace(
        prepare=lambda state: None,
        reset_cache=lambda: None,
    )

    state = _boss_state("The Mouth")
    state.boss_blind_only_hand = "PAIR"
    state.discards_remaining = 1
    discard = _plan(
        BalatroAction(DISCARD_CARDS, cards=[_card("2")]),
        clear=0.15,
        progress=0.25,
    )

    decision = policy.decide(state, (discard,))

    assert decision.mode == PACE_RECOVERY
    assert decision.action.name == DISCARD_CARDS
    assert decision.selected_plan is discard


def test_production_stack_does_not_install_boss_hand_constraint_overlay():
    before_decide = StrategyAwareLiveHandActionPolicy.decide
    before_fit = StrategyAwareLiveHandActionPolicy._strategy_fit

    install_boss_hand_constraint_policy()

    assert StrategyAwareLiveHandActionPolicy.decide is before_decide
    assert StrategyAwareLiveHandActionPolicy._strategy_fit is before_fit
    assert not hasattr(StrategyAwareLiveHandActionPolicy, "_boss_hand_constraint_installed")
    assert StrategyAwareLiveHandActionPolicy.decide.__module__ == (
        "games.balatro.live.strategy_hand_policy"
    )
    assert StrategyAwareLiveHandActionPolicy._strategy_fit.__module__ == (
        "games.balatro.live.strategy_hand_policy"
    )
