from types import SimpleNamespace

from games.balatro.actions import BalatroAction, DISCARD_CARDS
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.faceless_joker import FacelessJoker
from games.balatro.jokers.mail_in_rebate import MailInRebateJoker
from games.balatro.jokers.pareidolia import PareidoliaJoker
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live.discard_projection import LiveDiscardJokerProjector
from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.live.post_hand_outcomes import LiveVisibleCardScoreOutcomeModel
from games.balatro.live.runtime.live_memory_observer import (
    _normalize_round_joker_public_state,
)
from games.balatro.live.runtime.luajit_memory import LuaValue
from games.balatro.state import BalatroState


def _state(cards, jokers, *, money=0):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.money = money
    state.jokers = list(jokers)
    return state


def test_faceless_joker_rewards_three_discarded_faces_and_isolates_parent():
    cards = [
        BalatroCard("J", "Spades"),
        BalatroCard("Q", "Hearts"),
        BalatroCard("K", "Clubs"),
    ]
    state = _state(cards, [FacelessJoker()])

    projected = LiveDiscardJokerProjector().project(state, cards)

    assert projected.money == 5
    assert state.money == 0


def test_faceless_joker_uses_pareidolia_face_semantics():
    cards = [
        BalatroCard("2", "Spades"),
        BalatroCard("3", "Hearts"),
        BalatroCard("4", "Clubs"),
    ]
    state = _state(cards, [PareidoliaJoker(), FacelessJoker()])

    projected = LiveDiscardJokerProjector().project(state, cards)

    assert projected.money == 5


def test_faceless_joker_requires_three_faces_in_same_discard():
    cards = [
        BalatroCard("J", "Spades"),
        BalatroCard("Q", "Hearts"),
        BalatroCard("2", "Clubs"),
    ]
    state = _state(cards, [FacelessJoker()])

    projected = LiveDiscardJokerProjector().project(state, cards)

    assert projected.money == 0


def test_mail_in_rebate_rewards_five_per_matching_discard():
    cards = [
        BalatroCard("K", "Spades"),
        BalatroCard("K", "Hearts"),
        BalatroCard("Q", "Clubs"),
    ]
    state = _state(cards, [MailInRebateJoker("K")], money=1)

    projected = LiveDiscardJokerProjector().project(state, cards)

    assert projected.money == 11
    assert state.money == 1


def test_faceless_and_mail_in_rebate_stack_in_one_discard():
    cards = [
        BalatroCard("J", "Spades"),
        BalatroCard("Q", "Hearts"),
        BalatroCard("K", "Clubs"),
    ]
    state = _state(
        cards,
        [FacelessJoker(), MailInRebateJoker("K")],
    )

    projected = LiveDiscardJokerProjector().project(state, cards)

    assert projected.money == 10


def test_faceless_and_mail_in_rebate_do_not_block_play_projection():
    ace = BalatroCard("A", "Spades")
    state = _state(
        [ace],
        [FacelessJoker(), MailInRebateJoker("K")],
    )

    transition = LiveVisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.minimum == 16


def test_mail_in_rebate_round_target_hydrates_factory_rank():
    class Decoder:
        def string_fields(self, address):
            assert address == 7
            return {"rank": LuaValue("string", "King", 0)}

    round_state = _normalize_round_joker_public_state(
        Decoder(),
        {"mail_card": LuaValue("table", 7, 0)},
    )
    assert round_state["j_mail"] == {"rank": "King"}

    joker = LiveJokerFactory().create(
        {
            "center": "j_mail",
            "label": "Mail-In Rebate",
            "public_state": round_state["j_mail"],
        }
    )
    assert isinstance(joker, MailInRebateJoker)
    assert joker.rank == "K"


class _OneDrawModel:
    def distribution(self, composition, count):
        cards = tuple(
            BalatroCard(str(index + 2), "Diamonds")
            for index in range(count)
        )
        return SimpleNamespace(
            exact=True,
            outcomes=(SimpleNamespace(cards=cards, probability=1.0),),
        )

    @staticmethod
    def card_from_signature(signature):
        return signature

    @staticmethod
    def remaining_cards(composition, outcome):
        return []


class _RecordingPlanner(LiveBlindClearPlanner):
    def __init__(self):
        super().__init__(draw_outcomes=_OneDrawModel(), horizon=2)
        self.child_money = []

    def _best_value(self, state, depth):
        self.child_money.append(state.money)
        return self._terminal_value(state, clear=False), True


def test_d1_discard_child_receives_faceless_and_mail_in_cash():
    cards = [
        BalatroCard("J", "Spades"),
        BalatroCard("Q", "Hearts"),
        BalatroCard("K", "Clubs"),
    ]
    state = _state(
        cards,
        [FacelessJoker(), MailInRebateJoker("K")],
    )
    state.deck = [
        BalatroCard("2", "Diamonds"),
        BalatroCard("3", "Diamonds"),
        BalatroCard("4", "Diamonds"),
    ]
    state.discards_remaining = 2
    planner = _RecordingPlanner()

    planner._estimate_discard(
        state,
        BalatroAction(DISCARD_CARDS, cards),
        depth=2,
    )

    assert planner.child_money == [10]
    assert state.money == 0
