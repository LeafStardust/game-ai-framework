from dataclasses import FrozenInstanceError

import pytest

from games.balatro.env.action_encoding import (
    PUBLIC_ACTION_SCHEMA,
    PUBLIC_ACTION_VERSION,
    ActionMask,
    PublicActionEncodingError,
    action_from_index,
    action_index,
    apply_action_mask,
    legal_action_mask,
)
from games.balatro.env.actions import EnvAction
from games.balatro.env.transition import HeadlessRunState, ShopTransitionEngine
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.state import BalatroState


def test_env_o_action_schema_is_versioned_fixed_and_contract_ordered():
    assert PUBLIC_ACTION_SCHEMA.version == PUBLIC_ACTION_VERSION
    assert PUBLIC_ACTION_SCHEMA.shape == (27,)
    assert [(slot.index, slot.alias, slot.params) for slot in PUBLIC_ACTION_SCHEMA.slots[:4]] == [
        (0, "END_SHOP", ()),
        (1, "BUY_JOKER", (("slot", 0),)),
        (2, "BUY_JOKER", (("slot", 1),)),
        (3, "BUY_JOKER", (("slot", 2),)),
    ]
    assert [slot.alias for slot in PUBLIC_ACTION_SCHEMA.slots[-2:]] == ["SKIP_BLIND", "SELECT_BLIND"]


def test_env_o_action_indices_round_trip_parameterized_slots():
    for slot in PUBLIC_ACTION_SCHEMA.slots:
        assert action_index(slot.action()) == slot.index
        assert action_from_index(slot.index) == slot.action()


def test_env_o_legality_mask_uses_only_exact_actions_and_is_immutable():
    actions = (
        EnvAction.from_alias("BUY_JOKER", {"slot": 2}),
        EnvAction.from_alias("REROLL_SHOP"),
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 4}),
    )
    mask = legal_action_mask(actions)
    assert mask.schema_version == PUBLIC_ACTION_VERSION
    assert mask.shape == PUBLIC_ACTION_SCHEMA.shape
    assert {index for index, value in enumerate(mask.values) if value} == {
        action_index(action) for action in actions
    }
    with pytest.raises(FrozenInstanceError):
        mask.values = ()


def test_env_o_masked_probabilities_make_illegal_mass_exactly_zero():
    legal = EnvAction.from_alias("SELECT_BLIND")
    mask = legal_action_mask((legal,))
    result = apply_action_mask([1.0] * len(mask.values), mask)
    assert result[action_index(legal)] == 1.0
    assert all(value == 0.0 for index, value in enumerate(result) if index != action_index(legal))
    assert sum(result) == 1.0


def test_env_o_mask_consumes_canonical_shop_legality_without_reimplementing_it():
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.money = 2
    joker = FlatMultJoker()
    joker.price = 2
    joker.edition = None
    state.shop_jokers = [joker]
    run = HeadlessRunState(public=state, seed="ACTION-SCHEMA")
    actions = ShopTransitionEngine().legal_actions(run)
    mask = legal_action_mask(actions)
    assert {PUBLIC_ACTION_SCHEMA.slots[index].alias for index, value in enumerate(mask.values) if value} == {
        "BUY_JOKER", "END_SHOP"
    }


def test_env_o_terminal_empty_mask_returns_all_zero_without_rescue_action():
    mask = legal_action_mask(())
    assert apply_action_mask([1.0] * len(mask.values), mask) == (0.0,) * len(mask.values)


@pytest.mark.parametrize(
    "action",
    [
        EnvAction.from_alias("BUY_JOKER", {"slot": 3}),
        EnvAction.from_alias("CHOOSE_PACK_OPTION", {"option_index": 4}),
        EnvAction.from_alias("END_SHOP", {"slot": 0}),
    ],
)
def test_env_o_out_of_schema_parameters_fail_closed(action):
    with pytest.raises(PublicActionEncodingError, match="outside the versioned schema"):
        action_index(action)


def test_env_o_duplicate_actions_and_zero_legal_mass_fail_closed():
    action = EnvAction.from_alias("END_SHOP")
    with pytest.raises(PublicActionEncodingError, match="duplicate legal action"):
        legal_action_mask((action, action))
    mask = legal_action_mask((action,))
    with pytest.raises(PublicActionEncodingError, match="zero probability mass"):
        apply_action_mask([0.0] * len(mask.values), mask)


def test_env_o_probability_shape_and_values_fail_closed():
    mask = legal_action_mask(())
    with pytest.raises(PublicActionEncodingError, match="shape"):
        apply_action_mask([], mask)
    bad = [1.0] * len(mask.values)
    bad[0] = float("nan")
    with pytest.raises(PublicActionEncodingError, match="finite and nonnegative"):
        apply_action_mask(bad, mask)
    with pytest.raises(PublicActionEncodingError, match="version mismatch"):
        apply_action_mask([1.0] * len(mask.values), ActionMask("old", mask.values))
