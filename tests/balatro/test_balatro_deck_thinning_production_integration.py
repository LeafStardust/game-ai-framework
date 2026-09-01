from games.balatro.joker_policy import (
    BUY,
    HOLD,
    JokerAcquisitionPolicy,
    JokerAcquisitionThresholds,
)
from games.balatro.jokers.erosion import ErosionJoker
from games.balatro.jokers.trading_card import TradingCardJoker
from games.balatro.state import BalatroState


def _state(*jokers):
    state = BalatroState()
    state.phase = "SHOP"
    state.ante = 3
    state.money = 20
    state.joker_slots = 5
    state.jokers = list(jokers)
    state.owned_deck = list(state.deck)
    return state


def _thresholds(*, minimum_purchase_advantage: float) -> JokerAcquisitionThresholds:
    return JokerAcquisitionThresholds(
        minimum_purchase_advantage=minimum_purchase_advantage,
        minimum_replacement_advantage=0.0,
        price_weight=0.0,
        interest_weight=0.0,
        reserve_weight=0.0,
        last_joker_slot_penalty=0.0,
        penultimate_joker_slot_penalty=0.0,
    )


def _add_option(policy, state, candidate):
    transition = policy.transition_planner.plan(state, candidate)
    return policy._score_add(
        state,
        candidate,
        transition.candidate_value.total_gain,
        strategic_conflict=(
            getattr(transition.candidate_value, "applicability", None) == "CONFLICT"
        ),
    )


def test_real_erosion_strategy_changes_final_d2_trading_card_acquisition():
    """Pilot B must reach D2's final BUY/HOLD authority, not stop at a helper bonus."""
    ordinary_state = _state()
    thinning_state = _state(ErosionJoker())
    candidate = TradingCardJoker()
    candidate.cost = 0

    # First measure the same canonical D2 option under identical zero-cost
    # economics. The only state difference is the existing Erosion thinning engine.
    probe = JokerAcquisitionPolicy(_thresholds(minimum_purchase_advantage=0.0))
    ordinary_option = _add_option(probe, ordinary_state, candidate)
    thinning_option = _add_option(probe, thinning_state, candidate)

    assert thinning_option.total_advantage > ordinary_option.total_advantage
    assert any("deck_thinning" in note for note in thinning_option.rationale)

    # Put the admission line strictly between those two real production values.
    # This is a controlled counterfactual, not numerical tuning: both decisions use
    # the same policy, candidate, price, cash, slots and threshold. Erosion's public
    # strategy evidence must be the fact that flips final HOLD -> BUY.
    midpoint = (
        ordinary_option.total_advantage + thinning_option.total_advantage
    ) / 2.0
    policy = JokerAcquisitionPolicy(
        _thresholds(minimum_purchase_advantage=midpoint)
    )

    ordinary_decision = policy.decide(ordinary_state, candidate)
    thinning_decision = policy.decide(thinning_state, candidate)

    assert ordinary_decision.action == HOLD
    assert thinning_decision.action == BUY
    assert thinning_decision.selected is not None
    assert thinning_decision.selected.total_advantage > midpoint
    assert any(
        "deck_thinning" in note
        for note in thinning_decision.selected.rationale
    )
