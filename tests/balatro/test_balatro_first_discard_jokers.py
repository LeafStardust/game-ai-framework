from types import SimpleNamespace

import pytest

from games.balatro.actions import BalatroAction, DISCARD_CARDS
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.blueprint import BlueprintJoker
from games.balatro.jokers.burnt_joker import BurntJoker
from games.balatro.jokers.canio import CanioJoker
from games.balatro.jokers.glass_joker import GlassJoker
from games.balatro.jokers.trading_card import TradingCardJoker
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live.discard_projection import (
    LiveDiscardJokerProjector,
    UnsupportedDiscardProjection,
)
from games.balatro.live.post_hand_outcomes import LiveVisibleCardScoreOutcomeModel
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.live_memory_discard_history_observer import (
    public_discard_history,
)
from games.balatro.live.runtime.luajit_memory import LuaValue
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.state import BalatroState


def _state(cards, jokers, *, discards_used=0, money=0):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.owned_deck = list(cards)
    state.money = money
    state.jokers = list(jokers)
    state.discards_used = discards_used
    return state


def test_state_copy_preserves_public_discard_history():
    state = BalatroState()
    state.discards_used = 2

    copied = state.copy()

    assert copied.discards_used == 2


def test_public_discard_history_uses_round_reset_minus_remaining():
    class Decoder:
        def string_fields(self, address):
            return {
                1: {
                    "current_round": LuaValue("table", 2, 0),
                    "round_resets": LuaValue("table", 3, 0),
                },
                2: {"discards_left": LuaValue("integer", 2, 0)},
                3: {"discards": LuaValue("integer", 4, 0)},
            }[address]

    root = {"GAME": LuaValue("table", 1, 0)}

    assert public_discard_history(Decoder(), root) == (4, 2)


def test_translator_preserves_observed_discard_usage():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "deck": "RED",
            "stake": "WHITE",
            "round": {
                "chips": 300,
                "hands_left": 4,
                "discards_left": 3,
                "discards_used": 1,
            },
        },
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert state.discards_remaining == 3
    assert state.discards_used == 1


def test_translator_fails_closed_when_discard_usage_is_unobserved():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={"round": {"discards_left": 2}},
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert state.discards_used is None


def test_burnt_upgrades_first_discarded_poker_hand_with_multiple_cards():
    cards = [
        BalatroCard("8", "Spades", live_id=1),
        BalatroCard("8", "Hearts", live_id=2),
    ]
    state = _state(cards, [BurntJoker()])

    projected = LiveDiscardJokerProjector().project(state, cards)

    assert projected.hand_levels["PAIR"] == 2
    assert projected.discards_used == 1
    assert state.hand_levels["PAIR"] == 1
    assert state.discards_used == 0


def test_burnt_only_upgrades_the_first_discard():
    cards = [
        BalatroCard("8", "Spades", live_id=1),
        BalatroCard("8", "Hearts", live_id=2),
    ]
    state = _state(cards, [BurntJoker()], discards_used=1)

    projected = LiveDiscardJokerProjector().project(state, cards)

    assert projected.hand_levels["PAIR"] == 1
    assert projected.discards_used == 2


def test_blueprint_copy_of_burnt_stacks_first_discard_level_up():
    cards = [
        BalatroCard("8", "Spades", live_id=1),
        BalatroCard("8", "Hearts", live_id=2),
    ]
    state = _state(cards, [BlueprintJoker(), BurntJoker()])

    projected = LiveDiscardJokerProjector().project(state, cards)

    assert projected.hand_levels["PAIR"] == 3


def test_trading_card_first_single_discard_destroys_and_rewards():
    card = BalatroCard(
        "K",
        "Hearts",
        enhancement="Glass",
        live_id=11,
    )
    other = BalatroCard("2", "Clubs", live_id=12)
    glass = GlassJoker()
    canio = CanioJoker()
    state = _state([card, other], [TradingCardJoker(), glass, canio])
    state.owned_deck = [
        BalatroCard(
            "K",
            "Hearts",
            enhancement="Glass",
            live_id=11,
        ),
        BalatroCard("2", "Clubs", live_id=12),
    ]

    projected = LiveDiscardJokerProjector().project(state, [card])

    assert projected.money == 3
    assert projected.discards_used == 1
    assert [owned.live_id for owned in projected.owned_deck] == [12]
    assert projected.glass_cards_destroyed == 1
    projected_glass = next(
        joker for joker in projected.jokers
        if type(joker).__name__ == "GlassJoker"
    )
    projected_canio = next(
        joker for joker in projected.jokers
        if type(joker).__name__ == "CanioJoker"
    )
    assert projected_glass.x_mult == pytest.approx(1.75)
    assert projected_canio.x_mult == pytest.approx(2.0)

    assert state.money == 0
    assert len(state.owned_deck) == 2
    assert glass.x_mult == pytest.approx(1.0)
    assert canio.x_mult == pytest.approx(1.0)


def test_trading_card_does_not_trigger_on_later_or_multi_card_discard():
    card = BalatroCard("K", "Hearts", live_id=1)
    second = BalatroCard("Q", "Spades", live_id=2)

    later = _state([card], [TradingCardJoker()], discards_used=1)
    later_projected = LiveDiscardJokerProjector().project(later, [card])
    assert later_projected.money == 0
    assert len(later_projected.owned_deck) == 1
    assert later_projected.discards_used == 2

    multi = _state([card, second], [TradingCardJoker()])
    multi_projected = LiveDiscardJokerProjector().project(
        multi,
        [card, second],
    )
    assert multi_projected.money == 0
    assert len(multi_projected.owned_deck) == 2
    assert multi_projected.discards_used == 1


def test_first_discard_jokers_fail_closed_without_public_history():
    card = BalatroCard("8", "Spades")
    state = _state([card], [TradingCardJoker()], discards_used=None)

    with pytest.raises(UnsupportedDiscardProjection):
        LiveDiscardJokerProjector().project(state, [card])


def test_burnt_and_trading_are_score_neutral_complete_live_projections():
    ace = BalatroCard("A", "Spades")
    state = _state([ace], [BurntJoker(), TradingCardJoker()])

    transition = LiveVisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.deterministic is True
    assert transition.distribution.minimum == 16


def test_blueprint_burnt_is_complete_and_score_neutral():
    ace = BalatroCard("A", "Spades")
    state = _state([ace], [BlueprintJoker(), BurntJoker()])

    transition = LiveVisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 16


class _PairDrawModel:
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
        super().__init__(draw_outcomes=_PairDrawModel(), horizon=2)
        self.child_pair_level = None
        self.child_discards_used = None

    def _best_value(self, state, depth):
        self.child_pair_level = state.hand_levels["PAIR"]
        self.child_discards_used = state.discards_used
        return self._terminal_value(state, clear=False), True


def test_d1_discard_child_carries_burnt_level_and_discard_history():
    cards = [
        BalatroCard("8", "Spades", live_id=1),
        BalatroCard("8", "Hearts", live_id=2),
    ]
    state = _state(cards, [BurntJoker()])
    state.deck = [
        BalatroCard("2", "Diamonds", live_id=3),
        BalatroCard("3", "Diamonds", live_id=4),
    ]
    state.discards_remaining = 2
    planner = _RecordingPlanner()

    planner._estimate_discard(
        state,
        BalatroAction(DISCARD_CARDS, cards),
        depth=2,
    )

    assert planner.child_pair_level == 2
    assert planner.child_discards_used == 1
