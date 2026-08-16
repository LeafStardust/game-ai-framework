from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.blueprint import BlueprintJoker
from games.balatro.jokers.bull import BullJoker
from games.balatro.jokers.to_do_list import ToDoListJoker
from games.balatro.live.final_joker_outcomes import LiveFinalJokerScoreOutcomeModel
from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.state import BalatroState


def _state(cards, jokers, *, money=0):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.owned_deck = list(cards)
    state.jokers = list(jokers)
    state.money = money
    return state


def _project(state, hand, cards):
    return LiveFinalJokerScoreOutcomeModel().project_transition(
        hand,
        state,
        cards,
    )


def test_to_do_list_hydrates_observed_target_hand():
    joker = LiveJokerFactory().create(
        {
            "center": "j_todo_list",
            "label": "To Do List",
            "public_state": {"target_hand": "Pair"},
        }
    )

    assert isinstance(joker, ToDoListJoker)
    assert joker.target_hand == PokerHand.PAIR


def test_to_do_list_hydrates_secret_target_hand():
    joker = LiveJokerFactory().create(
        {
            "center": "j_todo_list",
            "label": "To Do List",
            "public_state": {"target_hand": "Flush Five"},
        }
    )

    assert isinstance(joker, ToDoListJoker)
    assert joker.target_hand == PokerHand.FLUSH_FIVE


def test_matching_to_do_list_pays_four_without_rerolling_or_mutating_parent():
    ace = BalatroCard("A", "Spades")
    joker = ToDoListJoker(PokerHand.HIGH_CARD)
    state = _state([ace], [joker], money=1)

    transition = _project(state, PokerHand.HIGH_CARD, [ace])

    assert transition.joker_projection_complete is True
    assert transition.distribution.deterministic is True
    branch = transition.distribution.outcomes[0].state_after_scoring
    assert branch.money == 5
    assert branch.jokers[0].target_hand == PokerHand.HIGH_CARD
    assert state.money == 1
    assert joker.target_hand == PokerHand.HIGH_CARD


def test_nonmatching_to_do_list_does_not_pay():
    ace = BalatroCard("A", "Spades")
    state = _state([ace], [ToDoListJoker(PokerHand.PAIR)], money=2)

    transition = _project(state, PokerHand.HIGH_CARD, [ace])

    assert transition.distribution.outcomes[0].state_after_scoring.money == 2


def test_to_do_list_money_is_visible_to_later_bull_in_joker_order():
    ace = BalatroCard("A", "Spades")
    before_bull = _state(
        [ace],
        [ToDoListJoker(PokerHand.HIGH_CARD), BullJoker()],
        money=1,
    )
    after_bull = _state(
        [ace],
        [BullJoker(), ToDoListJoker(PokerHand.HIGH_CARD)],
        money=1,
    )

    before = _project(before_bull, PokerHand.HIGH_CARD, [ace])
    after = _project(after_bull, PokerHand.HIGH_CARD, [ace])

    # Base High Card plus Ace is 16 chips. To Do List before Bull makes Bull see
    # $5 (+10 chips); Bull before To Do List sees only $1 (+2 chips).
    assert before.distribution.minimum == 26
    assert after.distribution.minimum == 18
    assert before.distribution.outcomes[0].state_after_scoring.money == 5
    assert after.distribution.outcomes[0].state_after_scoring.money == 5


def test_blueprint_copies_to_do_list_reward():
    ace = BalatroCard("A", "Spades")
    state = _state(
        [ace],
        [BlueprintJoker(), ToDoListJoker(PokerHand.HIGH_CARD)],
        money=0,
    )

    transition = _project(state, PokerHand.HIGH_CARD, [ace])

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 16
    assert transition.distribution.outcomes[0].state_after_scoring.money == 8


def test_to_do_list_can_pay_on_secret_hand_target():
    cards = [
        BalatroCard("K", suit)
        for suit in ("Hearts", "Diamonds", "Clubs", "Spades", "Hearts")
    ]
    state = _state(
        cards,
        [ToDoListJoker(PokerHand.FIVE_OF_A_KIND)],
        money=0,
    )

    transition = _project(state, PokerHand.FIVE_OF_A_KIND, cards)

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == (120 + 50) * 12
    assert transition.distribution.outcomes[0].state_after_scoring.money == 4


def test_missing_to_do_list_target_fails_closed():
    ace = BalatroCard("A", "Spades")
    state = _state([ace], [ToDoListJoker()], money=0)

    transition = _project(state, PokerHand.HIGH_CARD, [ace])

    assert transition.joker_projection_complete is False
    assert transition.unsupported_jokers == ("ToDoList",)
    assert transition.distribution.outcomes[0].state_after_scoring.money == 0
