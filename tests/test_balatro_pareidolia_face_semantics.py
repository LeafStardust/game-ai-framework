from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.hand_rules import card_is_face, hand_rules_for_state
from games.balatro.joker import JokerContext
from games.balatro.jokers.pareidolia import PareidoliaJoker
from games.balatro.jokers.photograph import PhotographJoker
from games.balatro.jokers.scary_face import ScaryFaceJoker
from games.balatro.jokers.smiley_face import SmileyFaceJoker
from games.balatro.jokers.sock_and_buskin import SockAndBuskinJoker
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.scoring import HandScore
from games.balatro.state import BalatroState


def _pareidolia_rules():
    state = BalatroState()
    state.jokers = [PareidoliaJoker()]
    return hand_rules_for_state(state)


def test_pareidolia_declares_face_rule_only_for_hand_rules():
    joker = PareidoliaJoker()
    ordinary = JokerContext(data={}, trigger="HAND_SCORED")
    rules = JokerContext(data={}, trigger="HAND_RULES")

    joker.apply(ordinary)
    joker.apply(rules)

    assert "all_cards_are_face" not in ordinary.data
    assert rules.data["all_cards_are_face"] is True
    assert card_is_face(BalatroCard("2", "Clubs"), rules.data)


def test_scary_and_smiley_treat_number_scoring_card_as_face():
    card = BalatroCard("7", "Clubs")
    rules = _pareidolia_rules()
    context = JokerContext(
        score=HandScore(12, 1),
        cards=[card],
        poker_hand=PokerHand.HIGH_CARD,
        data={"scoring_cards": [card], "hand_rules": rules},
    )

    ScaryFaceJoker().apply(context)
    SmileyFaceJoker().apply(context)

    assert context.score.chips == 42
    assert context.score.mult == 6


def test_photograph_targets_first_number_scoring_card_under_pareidolia():
    kicker = BalatroCard("A", "Clubs")
    first_pair = BalatroCard("7", "Hearts")
    second_pair = BalatroCard("7", "Spades")
    rules = _pareidolia_rules()
    context = JokerContext(
        score=HandScore(24, 2),
        cards=[kicker, first_pair, second_pair],
        poker_hand=PokerHand.PAIR,
        trigger="CARD_SCORED",
        data={
            "current_scoring_card": first_pair,
            "scoring_cards": [first_pair],
            "hand_rules": rules,
        },
    )

    PhotographJoker().apply(context)

    assert context.score.x_mult == 2


def test_sock_retriggers_number_scoring_card_under_pareidolia():
    card = BalatroCard("7", "Clubs")
    rules = _pareidolia_rules()
    context = JokerContext(
        cards=[card],
        poker_hand=PokerHand.HIGH_CARD,
        trigger="HAND_PLAYED",
        data={"scoring_cards": [card], "hand_rules": rules},
    )

    SockAndBuskinJoker().apply(context)

    assert context.data["retrigger_by_card_id"][id(card)] == 1


def test_live_projection_remains_fail_closed_until_pareidolia_is_admitted():
    card = BalatroCard("7", "Clubs")
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [card]
    state.deck = []
    state.score = 0
    state.hands_remaining = 1
    state.discards_remaining = 0
    state.blind = Blind(BlindType.BIG, 100)
    state.jokers = [PareidoliaJoker(), ScaryFaceJoker()]

    projection = LiveHandDecisionEvaluator().project_play(
        state,
        BalatroAction(PLAY_CARDS, cards=[card]),
    )

    assert projection.joker_projection_complete is False
    assert "Pareidolia" in projection.unsupported_jokers
