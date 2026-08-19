import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.matador import MatadorJoker
from games.balatro.live.boss_blind_integration import boss_blind_planning_rule
from games.balatro.live.draw_model import PublicCardSignature, PublicDeckComposition
from games.balatro.live.draw_outcomes import PublicDrawOutcomeModel
from games.balatro.live.final_joker_outcomes import LiveFinalJokerScoreOutcomeModel
from games.balatro.state import BalatroState


CARD_DEBUFF_BOSSES = (
    "The Club",
    "The Goad",
    "The Window",
    "The Plant",
    "The Pillar",
)


def _boss_state(name: str, cards):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.blind = Blind(BlindType.BOSS, 10_000)
    state.boss_name = name
    state.hand = list(cards)
    state.deck = []
    state.owned_deck = list(cards)
    state.hands_remaining = 4
    state.discards_remaining = 3
    state.discards_used = 0
    state.hand_size = len(cards)
    return state


def test_public_card_signature_preserves_debuff_and_permanent_bonus():
    card = BalatroCard(
        "A",
        "Clubs",
        enhancement="Bonus",
        edition="Foil",
        seal="Red",
        debuffed=True,
        permanent_bonus=15,
    )

    signature = PublicCardSignature.from_card(card)

    assert signature.rank == "A"
    assert signature.suit == "Clubs"
    assert signature.debuffed is True
    assert signature.permanent_bonus == 15

    rebuilt = PublicDrawOutcomeModel.card_from_signature(signature)
    assert rebuilt.debuffed is True
    assert rebuilt.permanent_bonus == 15
    assert rebuilt.enhancement == "Bonus"
    assert rebuilt.edition == "Foil"
    assert rebuilt.seal == "Red"


def test_debuff_status_is_part_of_unordered_public_deck_composition():
    clean = BalatroCard("K", "Clubs", debuffed=False)
    debuffed = BalatroCard("K", "Clubs", debuffed=True)

    composition = PublicDeckComposition.from_cards([clean, debuffed])

    assert composition.total_cards == 2
    assert composition.unique_signatures == 2
    outcomes = PublicDrawOutcomeModel().distribution(composition, 1).outcomes
    assert len(outcomes) == 2
    assert {outcome.cards[0].debuffed for outcome in outcomes} == {False, True}
    assert all(outcome.probability == pytest.approx(0.5) for outcome in outcomes)


def test_remaining_public_deck_cards_keep_debuff_and_hiker_bonus():
    debuffed = BalatroCard("Q", "Diamonds", debuffed=True, permanent_bonus=10)
    clean = BalatroCard("2", "Spades", debuffed=False, permanent_bonus=5)
    model = PublicDrawOutcomeModel()
    composition = PublicDeckComposition.from_cards([debuffed, clean])
    distribution = model.distribution(composition, 1)

    debuffed_draw = next(
        outcome for outcome in distribution.outcomes if outcome.cards[0].debuffed
    )
    remaining = model.remaining_cards(composition, debuffed_draw)

    assert len(remaining) == 1
    assert remaining[0].rank == "2"
    assert remaining[0].debuffed is False
    assert remaining[0].permanent_bonus == 5


@pytest.mark.parametrize("boss_name", CARD_DEBUFF_BOSSES)
def test_card_debuff_bosses_are_explicit_authoritative_pass_through_rules(boss_name):
    state = _boss_state(boss_name, [BalatroCard("A", "Spades")])

    rule = boss_blind_planning_rule(state)

    assert rule is not None
    assert rule.boss_name == boss_name
    assert rule.required_play_cards is None
    assert rule.evaluator_factory is None


@pytest.mark.parametrize("boss_name", CARD_DEBUFF_BOSSES)
def test_debuffed_playing_card_skips_card_score_and_triggers_matador(boss_name):
    card = BalatroCard("A", "Spades", debuffed=True)
    state = _boss_state(boss_name, [card])
    state.money = 0
    state.jokers = [MatadorJoker()]

    transition = LiveFinalJokerScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [card],
    )
    branch = transition.distribution.outcomes[0].state_after_scoring

    # A debuffed Ace still forms High Card but contributes no 11 card chips.
    assert transition.distribution.minimum == 5
    assert transition.distribution.maximum == 5
    assert branch.money == 8
    assert state.money == 0


def test_hypothetical_debuffed_draw_remains_debuffed_when_scored_next_hand():
    signature = PublicCardSignature(
        rank="A",
        suit="Clubs",
        debuffed=True,
        permanent_bonus=25,
    )
    drawn = PublicDrawOutcomeModel.card_from_signature(signature)
    state = _boss_state("The Club", [drawn])

    transition = LiveFinalJokerScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [drawn],
    )

    # Neither the Ace's 11 chips nor its permanent +25 survive the boss debuff.
    assert transition.distribution.minimum == 5
    assert transition.distribution.maximum == 5
