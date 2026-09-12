from dataclasses import FrozenInstanceError

import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.env.observation_encoding import (
    PUBLIC_OBSERVATION_SCHEMA,
    PUBLIC_OBSERVATION_VERSION,
    PublicObservationEncodingError,
    encode_public_observation,
)
from games.balatro.env.state import EnvStateFrame, RunStatus, TurnOwner
from games.balatro.env.shop_items import GeneratedShopJokerItem
from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.state import BalatroState


def _frame() -> EnvStateFrame:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.owned_deck = state.deck.copy()
    state.phase = "SELECTING_HAND"
    state.money = 7
    state.blind = Blind(BlindType.SMALL, 300, reward=3)
    state.hand = [BalatroCard("A", "Spades", live_id=901, facing_observed=True)]
    state.jokers = [FlatMultJoker()]
    return EnvStateFrame(state, RunStatus.RUNNING, TurnOwner.TACTICAL_POLICY)


def _at(encoded, name):
    return encoded.values[PUBLIC_OBSERVATION_SCHEMA.feature_names.index(name)]


def test_env_o_schema_is_versioned_fixed_and_ordered():
    encoded = _frame().encoded_observation()
    assert PUBLIC_OBSERVATION_SCHEMA.version == PUBLIC_OBSERVATION_VERSION
    assert encoded.schema_version == PUBLIC_OBSERVATION_VERSION
    assert encoded.shape == PUBLIC_OBSERVATION_SCHEMA.shape
    assert PUBLIC_OBSERVATION_SCHEMA.feature_names[:5] == (
        "frame.status", "frame.owner", "state.phase", "state.money", "state.ante"
    )
    assert _at(encoded, "state.money") == 7.0
    assert _at(encoded, "state.blind.requirement") == 300.0
    assert _at(encoded, "hand.0.rank") == 13.0
    assert _at(encoded, "jokers.0.present") == 1.0


def test_env_o_encoded_output_and_schema_are_immutable():
    encoded = _frame().encoded_observation()
    with pytest.raises(FrozenInstanceError):
        encoded.values = ()
    with pytest.raises(TypeError):
        encoded.values[0] = 99
    with pytest.raises(FrozenInstanceError):
        PUBLIC_OBSERVATION_SCHEMA.version = "changed"


def test_env_o_hidden_identity_draw_order_rng_and_live_ids_do_not_leak():
    first = _frame()
    first.state.hand = [BalatroCard("A", "Spades", live_id=1, face_down=True, forced_selection=True)]
    second = _frame()
    second.state.hand = [BalatroCard("2", "Hearts", live_id=999, face_down=True, forced_selection=True)]
    first.state.jokers[0].live_id = 40
    second.state.jokers[0].live_id = 9000
    first.state.deck = list(reversed(first.state.deck))
    second.state.deck = second.state.deck[7:] + second.state.deck[:7]
    assert encode_public_observation(first) == encode_public_observation(second)
    hidden = encode_public_observation(first)
    assert _at(hidden, "hand.0.rank") == 1.0
    assert _at(hidden, "hand.0.suit") == 1.0
    assert _at(hidden, "hand.0.forced_selection") == 1.0


def test_env_o_owned_deck_order_is_canonical_but_composition_remains_visible():
    first = _frame()
    second = _frame()
    second.state.owned_deck = list(reversed(second.state.owned_deck))
    assert encode_public_observation(first) == encode_public_observation(second)
    second.state.owned_deck[0] = BalatroCard("A", "Spades", enhancement="Bonus")
    assert encode_public_observation(first) != encode_public_observation(second)


def test_env_o_shop_and_generation_authority_have_stable_values():
    frame = _frame()
    state = frame.state
    state.phase = "SHOP"
    state.shop_active = True
    state.shop_jokers = [GeneratedShopJokerItem("j_joker", 1, 2, None, 2)]
    state.shop_vouchers = [GeneratedShopVoucherItem("v_seed_money", 10, 10)]
    state.vouchers_observed = True
    state.vouchers = ["v_crystal_ball"]
    state.joker_generation_pool_observed = True
    state.joker_generation_pools = {
        "1": [{"key": "j_joker"}], "2": [], "3": [], "4": []
    }
    encoded = encode_public_observation(frame)
    assert _at(encoded, "shop.jokers.0.center") > 0
    assert _at(encoded, "shop.vouchers.0.price") == 10.0
    assert _at(encoded, "vouchers.owned.v_crystal_ball") == 1.0
    assert _at(encoded, "pool.joker.j_joker") == 1.0
    assert _at(encoded, "pool.joker.j_abstract") == 0.0


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda state: setattr(state, "owned_deck", None), "owned_deck authority"),
        (lambda state: state.hand.extend([BalatroCard("A", "Spades")] * 23), "capacity 22"),
        (lambda state: state.jokers.append(object()), "Joker identity"),
        (lambda state: state.vouchers.append("v_unsupported"), "owned Vouchers"),
        (lambda state: setattr(state, "phase", "SECRET_PHASE"), "versioned schema"),
    ],
)
def test_env_o_unsupported_or_missing_authority_fails_closed(mutation, message):
    frame = _frame()
    mutation(frame.state)
    with pytest.raises(PublicObservationEncodingError, match=message):
        encode_public_observation(frame)


def test_env_o_source_state_is_not_mutated_and_face_up_live_id_is_ignored():
    frame = _frame()
    before_id = frame.state.hand[0].live_id
    baseline = encode_public_observation(frame)
    frame.state.hand[0].live_id = 123456
    assert encode_public_observation(frame) == baseline
    assert before_id == 901
