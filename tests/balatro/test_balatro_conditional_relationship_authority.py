from games.balatro.state import BalatroState
from games.balatro.strategy import GOLD, NEUTRAL, SILVER
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES
from games.balatro.strategy_conditional_relationships import (
    StateAwareBalatroStrategyTracker,
    conditional_joker_relationship,
)


class DNAJoker:
    pass


class ScholarJoker:
    pass


class HangingChadJoker:
    pass


class PhotographJoker:
    pass


class SmearedJoker:
    pass


def _state(*jokers):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.jokers = list(jokers)
    return state


def _tracker(strategy_id):
    definition = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES[strategy_id]
    return StateAwareBalatroStrategyTracker({strategy_id: definition})


def test_aces_dna_does_not_leak_silver_without_ace_commitment():
    state = _state(DNAJoker())
    tracker = _tracker("aces")

    assert conditional_joker_relationship(state, "aces", state.jokers[0]) == NEUTRAL
    assessment = tracker.assess(state)[0]
    assert assessment.silver_owned == 0


def test_aces_scholar_dna_pair_promotes_scholar_and_keeps_dna_support():
    state = _state(ScholarJoker(), DNAJoker())
    tracker = _tracker("aces")
    assessment = tracker.assess(state)[0]

    assert conditional_joker_relationship(state, "aces", state.jokers[0]) == GOLD
    assert conditional_joker_relationship(state, "aces", state.jokers[1]) == SILVER
    assert assessment.gold_owned == 1
    assert assessment.silver_owned == 1


def test_photochad_hanging_chad_requires_photograph_and_then_becomes_gold():
    chad = HangingChadJoker()
    without_photo = _state(chad)
    with_photo = _state(PhotographJoker(), chad)

    assert conditional_joker_relationship(without_photo, "face_photochad", chad) == NEUTRAL
    assert _tracker("face_photochad").assess(without_photo)[0].silver_owned == 0

    assert conditional_joker_relationship(with_photo, "face_photochad", chad) == GOLD
    assessment = _tracker("face_photochad").assess(with_photo)[0]
    assert assessment.gold_owned == 1


def test_smeared_does_not_create_hearts_route_without_heart_payoff():
    state = _state(SmearedJoker())
    assessment = _tracker("hearts").assess(state)[0]

    assert conditional_joker_relationship(state, "hearts", state.jokers[0]) == NEUTRAL
    assert assessment.silver_owned == 0
