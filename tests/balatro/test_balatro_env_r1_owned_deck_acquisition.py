import pytest

from games.balatro.card import BalatroCard
from games.balatro.env import EnvAction
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    ShopTransitionEngine,
)
from games.balatro.jokers.drivers_license import DriversLicenseJoker
from games.balatro.jokers.erosion import ErosionJoker
from games.balatro.jokers.steel_joker import SteelJoker
from games.balatro.jokers.stone_joker import StoneJoker
from games.balatro.live import DefaultBalatroStateTranslator, LiveBalatroSnapshot
from games.balatro.live.joker_projection import LiveJokerScoreProjector
from games.balatro.state import BalatroState


OWNED_DECK_SCORING_TYPES = (
    SteelJoker,
    StoneJoker,
    DriversLicenseJoker,
    ErosionJoker,
)


def _snapshot(owned_cards_marker=...):
    payload = {
        "deck": "RED",
        "stake": "WHITE",
        "hand": {"count": 0, "limit": 8, "cards": []},
        "cards": {"count": 0, "limit": 52, "cards": []},
        "jokers": {"count": 0, "limit": 5, "cards": []},
        "consumables": {"count": 0, "limit": 2, "cards": []},
    }
    if owned_cards_marker is not ...:
        payload["owned_cards"] = owned_cards_marker
    return LiveBalatroSnapshot(
        sequence=1,
        phase="SHOP",
        state_complete=True,
        payload=payload,
    )


def _owned_card(*, rank="A", suit="S", enhancement=None):
    modifier = {}
    if enhancement is not None:
        modifier["enhancement"] = enhancement
    return {
        "value": {"rank": rank, "suit": suit},
        "modifier": modifier,
        "debuff": False,
        "permanent_bonus": 0,
        "forced_selection": False,
    }


def _shop_state(*, owned=True) -> BalatroState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.money = 20
    state.hand_size = 8
    state.hands_remaining = 2
    state.discards_remaining = 1
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    state.owned_deck = (
        [
            BalatroCard("A", "Spades", enhancement="Steel"),
            BalatroCard("K", "Hearts", enhancement="Stone"),
        ]
        if owned
        else None
    )
    return state


def _priced(joker_type):
    joker = joker_type()
    joker.cost = 5
    return joker


def test_translator_preserves_complete_authoritative_owned_deck():
    state = DefaultBalatroStateTranslator().translate(
        _snapshot(
            {
                "count": 2,
                "limit": 2,
                "cards": [
                    _owned_card(enhancement="m_steel"),
                    _owned_card(rank="K", suit="H", enhancement="m_stone"),
                ],
            }
        )
    )

    assert state.owned_deck is not None
    assert [(card.rank, card.suit, card.enhancement) for card in state.owned_deck] == [
        ("A", "Spades", "Steel"),
        ("K", "Hearts", "Stone"),
    ]


def test_translator_keeps_missing_owned_deck_unobserved():
    state = DefaultBalatroStateTranslator().translate(_snapshot())
    assert state.owned_deck is None


def test_translator_accepts_authoritative_empty_owned_deck():
    state = DefaultBalatroStateTranslator().translate(
        _snapshot({"count": 0, "limit": 0, "cards": []})
    )
    assert state.owned_deck == []


@pytest.mark.parametrize(
    "owned_cards",
    (
        {"count": 2, "limit": 2, "cards": [_owned_card()]},
        {"count": 1, "limit": 1, "cards": [{}]},
        {"count": 1, "limit": 1, "cards": [_owned_card(rank="JOKER")]},
        {"count": 1, "limit": 1, "cards": [_owned_card(suit="Stars")]},
        {"count": 1, "limit": 1, "cards": [_owned_card(enhancement="m_unknown")]},
        {"count": 1, "limit": 1, "cards": ["not-a-card"]},
    ),
)
def test_translator_fails_closed_instead_of_partially_translating_owned_deck(owned_cards):
    state = DefaultBalatroStateTranslator().translate(_snapshot(owned_cards))
    assert state.owned_deck is None


@pytest.mark.parametrize("joker_type", OWNED_DECK_SCORING_TYPES)
def test_balatro_env_r1_owned_deck_scoring_requires_authoritative_owned_deck(joker_type):
    state = _shop_state(owned=False)
    state.shop_jokers = [_priced(joker_type)]
    run = HeadlessRunState(public=state, seed=40)
    engine = ShopTransitionEngine()
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action not in engine.legal_actions(run)
    with pytest.raises(
        HeadlessTransitionError,
        match="illegal shop transition: BUY_JOKER",
    ):
        engine.step(run, action)


@pytest.mark.parametrize("joker_type", OWNED_DECK_SCORING_TYPES)
def test_balatro_env_r1_owned_deck_scoring_purchase_is_exact_inventory_only(joker_type):
    state = _shop_state(owned=True)
    state.shop_jokers = [_priced(joker_type)]
    run = HeadlessRunState(public=state, seed=41)
    engine = ShopTransitionEngine()
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    candidate = state.shop_jokers[0]
    assert LiveJokerScoreProjector.supports_in_state(candidate, state)
    assert action in engine.legal_actions(run)

    next_run = engine.step(run, action)

    assert run.public.money == 20
    assert run.public.jokers == []
    assert len(run.public.shop_jokers) == 1
    assert next_run.public.money == 15
    assert len(next_run.public.jokers) == 1
    assert type(next_run.public.jokers[0]) is joker_type
    assert next_run.public.shop_jokers == []
    assert next_run.public.owned_deck == state.owned_deck
    assert next_run.public.hand_size == 8
    assert next_run.public.hands_remaining == 2
    assert next_run.public.discards_remaining == 1
    assert next_run.public.round_reset_hands == 4
    assert next_run.public.round_reset_discards == 3


@pytest.mark.parametrize("joker_type", OWNED_DECK_SCORING_TYPES)
def test_balatro_env_r1_owned_deck_scoring_editions_remain_fail_closed(joker_type):
    state = _shop_state(owned=True)
    joker = _priced(joker_type)
    joker.edition = "Negative"
    state.shop_jokers = [joker]
    run = HeadlessRunState(public=state, seed=42)
    engine = ShopTransitionEngine()
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action not in engine.legal_actions(run)
    with pytest.raises(
        HeadlessTransitionError,
        match="illegal shop transition: BUY_JOKER",
    ):
        engine.step(run, action)
