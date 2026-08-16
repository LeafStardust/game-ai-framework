import pytest

from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.astronomer import AstronomerJoker
from games.balatro.jokers.burglar import BurglarJoker
from games.balatro.jokers.cartomancer import CartomancerJoker
from games.balatro.jokers.certificate import CertificateJoker
from games.balatro.jokers.chaos_the_clown import ChaosTheClownJoker
from games.balatro.jokers.cloud_9 import Cloud9Joker
from games.balatro.jokers.credit_card import CreditCardJoker
from games.balatro.jokers.delayed_gratification import DelayedGratificationJoker
from games.balatro.jokers.diet_cola import DietColaJoker
from games.balatro.jokers.drunkard import DrunkardJoker
from games.balatro.jokers.gift_card import GiftCardJoker
from games.balatro.jokers.golden_joker import GoldenJoker
from games.balatro.jokers.hallucination import HallucinationJoker
from games.balatro.jokers.juggler import JugglerJoker
from games.balatro.jokers.marble_joker import MarbleJoker
from games.balatro.jokers.riff_raff import RiffRaffJoker
from games.balatro.jokers.rocket import RocketJoker
from games.balatro.jokers.satellite import SatelliteJoker
from games.balatro.jokers.showman import ShowmanJoker
from games.balatro.jokers.to_the_moon import ToTheMoonJoker
from games.balatro.jokers.troubadour import TroubadourJoker
from games.balatro.live.post_hand_outcomes import LiveVisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


BLIND_NEUTRAL_JOKERS = (
    AstronomerJoker,
    BurglarJoker,
    CartomancerJoker,
    CertificateJoker,
    ChaosTheClownJoker,
    Cloud9Joker,
    CreditCardJoker,
    DelayedGratificationJoker,
    DietColaJoker,
    DrunkardJoker,
    GiftCardJoker,
    GoldenJoker,
    HallucinationJoker,
    JugglerJoker,
    MarbleJoker,
    RiffRaffJoker,
    RocketJoker,
    SatelliteJoker,
    ShowmanJoker,
    ToTheMoonJoker,
    TroubadourJoker,
)


def _project(jokers):
    ace = BalatroCard("A", "Spades")
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [ace]
    state.deck = []
    state.jokers = list(jokers)
    state.hand_size = 11
    state.hands_remaining = 2
    state.discards_remaining = 4

    return state, LiveVisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )


@pytest.mark.parametrize("joker_class", BLIND_NEUTRAL_JOKERS)
def test_blind_neutral_joker_does_not_block_exact_score_projection(joker_class):
    state, transition = _project([joker_class()])

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.deterministic is True
    assert transition.distribution.minimum == 16
    assert transition.distribution.maximum == 16
    assert transition.state_after_scoring.hand_size == 11
    assert transition.state_after_scoring.hands_remaining == 2
    assert transition.state_after_scoring.discards_remaining == 4
    assert state.hand_size == 11
    assert state.hands_remaining == 2
    assert state.discards_remaining == 4


def test_burglar_preserves_live_post_blind_resource_state():
    ace = BalatroCard("A", "Spades")
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [ace]
    state.deck = []
    state.jokers = [BurglarJoker()]
    state.hands_remaining = 6
    state.discards_remaining = 0

    transition = LiveVisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.minimum == 16
    assert transition.distribution.maximum == 16
    assert transition.state_after_scoring.hands_remaining == 6
    assert transition.state_after_scoring.discards_remaining == 0
    assert state.hands_remaining == 6
    assert state.discards_remaining == 0


def test_blind_neutral_jokers_remain_neutral_when_combined():
    _, transition = _project([joker_class() for joker_class in BLIND_NEUTRAL_JOKERS])

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.deterministic is True
    assert transition.distribution.minimum == 16
    assert transition.distribution.maximum == 16
