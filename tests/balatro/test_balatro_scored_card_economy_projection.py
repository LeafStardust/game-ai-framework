from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.bootstraps import BootstrapsJoker
from games.balatro.jokers.bull import BullJoker
from games.balatro.jokers.golden_ticket import GoldenTicketJoker
from games.balatro.jokers.rough_gem import RoughGemJoker
from games.balatro.jokers.smeared_joker import SmearedJoker
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _state(cards, jokers, *, money=0):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.jokers = list(jokers)
    state.money = money
    return state


def _project(hand, cards, jokers, *, money=0):
    state = _state(cards, jokers, money=money)
    transition = VisibleCardScoreOutcomeModel().project_transition(
        hand,
        state,
        cards,
    )
    return state, transition


def test_rough_gem_earns_only_from_scoring_diamonds():
    diamond = BalatroCard("A", "Diamonds")
    state, transition = _project(
        PokerHand.HIGH_CARD,
        [diamond],
        [RoughGemJoker()],
    )

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.deterministic is True
    assert transition.distribution.minimum == 16
    assert transition.state_after_scoring.money == 1
    assert state.money == 0

    pair = [
        BalatroCard("A", "Spades"),
        BalatroCard("A", "Hearts"),
        BalatroCard("2", "Diamonds"),
    ]
    _, kicker_transition = _project(
        PokerHand.PAIR,
        pair,
        [RoughGemJoker()],
    )

    assert kicker_transition.state_after_scoring.money == 0


def test_rough_gem_respects_smeared_suit_semantics():
    heart = BalatroCard("A", "Hearts")
    _, transition = _project(
        PokerHand.HIGH_CARD,
        [heart],
        [SmearedJoker(), RoughGemJoker()],
    )

    assert transition.joker_projection_complete is True
    assert transition.state_after_scoring.money == 1


def test_rough_gem_retriggers_earn_again():
    diamond = BalatroCard("A", "Diamonds", seal="Red")
    _, transition = _project(
        PokerHand.HIGH_CARD,
        [diamond],
        [RoughGemJoker()],
    )

    assert transition.joker_projection_complete is True
    assert transition.state_after_scoring.money == 2


def test_rough_gem_money_is_visible_to_bull_same_hand():
    diamond = BalatroCard("A", "Diamonds")
    state, transition = _project(
        PokerHand.HIGH_CARD,
        [diamond],
        [RoughGemJoker(), BullJoker()],
    )

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 18
    assert transition.state_after_scoring.money == 1
    assert state.money == 0


def test_golden_ticket_earns_per_scored_gold_trigger():
    gold = BalatroCard("A", "Spades", enhancement="Gold")
    state, transition = _project(
        PokerHand.HIGH_CARD,
        [gold],
        [GoldenTicketJoker()],
    )

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.minimum == 16
    assert transition.state_after_scoring.money == 4
    assert state.money == 0

    red_gold = BalatroCard(
        "A",
        "Spades",
        enhancement="Gold",
        seal="Red",
    )
    _, retrigger_transition = _project(
        PokerHand.HIGH_CARD,
        [red_gold],
        [GoldenTicketJoker()],
    )

    assert retrigger_transition.state_after_scoring.money == 8


def test_golden_ticket_money_is_visible_to_bootstraps_same_hand():
    gold = BalatroCard("A", "Spades", enhancement="Gold")
    state, transition = _project(
        PokerHand.HIGH_CARD,
        [gold],
        [GoldenTicketJoker(), BootstrapsJoker()],
        money=1,
    )

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 48
    assert transition.state_after_scoring.money == 5
    assert state.money == 1
