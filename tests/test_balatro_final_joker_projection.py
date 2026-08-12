from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.bootstraps import BootstrapsJoker
from games.balatro.jokers.canio import CanioJoker
from games.balatro.jokers.lucky_cat import LuckyCatJoker
from games.balatro.jokers.seltzer import SeltzerJoker
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _state(cards, *, money=0):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.money = money
    state.score = 0
    state.blind = Blind(BlindType.BIG, 10_000)
    return state


def test_seltzer_retriggers_scoring_cards_and_consumes_one_hand_on_branch_only():
    cards = [
        BalatroCard("10", "Spades"),
        BalatroCard("10", "Diamonds"),
    ]
    state = _state(cards)
    seltzer = SeltzerJoker()
    seltzer.rounds_remaining = 7
    state.jokers = [seltzer]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        cards,
    )

    # Pair base 10 Chips + both 10s twice = 50 Chips; 50 * 2 Mult = 100.
    assert transition.distribution.minimum == 100
    assert transition.distribution.maximum == 100
    assert transition.joker_projection_complete is True
    assert seltzer.rounds_remaining == 7
    assert transition.state_after_scoring.jokers[0].rounds_remaining == 6


def test_seltzer_stacks_with_red_seal_and_adds_independent_lucky_attempts():
    cards = [
        BalatroCard("10", "Spades", enhancement="Lucky", seal="Red"),
        BalatroCard("10", "Diamonds"),
    ]
    state = _state(cards)
    seltzer = SeltzerJoker()
    seltzer.rounds_remaining = 1
    state.jokers = [seltzer]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        cards,
    )

    # Lucky 10 scores three times: base + Red Seal + Seltzer. The other 10 scores
    # twice: base + Seltzer. Pair base 10 + 50 rank Chips = 60 total Chips.
    assert [
        (outcome.score, round(outcome.probability, 10))
        for outcome in transition.distribution.outcomes
    ] == [
        (120, 0.512),
        (1320, 0.384),
        (2520, 0.096),
        (3720, 0.008),
    ]
    assert transition.state_after_scoring.jokers[0].rounds_remaining == 0
    assert seltzer.rounds_remaining == 1


def test_lucky_cat_branches_money_and_mult_success_without_mutating_live_state():
    cards = [
        BalatroCard("10", "Spades", enhancement="Lucky"),
        BalatroCard("10", "Diamonds"),
    ]
    state = _state(cards)
    lucky_cat = LuckyCatJoker()
    state.jokers = [lucky_cat]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        cards,
    )

    branches = sorted(
        (
            outcome.score,
            round(outcome.probability, 10),
            outcome.state_after_scoring.money,
            outcome.state_after_scoring.jokers[0].x_mult,
        )
        for outcome in transition.distribution.outcomes
    )
    assert branches == [
        (60, round(56 / 75, 10), 0, 1.0),
        (75, round(4 / 75, 10), 20, 1.25),
        (825, round(1 / 75, 10), 20, 1.25),
        (825, round(14 / 75, 10), 0, 1.25),
    ]
    assert transition.joker_projection_complete is True
    assert lucky_cat.x_mult == 1.0
    assert state.money == 0


def test_lucky_money_trigger_updates_bootstraps_on_the_same_scoring_branch():
    cards = [
        BalatroCard("10", "Spades", enhancement="Lucky"),
        BalatroCard("10", "Diamonds"),
    ]
    state = _state(cards)
    state.jokers = [BootstrapsJoker(), LuckyCatJoker()]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        cards,
    )

    branches = sorted(
        (
            outcome.score,
            round(outcome.probability, 10),
            outcome.state_after_scoring.money,
        )
        for outcome in transition.distribution.outcomes
    )
    assert branches == [
        (60, round(56 / 75, 10), 0),
        (375, round(4 / 75, 10), 20),
        (825, round(14 / 75, 10), 0),
        (1125, round(1 / 75, 10), 20),
    ]


def test_canio_glass_face_breaks_only_after_current_hand_scores():
    card = BalatroCard("K", "Spades", enhancement="Glass")
    state = _state([card])
    canio = CanioJoker()
    canio.x_mult = 3.0
    state.jokers = [canio]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [card],
    )

    # Current score uses Canio x3 in both branches. The Glass K is 15 Chips total,
    # Glass supplies x2, so 15 * 1 * 2 * 3 = 90 before its post-score break check.
    branches = sorted(
        (
            outcome.score,
            round(outcome.probability, 10),
            outcome.state_after_scoring.jokers[0].x_mult,
        )
        for outcome in transition.distribution.outcomes
    )
    assert branches == [
        (90, 0.25, 4.0),
        (90, 0.75, 3.0),
    ]
    assert transition.joker_projection_complete is True
    assert canio.x_mult == 3.0
