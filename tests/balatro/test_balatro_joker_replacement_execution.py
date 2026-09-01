from types import SimpleNamespace

from games.balatro.actions import (
    BUY_JOKER,
    END_SHOP,
    SELL_JOKER,
    BalatroAction,
)
from games.balatro.card import BalatroCard
from games.balatro.joker import Joker, JokerContext
from games.balatro.joker_policy import (
    JokerAcquisitionPolicy,
    JokerAcquisitionThresholds,
)
from games.balatro.jokers.baron import BaronJoker
from games.balatro.jokers.mime import MimeJoker
from games.balatro.shop_arbiter import BuildAwareShopArbiter
from games.balatro.shop_policy import BalatroShopPolicy
from games.balatro.state import BalatroState


class InertJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        return context


class PlusMultJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is not None:
            context.score.mult += 8
        return context


class _TransactionTransitionPlanner:
    """Deterministic build evidence for transaction-checkpoint tests only."""

    def __init__(self) -> None:
        # D2/D14 callers treat the transition planner's evaluator as part of the
        # planner interface, so the transaction fixture exposes the same minimal
        # ``evaluate(state, candidate)`` contract as JokerBuildValueEvaluator.
        self.evaluator = SimpleNamespace(
            evaluate=lambda _state, candidate: self._value(candidate)
        )

    @staticmethod
    def _value(candidate):
        gain = 2.0 if isinstance(candidate, PlusMultJoker) else 0.0
        return SimpleNamespace(
            total_gain=gain,
            direct_scoring_gain=gain,
            applicability=None,
        )

    def plan(self, state, candidate):
        candidate_value = self._value(candidate)
        if len(state.jokers) < int(state.joker_slots):
            return SimpleNamespace(
                action="ADD" if candidate_value.total_gain > 0.0 else "HOLD",
                candidate=type(candidate).__name__,
                candidate_value=candidate_value,
                replacement=None,
                alternatives=(),
                rationale=("deterministic transaction-test build evidence",),
            )

        alternatives = []
        for index, incumbent in enumerate(state.jokers):
            incumbent_value = self._value(incumbent)
            delta = candidate_value.total_gain - incumbent_value.total_gain
            alternatives.append(
                SimpleNamespace(
                    replace_index=index,
                    replace_joker=type(incumbent).__name__,
                    incumbent_value=incumbent_value,
                    candidate_value=candidate_value,
                    build_delta=delta,
                    rationale=("deterministic transaction-test replacement evidence",),
                    eligible=True,
                    blocked_reason=None,
                )
            )

        ranked = tuple(
            sorted(
                alternatives,
                key=lambda option: (-option.build_delta, option.replace_index),
            )
        )
        best = ranked[0] if ranked else None
        return SimpleNamespace(
            action=(
                "REPLACE"
                if best is not None and best.build_delta > 0.0
                else "HOLD"
            ),
            candidate=type(candidate).__name__,
            candidate_value=candidate_value,
            replacement=best,
            alternatives=ranked,
            rationale=("deterministic transaction-test build evidence",),
        )


def _state(*, money: int, slots: int = 2) -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = money
    state.joker_slots = slots
    state.deck = [
        BalatroCard("K", "Hearts", enhancement="Steel"),
        BalatroCard("K", "Spades", enhancement="Steel"),
        BalatroCard("K", "Clubs"),
        BalatroCard("Q", "Diamonds"),
        BalatroCard("9", "Hearts"),
    ]
    return state


def _replacement_policy(*, transition_planner=None) -> JokerAcquisitionPolicy:
    return JokerAcquisitionPolicy(
        JokerAcquisitionThresholds(
            minimum_purchase_advantage=0.0,
            minimum_replacement_advantage=0.0,
            price_weight=0.0,
            interest_weight=0.0,
            reserve_weight=0.0,
            last_joker_slot_penalty=0.0,
            penultimate_joker_slot_penalty=0.0,
        ),
        transition_planner=transition_planner,
    )


def _arbiter(*, transaction_fixture: bool = False) -> BuildAwareShopArbiter:
    # These tests isolate the irreversible SELL -> fresh-observation -> BUY
    # transaction contract. Neutralize D14's real resource opportunity costs so
    # they cannot turn the intended second checkpoint into an economics test.
    shop_policy = BalatroShopPolicy(
        price_weight=0.0,
        interest_weight=0.0,
        reserve_target=0,
        reserve_weight=0.0,
        last_joker_slot_penalty=0.0,
        penultimate_joker_slot_penalty=0.0,
        last_consumable_slot_penalty=0.0,
        hold_bias=0.0,
    )
    transition_planner = (
        _TransactionTransitionPlanner() if transaction_fixture else None
    )
    return BuildAwareShopArbiter(
        shop_policy=shop_policy,
        joker_policy=_replacement_policy(
            transition_planner=transition_planner,
        ),
    )


def test_full_joker_bar_replacement_emits_only_sell_step():
    state = _state(money=1)
    mime = MimeJoker()
    mime.sell_cost = 1
    inert = InertJoker()
    inert.sell_cost = 5
    state.jokers = [mime, inert]

    candidate = BaronJoker()
    candidate.cost = 6
    state.shop_jokers = [candidate]

    # A full Joker bar intentionally has no executable BUY_JOKER in the ordinary
    # visible action list. D2 still evaluates the visible shop candidate directly.
    decision = _arbiter().decide(
        state,
        [BalatroAction(END_SHOP)],
        reroll_cost=None,
    )

    assert decision.action.name == SELL_JOKER
    assert decision.action.target == 1
    assert decision.source == "JOKER_REPLACE_SELL"
    assert decision.joker is not None
    assert decision.joker.selected is not None
    assert decision.joker.selected.replace_joker == "InertJoker"
    assert decision.joker.selected.economics.sell_credit == 5
    assert decision.joker.selected.economics.money_after == 0
    assert "replacement execution step=SELL" in decision.rationale
    assert "follow-up BUY is not chained" in decision.rationale
    assert any("fresh authoritative observation" in note for note in decision.rationale)


def test_post_sale_fresh_replan_emits_buy_from_new_checkpoint():
    candidate = PlusMultJoker()
    candidate.cost = 6

    before = _state(money=1, slots=1)
    incumbent = InertJoker()
    incumbent.sell_cost = 5
    before.jokers = [incumbent]
    before.shop_jokers = [candidate]

    arbiter = _arbiter(transaction_fixture=True)
    sell = arbiter.decide(
        before,
        [BalatroAction(END_SHOP)],
        reroll_cost=None,
    )
    assert sell.action.name == SELL_JOKER

    # This is the authoritative state the next autonomous iteration would obtain
    # after the dispatcher has reconciled the completed sale.
    after = _state(money=6, slots=1)
    after.jokers = []
    after.shop_jokers = [candidate]
    buy_action = BalatroAction(BUY_JOKER, target=candidate)

    buy = arbiter.decide(
        after,
        [buy_action, BalatroAction(END_SHOP)],
        reroll_cost=None,
    )

    assert buy.action.name == BUY_JOKER
    assert buy.action.target is candidate
    assert buy.source == "JOKER_BUY"
    assert buy.joker is not None
    assert buy.joker.selected is not None
    assert buy.joker.selected.economics.sell_credit == 0
    assert buy.joker.selected.economics.money_after == 0


def test_post_sale_replan_can_abandon_original_purchase_when_shop_state_changes():
    before = _state(money=1, slots=1)
    incumbent = InertJoker()
    incumbent.sell_cost = 5
    before.jokers = [incumbent]
    candidate = PlusMultJoker()
    candidate.cost = 6
    before.shop_jokers = [candidate]

    arbiter = _arbiter(transaction_fixture=True)
    sell = arbiter.decide(
        before,
        [BalatroAction(END_SHOP)],
        reroll_cost=None,
    )
    assert sell.action.name == SELL_JOKER

    # No pending compound transaction is carried across the irreversible sale.
    # If the next authoritative checkpoint no longer offers a worthwhile Joker,
    # the fresh decision is free to hold instead of blindly buying the old target.
    after = _state(money=6, slots=1)
    after.jokers = []
    after.shop_jokers = [InertJoker()]

    replanned = arbiter.decide(
        after,
        [BalatroAction(END_SHOP)],
        reroll_cost=None,
    )

    assert replanned.action.name == END_SHOP
    assert replanned.source == "END_SHOP"
