from games.balatro.boss_trigger import matador_boss_hand_triggered
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.joker import JokerContext
from games.balatro.jokers.blueprint import BlueprintJoker
from games.balatro.jokers.bull import BullJoker
from games.balatro.jokers.chicot import ChicotJoker
from games.balatro.jokers.matador import MatadorJoker
from games.balatro.live.final_joker_outcomes import LiveFinalJokerScoreOutcomeModel
from games.balatro.state import BalatroState


def _state(cards, jokers, *, boss_name, money=0):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.owned_deck = list(cards)
    state.jokers = list(jokers)
    state.boss_name = boss_name
    state.money = money
    return state


def _project(state, hand, cards):
    return LiveFinalJokerScoreOutcomeModel().project_transition(
        hand,
        state,
        cards,
    )


def test_matador_no_longer_pays_on_boss_defeat_event():
    state = BalatroState()
    context = JokerContext(
        state=state,
        poker_hand=PokerHand.HIGH_CARD,
        cards=[BalatroCard("A", "Spades")],
        trigger="BOSS_BLIND_DEFEATED",
        data={},
    )

    MatadorJoker().apply(context)

    assert state.money == 0


def test_debuffing_boss_pays_only_when_played_hand_contains_debuffed_card():
    debuffed = BalatroCard("A", "Hearts", debuffed=True)
    normal = BalatroCard("A", "Spades")

    triggered = _state([debuffed], [MatadorJoker()], boss_name="The Head")
    clean = _state([normal], [MatadorJoker()], boss_name="The Head")

    assert _project(triggered, PokerHand.HIGH_CARD, [debuffed]).state_after_scoring.money == 8
    assert _project(clean, PokerHand.HIGH_CARD, [normal]).state_after_scoring.money == 0


def test_flint_always_triggers_matador_for_a_played_hand():
    card = BalatroCard("A", "Spades")
    state = _state([card], [MatadorJoker()], boss_name="The Flint")

    transition = _project(state, PokerHand.HIGH_CARD, [card])

    assert transition.joker_projection_complete is True
    assert transition.state_after_scoring.money == 8
    assert state.money == 0


def test_eye_triggers_only_when_poker_hand_type_was_already_played_this_round():
    card = BalatroCard("A", "Spades")
    repeated = _state([card], [MatadorJoker()], boss_name="The Eye")
    repeated.round_hand_play_counts["HIGH_CARD"] = 1
    fresh = _state([card], [MatadorJoker()], boss_name="The Eye")

    assert matador_boss_hand_triggered(
        repeated, PokerHand.HIGH_CARD, [card]
    ).triggered is True
    assert matador_boss_hand_triggered(
        fresh, PokerHand.HIGH_CARD, [card]
    ).triggered is False


def test_mouth_triggers_when_played_hand_differs_from_first_hand_type():
    card = BalatroCard("A", "Spades")
    state = _state([card], [MatadorJoker()], boss_name="The Mouth")
    state.round_hand_play_counts["PAIR"] = 1

    assert matador_boss_hand_triggered(
        state, PokerHand.HIGH_CARD, [card]
    ).triggered is True
    assert matador_boss_hand_triggered(
        state, PokerHand.PAIR, [card]
    ).triggered is False


def test_psychic_triggers_matador_only_for_fewer_than_five_played_cards():
    four = [BalatroCard(str(rank), "Spades") for rank in ("2", "3", "4", "5")]
    five = [*four, BalatroCard("6", "Spades")]
    state = _state(five, [MatadorJoker()], boss_name="The Psychic")

    assert matador_boss_hand_triggered(
        state, PokerHand.HIGH_CARD, four
    ).triggered is True
    assert matador_boss_hand_triggered(
        state, PokerHand.STRAIGHT, five
    ).triggered is False


def test_arm_triggers_only_when_played_hand_level_can_be_decreased():
    cards = [BalatroCard("K", "Spades"), BalatroCard("K", "Hearts")]
    state = _state(cards, [MatadorJoker()], boss_name="The Arm")
    state.hand_levels["PAIR"] = 2

    assert matador_boss_hand_triggered(
        state, PokerHand.PAIR, cards
    ).triggered is True

    state.hand_levels["PAIR"] = 1
    assert matador_boss_hand_triggered(
        state, PokerHand.PAIR, cards
    ).triggered is False


def test_ox_zeroes_money_before_matador_then_later_bull_uses_the_reward():
    cards = [BalatroCard("2", "Spades"), BalatroCard("2", "Hearts")]
    state = _state(
        cards,
        [MatadorJoker(), BullJoker()],
        boss_name="The Ox",
        money=20,
    )
    state.hand_play_counts["PAIR"] = 3

    transition = _project(state, PokerHand.PAIR, cards)

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 60
    assert transition.state_after_scoring.money == 8
    assert state.money == 20


def test_ox_bull_before_matador_sees_zero_dollars():
    cards = [BalatroCard("2", "Spades"), BalatroCard("2", "Hearts")]
    state = _state(
        cards,
        [BullJoker(), MatadorJoker()],
        boss_name="The Ox",
        money=20,
    )
    state.hand_play_counts["PAIR"] = 3

    transition = _project(state, PokerHand.PAIR, cards)

    assert transition.distribution.minimum == 28
    assert transition.state_after_scoring.money == 8


def test_blueprint_copy_of_matador_pays_independently_in_joker_order():
    cards = [BalatroCard("2", "Spades"), BalatroCard("2", "Hearts")]
    state = _state(
        cards,
        [BlueprintJoker(), MatadorJoker(), BullJoker()],
        boss_name="The Ox",
        money=20,
    )
    state.hand_play_counts["PAIR"] = 3

    transition = _project(state, PokerHand.PAIR, cards)

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 92
    assert transition.state_after_scoring.money == 16


def test_ox_tied_most_played_history_fails_closed_instead_of_guessing_target():
    cards = [BalatroCard("2", "Spades"), BalatroCard("2", "Hearts")]
    state = _state(cards, [MatadorJoker()], boss_name="The Ox", money=20)
    state.hand_play_counts["PAIR"] = 2
    state.hand_play_counts["HIGH_CARD"] = 2

    transition = _project(state, PokerHand.PAIR, cards)

    assert transition.joker_projection_complete is False
    assert transition.unsupported_jokers == ("Matador",)
    assert transition.state_after_scoring.money == 20


def test_non_triggering_tooth_never_pays_matador():
    card = BalatroCard("A", "Spades")
    state = _state([card], [MatadorJoker()], boss_name="The Tooth", money=5)

    transition = _project(state, PokerHand.HIGH_CARD, [card])

    assert transition.state_after_scoring.money == 5


def test_chicot_disables_matador_trigger_with_the_boss_effect():
    card = BalatroCard("A", "Hearts", debuffed=True)
    state = _state(
        [card],
        [MatadorJoker(), ChicotJoker()],
        boss_name="The Head",
        money=5,
    )

    transition = _project(state, PokerHand.HIGH_CARD, [card])

    assert transition.joker_projection_complete is True
    assert transition.state_after_scoring.money == 5
