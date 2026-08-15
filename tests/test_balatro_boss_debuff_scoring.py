from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.ancient_joker import AncientJoker
from games.balatro.jokers.wee_joker import WeeJoker
from games.balatro.live.head_blind_planner import HeadScorer
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _state(cards):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.blind = Blind(BlindType.BOSS, 1000)
    return state


def test_head_scorer_preserves_authoritative_live_debuff_flags():
    cards = [
        BalatroCard("K", "Spades", debuffed=True),
        BalatroCard("Q", "Clubs"),
    ]

    score = HeadScorer().score(
        PokerHand.HIGH_CARD,
        _state(cards),
        cards=cards,
        include_card_chips=True,
        resolve_random_effects=False,
    )

    # The debuffed King still defines High Card structurally, but contributes no
    # rank chips even though Spades is not The Head's suit-specific Hearts debuff.
    assert score.chips == 5
    assert score.mult == 1
    assert score.total == 5


def test_ancient_joker_ignores_debuffed_scoring_cards():
    cards = [
        BalatroCard("2", "Hearts", debuffed=True),
        BalatroCard("2", "Clubs"),
    ]
    state = _state(cards)
    ancient = AncientJoker()
    ancient.suit = "Hearts"
    state.jokers = [ancient]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        cards,
    )

    # Pair base 10 chips + only the non-debuffed 2 of Clubs = 12 chips at x2 Mult.
    # The debuffed Heart must not trigger Ancient Joker's x1.5 effect.
    assert transition.distribution.minimum == 24
    assert transition.distribution.maximum == 24
    assert transition.joker_projection_complete is True


def test_wee_joker_ignores_debuffed_scoring_twos():
    cards = [
        BalatroCard("2", "Hearts", debuffed=True),
        BalatroCard("2", "Clubs"),
    ]
    state = _state(cards)
    wee = WeeJoker()
    state.jokers = [wee]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        cards,
    )

    # Only the live, non-debuffed 2 scores: 10 base + 2 rank + 8 Wee = 20 chips,
    # multiplied by Pair's base x2 Mult. The authoritative Joker remains untouched.
    assert transition.distribution.minimum == 40
    assert transition.distribution.maximum == 40
    assert transition.joker_projection_complete is True
    assert wee.chips == 0
    assert transition.state_after_scoring.jokers[0].chips == 8
