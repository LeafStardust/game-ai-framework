from types import SimpleNamespace

import pytest

from games.balatro.actions import (
    BUY_CONSUMABLE,
    BUY_JOKER,
    BUY_VOUCHER,
    END_SHOP,
    BalatroAction,
)
from games.balatro.card import BalatroCard
from games.balatro.consumable import PlanetCard
from games.balatro.joker import Joker, JokerContext
from games.balatro.jokers.mime import MimeJoker
from games.balatro.shop_policy import (
    BalatroShopPolicy,
    DefaultShopItemValueEstimator,
)
from games.balatro.state import BalatroState
from games.balatro.tarots import Chariot


class FlatEstimator:

    def __init__(self, values):
        self.values = values

    def estimate(self, state, action):
        return self.values.get(action.name, 0.0), ("test value",)


class InertJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        return context


class PlusMultJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is not None and context.trigger == "HAND_SCORED":
            context.score.mult += 8
        return context


def _shop_state(*, money=10):
    state = BalatroState()
    state.phase = "SHOP"
    state.money = money
    state.joker_slots = 5
    state.consumable_slots = 2
    return state


def test_shop_policy_prefers_leave_when_purchase_value_is_too_low():
    state = _shop_state(money=10)
    voucher = SimpleNamespace(price=10, label="Unknown Voucher")
    actions = [
        BalatroAction(BUY_VOUCHER, target=voucher),
        BalatroAction(END_SHOP),
    ]
    policy = BalatroShopPolicy(
        FlatEstimator({BUY_VOUCHER: 1.0}),
    )

    assert policy.choose_action(state, actions).name == END_SHOP


def test_shop_policy_buys_high_value_joker_when_economics_support_it():
    state = _shop_state(money=10)
    joker = SimpleNamespace(cost=5, label="Strong Joker", edition=None)
    actions = [
        BalatroAction(BUY_JOKER, target=joker),
        BalatroAction(END_SHOP),
    ]
    policy = BalatroShopPolicy(
        FlatEstimator({BUY_JOKER: 8.0}),
    )

    ranked = policy.rank_actions(state, actions)

    assert ranked[0].action.name == BUY_JOKER
    assert ranked[0].item_utility == 8.0
    assert ranked[0].price_penalty > 0
    assert ranked[0].interest_penalty > 0


def test_shop_policy_charges_only_incremental_reserve_shortfall():
    policy = BalatroShopPolicy(
        FlatEstimator({BUY_CONSUMABLE: 0.0}),
        reserve_target=5,
        reserve_weight=1.0,
    )
    consumable = SimpleNamespace(price=2, category="TAROT")

    below_reserve = _shop_state(money=3)
    score = policy.score_action(
        below_reserve,
        BalatroAction(BUY_CONSUMABLE, target=consumable),
    )

    assert score.reserve_penalty == 2.0


def test_shop_policy_penalizes_using_last_joker_slot():
    state = _shop_state(money=20)
    state.jokers = [InertJoker() for _ in range(4)]
    joker = SimpleNamespace(cost=1, label="Candidate")
    action = BalatroAction(BUY_JOKER, target=joker)
    policy = BalatroShopPolicy(
        FlatEstimator({BUY_JOKER: 5.0}),
        last_joker_slot_penalty=2.0,
    )

    score = policy.score_action(state, action)

    assert score.slot_penalty == 2.0


def test_shop_policy_rewards_observable_joker_editions():
    state = _shop_state(money=20)
    normal = SimpleNamespace(cost=5, label="Normal", edition=None)
    negative = SimpleNamespace(cost=5, label="Negative", edition="Negative")
    policy = BalatroShopPolicy(
        FlatEstimator({BUY_JOKER: 5.0}),
    )

    normal_score = policy.score_action(
        state,
        BalatroAction(BUY_JOKER, target=normal),
    )
    negative_score = policy.score_action(
        state,
        BalatroAction(BUY_JOKER, target=negative),
    )

    assert negative_score.edition_bonus == 4.0
    assert negative_score.total > normal_score.total


def test_default_item_estimator_uses_whole_build_joker_value():
    state = _shop_state(money=20)
    state.deck = [
        BalatroCard("K", "Hearts", enhancement="Steel"),
        BalatroCard("K", "Spades", enhancement="Steel"),
        BalatroCard("Q", "Clubs"),
    ]
    estimator = DefaultShopItemValueEstimator()

    inert, inert_notes = estimator.estimate(
        state,
        BalatroAction(BUY_JOKER, target=InertJoker()),
    )
    scoring, scoring_notes = estimator.estimate(
        state,
        BalatroAction(BUY_JOKER, target=PlusMultJoker()),
    )
    mime, mime_notes = estimator.estimate(
        state,
        BalatroAction(BUY_JOKER, target=MimeJoker()),
    )

    assert scoring > inert
    assert mime > inert
    assert any("whole-build Joker gain" in note for note in scoring_notes)
    assert any("B3 contextual gain" in note for note in mime_notes)
    assert any("whole-build Joker gain" in note for note in inert_notes)


def test_default_item_estimator_uses_planet_upgrade_data():
    state = _shop_state(money=10)
    mercury = PlanetCard("Mercury", "PAIR", 15, 1)
    estimator = DefaultShopItemValueEstimator()

    value, notes = estimator.estimate(
        state,
        BalatroAction(BUY_CONSUMABLE, target=mercury),
    )

    assert value > 2.5
    assert any("planet upgrade" in note for note in notes)
    assert any("B4 build-path gain" in note for note in notes)


def test_chariot_build_path_value_increases_with_owned_mime():
    chariot = Chariot()
    chariot.price = 3
    estimator = DefaultShopItemValueEstimator()

    without_mime = _shop_state(money=12)
    value_without, notes_without = estimator.estimate(
        without_mime,
        BalatroAction(BUY_CONSUMABLE, target=chariot),
    )

    with_mime = _shop_state(money=12)
    with_mime.jokers = [MimeJoker()]
    value_with, notes_with = estimator.estimate(
        with_mime,
        BalatroAction(BUY_CONSUMABLE, target=chariot),
    )

    assert value_with > value_without
    assert any("MimeJoker" in note for note in notes_with)
    assert any("B4 build-path gain" in note for note in notes_without)


def test_hieroglyph_has_explicit_tradeoff_notes():
    state = _shop_state(money=12)
    state.ante = 2
    voucher = SimpleNamespace(price=10, label="Hieroglyph")

    value, notes = DefaultShopItemValueEstimator().estimate(
        state,
        BalatroAction(BUY_VOUCHER, target=voucher),
    )

    assert value > 0
    assert any("-1 Ante / -1 hand" in note for note in notes)


def test_shop_policy_rejects_unsupported_random_state_action():
    state = _shop_state()
    policy = BalatroShopPolicy()

    with pytest.raises(ValueError, match="cannot safely score"):
        policy.score_action(
            state,
            BalatroAction("BUY_BOOSTER", target=SimpleNamespace(price=4)),
        )


def test_shop_policy_prefers_end_shop_on_exact_tie():
    state = _shop_state(money=10)
    policy = BalatroShopPolicy(
        FlatEstimator({BUY_JOKER: 0.35}),
        price_weight=0.0,
        interest_weight=0.0,
        reserve_weight=0.0,
        hold_bias=0.35,
    )
    joker = SimpleNamespace(cost=0, label="Tie")
    actions = [
        BalatroAction(BUY_JOKER, target=joker),
        BalatroAction(END_SHOP),
    ]

    assert policy.choose_action(state, actions).name == END_SHOP
