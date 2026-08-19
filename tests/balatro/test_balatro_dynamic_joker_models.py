from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.castle import CastleJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.supernova import SupernovaJoker
from games.balatro.jokers.the_idol import TheIdolJoker
from games.balatro.events import BalatroEvent, BalatroEventType
from games.balatro.joker import JokerContext
from games.balatro.scoring import BalatroScorer, HandScore
from games.balatro.state import BalatroState


def test_base_joker_defaults_to_plus_four_mult():
    state = BalatroState()
    state.jokers = [FlatMultJoker()]

    score = BalatroScorer().score(PokerHand.HIGH_CARD, state=state)

    assert score.mult == 5


def test_supernova_uses_public_count_for_current_scored_hand():
    state = BalatroState()
    state.hand_play_counts["PAIR"] = 3
    state.hand_play_counts["FLUSH"] = 8
    state.jokers = [SupernovaJoker()]

    score = BalatroScorer().score(PokerHand.PAIR, state=state)

    # Base Pair Mult 2 + the prospective fourth Pair play.
    assert score.mult == 6


def test_castle_accumulates_only_its_current_public_suit():
    joker = CastleJoker("Hearts")
    state = BalatroState()
    discarded = [
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Spades"),
        BalatroCard("2", "Hearts"),
    ]
    joker.apply(
        JokerContext(
            state=state,
            event=BalatroEvent(BalatroEventType.CARDS_DISCARDED, discarded),
        )
    )

    scored = joker.apply(
        JokerContext(
            state=state,
            score=HandScore(100, 10, 1.0),
            poker_hand=PokerHand.HIGH_CARD,
        )
    )

    assert joker.chips == 6
    assert scored.score.chips == 106


def test_the_idol_scores_only_its_current_public_rank_and_suit():
    joker = TheIdolJoker("A", "Hearts")
    state = BalatroState()
    context = JokerContext(
        state=state,
        score=HandScore(100, 10, 1.0),
        poker_hand=PokerHand.PAIR,
        cards=[
            BalatroCard("A", "Hearts"),
            BalatroCard("A", "Spades"),
            BalatroCard("A", "Hearts"),
        ],
    )

    result = joker.apply(context)

    assert result.score.x_mult == 4.0


def test_state_copy_preserves_public_hand_play_counts():
    state = BalatroState()
    state.hand_play_counts["STRAIGHT"] = 5

    copied = state.copy()

    assert copied.hand_play_counts["STRAIGHT"] == 5
    assert copied.hand_play_counts is not state.hand_play_counts
