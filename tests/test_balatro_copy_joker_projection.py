from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.bloodstone import BloodstoneJoker
from games.balatro.jokers.blueprint import BlueprintJoker
from games.balatro.jokers.brainstorm import BrainstormJoker
from games.balatro.jokers.cavendish import CavendishJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.live.joker_projection import LiveJokerScoreProjector
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _project(jokers, *, card=None):
    card = card or BalatroCard("A", "Spades")
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [card]
    state.deck = []
    state.jokers = list(jokers)
    return VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [card],
    )


def test_blueprint_copies_validated_independent_joker_to_the_right():
    transition = _project([BlueprintJoker(), FlatMultJoker()])

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.deterministic is True
    assert transition.distribution.minimum == 144


def test_brainstorm_copies_validated_leftmost_independent_joker():
    transition = _project([FlatMultJoker(), BrainstormJoker()])

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 144


def test_blueprint_and_brainstorm_resolve_copy_chains():
    transition = _project(
        [FlatMultJoker(), BlueprintJoker(), BrainstormJoker()]
    )

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 208


def test_blueprint_copy_resolves_at_copier_position():
    transition = _project(
        [BlueprintJoker(), CavendishJoker(), FlatMultJoker()]
    )

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 208


def test_copy_uses_copier_edition_without_copying_target_edition():
    blueprint = BlueprintJoker()
    blueprint.edition = "Holographic"
    target = FlatMultJoker()
    target.edition = "Polychrome"

    transition = _project([blueprint, target])

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 456


def test_rightmost_blueprint_with_no_target_is_exactly_neutral():
    transition = _project([BlueprintJoker()])

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.minimum == 16


def test_copy_of_unvalidated_on_scored_target_fails_closed():
    heart = BalatroCard("A", "Hearts")
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [heart]
    state.deck = []
    blueprint = BlueprintJoker()
    bloodstone = BloodstoneJoker()
    state.jokers = [blueprint, bloodstone]

    assert LiveJokerScoreProjector.supports(blueprint) is True
    assert LiveJokerScoreProjector.supports_in_state(blueprint, state) is False

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [heart],
    )

    assert transition.joker_projection_complete is False
    assert "Blueprint" in transition.unsupported_jokers
