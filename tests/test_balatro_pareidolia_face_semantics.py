from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.hand_rules import card_is_face, hand_rules_for_state
from games.balatro.joker import JokerContext
from games.balatro.jokers.canio import CanioJoker
from games.balatro.jokers.pareidolia import PareidoliaJoker
from games.balatro.jokers.photograph import PhotographJoker
from games.balatro.jokers.scary_face import ScaryFaceJoker
from games.balatro.jokers.smiley_face import SmileyFaceJoker
from games.balatro.jokers.sock_and_buskin import SockAndBuskinJoker
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.scoring import HandScore
from games.balatro.state import BalatroState


def _pareidolia_rules():
    state = BalatroState()
    state.jokers = [PareidoliaJoker()]
    return hand_rules_for_state(state)


def _live_state(card, jokers):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [card]
    state.deck = []
    state.score = 0
    state.hands_remaining = 1
    state.discards_remaining = 0
    state.blind = Blind(BlindType.BIG, 100)
    state.jokers = list(jokers)
    return state


def test_pareidolia_declares_face_rule_only_for_hand_rules():
    joker = PareidoliaJoker()
    state = BalatroState()
    ordinary = JokerContext(state=state, data={}, trigger="HAND_SCORED")
    rules = JokerContext(state=state, data={}, trigger="HAND_RULES")

    joker.apply(ordinary)
    joker.apply(rules)

    assert "all_cards_are_face" not in ordinary.data
    assert rules.data["all_cards_are_face"] is True
    assert card_is_face(BalatroCard("2", "Clubs"), rules.data)


def test_scary_and_smiley_treat_number_scoring_card_as_face():
    card = BalatroCard("7", "Clubs")
    rules = _pareidolia_rules()
    context = JokerContext(
        state=BalatroState(),
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
        state=BalatroState(),
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
        state=BalatroState(),
        cards=[card],
        poker_hand=PokerHand.HIGH_CARD,
        trigger="HAND_PLAYED",
        data={"scoring_cards": [card], "hand_rules": rules},
    )

    SockAndBuskinJoker().apply(context)

    assert context.data["retrigger_by_card_id"][id(card)] == 1


def test_canio_direct_transition_treats_destroyed_number_card_as_face():
    card = BalatroCard("7", "Clubs")
    canio = CanioJoker()
    context = JokerContext(
        state=BalatroState(),
        score=HandScore(10, 2),
        data={
            "destroyed_cards": [card],
            "hand_rules": _pareidolia_rules(),
        },
    )

    canio.apply(context)

    assert canio.x_mult == 2.0
    assert context.score.x_mult == 2.0


def test_live_projection_admits_pareidolia_face_scoring():
    card = BalatroCard("7", "Clubs")
    state = _live_state(card, [PareidoliaJoker(), ScaryFaceJoker()])

    projection = LiveHandDecisionEvaluator().project_play(
        state,
        BalatroAction(PLAY_CARDS, cards=[card]),
    )

    assert projection.hand == PokerHand.HIGH_CARD
    assert projection.hand_score == 42
    assert projection.joker_projection_complete is True
    assert projection.unsupported_jokers == ()


def test_pareidolia_number_glass_break_can_grow_canio():
    card = BalatroCard("7", "Clubs", enhancement="Glass")
    state = _live_state(card, [PareidoliaJoker(), CanioJoker()])

    distribution = VisibleCardScoreOutcomeModel().project(
        PokerHand.HIGH_CARD,
        state,
        [card],
    )

    assert distribution.random_sources == ("Glass break x1",)
    assert [(outcome.score, outcome.probability) for outcome in distribution.outcomes] == [
        (24, 0.75),
        (24, 0.25),
    ]
    assert [
        next(
            joker
            for joker in outcome.state_after_scoring.jokers
            if isinstance(joker, CanioJoker)
        ).x_mult
        for outcome in distribution.outcomes
    ] == [1.0, 2.0]


def test_pareidolia_does_not_bypass_debuff_for_number_glass_card():
    card = BalatroCard("7", "Clubs", enhancement="Glass", debuffed=True)
    state = _live_state(
        card,
        [PareidoliaJoker(), ScaryFaceJoker(), CanioJoker()],
    )

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [card],
    )

    assert transition.joker_projection_complete is True
    assert transition.distribution.random_sources == ()
    assert transition.distribution.deterministic is True
    assert transition.distribution.minimum == 5
