import pytest

from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.blueprint import BlueprintJoker
from games.balatro.jokers.cavendish import CavendishJoker
from games.balatro.jokers.misprint import MisprintJoker
from games.balatro.live.post_hand_outcomes import LiveVisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _state(*jokers):
    ace = BalatroCard("A", "Spades")
    state = BalatroState()
    state.hand = [ace]
    state.deck = []
    state.jokers = list(jokers)
    return state, ace


def _project(state, ace):
    return LiveVisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )


def test_single_misprint_projects_all_24_uniform_mult_results():
    state, ace = _state(MisprintJoker())

    transition = _project(state, ace)
    distribution = transition.distribution

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert distribution.minimum == 16
    assert distribution.maximum == 384
    assert distribution.expected == pytest.approx(200.0)
    assert len(distribution.outcomes) == 24
    assert distribution.random_sources == ("Misprint x1",)
    assert [outcome.score for outcome in distribution.outcomes] == [
        16 * mult
        for mult in range(1, 25)
    ]
    assert all(
        outcome.probability == pytest.approx(1.0 / 24.0)
        for outcome in distribution.outcomes
    )


def test_two_misprints_use_independent_rolls_without_24_squared_rescoring():
    state, ace = _state(MisprintJoker(), MisprintJoker())

    distribution = _project(state, ace).distribution

    assert distribution.minimum == 16
    assert distribution.maximum == 752
    assert distribution.expected == pytest.approx(384.0)
    assert len(distribution.outcomes) == 47
    assert distribution.random_sources == ("Misprint x2",)
    by_score = {outcome.score: outcome.probability for outcome in distribution.outcomes}
    assert by_score[16] == pytest.approx(1.0 / 576.0)
    assert by_score[384] == pytest.approx(24.0 / 576.0)
    assert by_score[752] == pytest.approx(1.0 / 576.0)


def test_misprint_preserves_joker_order_around_xmult():
    early_xmult_state, ace = _state(CavendishJoker(), MisprintJoker())
    late_xmult_state, late_ace = _state(MisprintJoker(), CavendishJoker())

    early = _project(early_xmult_state, ace).distribution
    late = _project(late_xmult_state, late_ace).distribution

    assert early.minimum == 48
    assert early.maximum == 416
    assert late.minimum == 48
    assert late.maximum == 1152
    assert late.expected > early.expected


def test_blueprint_copies_misprint_as_an_independent_roll():
    state, ace = _state(BlueprintJoker(), MisprintJoker())

    distribution = _project(state, ace).distribution

    assert distribution.minimum == 16
    assert distribution.maximum == 752
    assert distribution.expected == pytest.approx(384.0)
    assert len(distribution.outcomes) == 47
    assert distribution.random_sources == ("Misprint x2",)


def test_polychrome_misprint_applies_after_its_random_mult():
    misprint = MisprintJoker()
    misprint.edition = "POLYCHROME"
    state, ace = _state(misprint)

    distribution = _project(state, ace).distribution

    assert distribution.minimum == 24
    assert distribution.maximum == 576
    assert distribution.expected == pytest.approx(300.0)


def test_misprint_projection_never_calls_hidden_random_randint(monkeypatch):
    def fail_randint(*_args, **_kwargs):
        raise AssertionError("live projection must not sample Misprint hidden RNG")

    monkeypatch.setattr("games.balatro.jokers.misprint.random.randint", fail_randint)
    state, ace = _state(MisprintJoker())

    distribution = _project(state, ace).distribution

    assert distribution.minimum == 16
    assert distribution.maximum == 384


def test_misprint_projection_does_not_mutate_authoritative_state():
    misprint = MisprintJoker()
    state, ace = _state(misprint)
    original_hand = list(state.hand)
    original_jokers = list(state.jokers)

    transition = _project(state, ace)

    assert state.hand == original_hand
    assert state.jokers == original_jokers
    assert state.jokers[0] is misprint
    assert transition.state_after_scoring is not state
