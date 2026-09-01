from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.strategy_semantics import StrategyCommitment
from games.balatro.joker_policy import _bond_transition_bonus
from games.balatro.jokers.erosion import ErosionJoker
from games.balatro.jokers.trading_card import TradingCardJoker
from games.balatro.jokers.zany_joker import ZanyJoker
from games.balatro.state import BalatroState


def _state(*jokers):
    state = BalatroState()
    state.jokers = list(jokers)
    state.owned_deck = list(state.deck)
    return state


def _planned_candidate(composition):
    plan = composition.strategy_plan
    if plan is None:
        return None
    return next(
        (
            candidate
            for candidate in composition.strategy_candidates
            if candidate.strategy_id == plan.strategy_id
        ),
        None,
    )


def test_erosion_forms_low_authority_deck_thinning_strategy():
    developments, composition = evaluate_bond_composition(_state(ErosionJoker()))
    deck_thinning = next(dev for dev in developments if dev.bond_id == "deck_thinning")

    assert deck_thinning.unlocked
    assert deck_thinning.rank.name == "R1"
    assert composition.strategy_plan is not None
    assert composition.strategy_plan.strategy_id == "semantic:deck_thinning"

    candidate = _planned_candidate(composition)
    assert candidate is not None
    assert candidate.commitment == StrategyCommitment.FORMING
    assert composition.pinned_strategy_id is None


def test_trading_card_is_more_valuable_when_it_deepens_current_thinning_strategy():
    scouting_value, scouting_notes = _bond_transition_bonus(
        _state(),
        TradingCardJoker(),
    )
    aligned_value, aligned_notes = _bond_transition_bonus(
        _state(ErosionJoker()),
        TradingCardJoker(),
    )

    assert 0.0 < scouting_value <= 0.50
    assert aligned_value > scouting_value
    assert aligned_value > 1.0
    assert any("deck_thinning" in note for note in aligned_notes)
    assert any("established rank gain=1.0" in note for note in aligned_notes)
    assert not any("established rank gain=1.0" in note for note in scouting_notes)


def test_unrelated_positive_bond_does_not_receive_equivalent_strategy_value():
    state = _state(ErosionJoker())

    aligned_value, aligned_notes = _bond_transition_bonus(state, TradingCardJoker())
    unrelated_value, unrelated_notes = _bond_transition_bonus(state, ZanyJoker())

    # Zany is genuine positive Three-of-a-Kind Bond development, but it opens an
    # unrelated axis while deck thinning is already FORMING. It must not receive
    # the same transition reward merely because its own Bond reaches R1.
    assert any("three_kind" in note for note in unrelated_notes)
    assert unrelated_value < aligned_value
    assert unrelated_value <= 0.0
    assert any("deck_thinning" in note for note in aligned_notes)
