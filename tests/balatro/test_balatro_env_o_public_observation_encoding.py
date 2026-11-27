from dataclasses import FrozenInstanceError, replace
from hashlib import sha256

import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.env.consumable_centers import VANILLA_SPECTRAL_CENTER_ORDER
from games.balatro.env.observation_encoding import (
    PUBLIC_OBSERVATION_SCHEMA,
    PUBLIC_OBSERVATION_VERSION,
    BOSS_NAMES,
    JOKER_CENTER_KEYS,
    PublicObservationEncodingError,
    VOUCHER_KEYS,
    encode_public_observation,
)
from games.balatro.env.public_observation import public_observation_state
from games.balatro.env.actions import EnvAction
from games.balatro.env.state import EnvStateFrame, RunStatus, TurnOwner
from games.balatro.env.shop_items import GeneratedShopJokerItem
from games.balatro.env.shop_consumable_items import GeneratedShopConsumableItem
from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
from games.balatro.env.transition import HeadlessRunState, ShopTransitionEngine
from games.balatro.env.voucher_capabilities import SHOP_BASE_GENERATION_VOUCHER_KEYS
from games.balatro.env.voucher_centers import VANILLA_VOUCHER_CENTER_KEYS
from games.balatro.env.boss_selection import VANILLA_BOSS_NAMES
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.castle import CastleJoker
from games.balatro.jokers.cloud_9 import Cloud9Joker
from games.balatro.jokers.rocket import RocketJoker
from games.balatro.jokers.vampire import VampireJoker
from games.balatro.spectrals import create_spectral
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
    assert encoded.shape == (3338,)
    assert PUBLIC_OBSERVATION_SCHEMA.feature_names[:5] == (
        "frame.status", "frame.owner", "state.phase", "state.money", "state.ante"
    )
    assert _at(encoded, "state.money") == 7.0
    assert _at(encoded, "state.blind.requirement") == 300.0
    assert _at(encoded, "hand.0.rank") == 13.0
    assert _at(encoded, "jokers.0.present") == 1.0


def test_env_o_v7_appends_only_the_exact_pending_double_tag_count():
    frame = _frame()
    names = PUBLIC_OBSERVATION_SCHEMA.feature_names
    legacy_digest = sha256("\n".join(names[:-1]).encode()).hexdigest()
    assert legacy_digest == "b170f7f6703953f6f20e72143ec0bd849b6549729c63393244c0deb3ab55601c"
    assert names[-1] == "tags.pending_double_count"

    baseline = frame.encoded_observation()
    pending = replace(frame, pending_double_tags=2).encoded_observation()
    assert pending.values[:-1] == baseline.values[:-1]
    assert (baseline.values[-1], pending.values[-1]) == (0.0, 2.0)


@pytest.mark.parametrize("invalid", [-1, True, 1.0])
def test_env_o_rejects_inexact_pending_double_tag_count(invalid):
    with pytest.raises(ValueError, match="nonnegative integer count"):
        replace(_frame(), pending_double_tags=invalid)


@pytest.mark.parametrize(("attribute", "prefix"), [
    ("owned_deck", "owned_deck"), ("discard_pile", "discard"),
])
def test_env_o_v6_accepts_exact_bounded_deck_and_rejects_overflow(attribute, prefix):
    frame = _frame()
    legacy = encode_public_observation(frame)
    assert legacy.values[2480:3320] == (0.0,) * 840

    cards = [BalatroCard("2", "Clubs") for _ in range(81)] + [BalatroCard("A", "Spades")]
    setattr(frame.state, attribute, cards)
    encoded = encode_public_observation(frame)
    assert _at(encoded, f"{prefix}.52.present") == 1.0
    assert _at(encoded, f"{prefix}.81.present") == 1.0
    assert _at(encoded, f"{prefix}.81.rank") == 13.0
    cards.reverse()
    assert encode_public_observation(frame) == encoded

    cards.append(BalatroCard("2", "Clubs"))
    with pytest.raises(PublicObservationEncodingError, match="exceeds schema capacity 82"):
        encode_public_observation(frame)


def test_env_o_v6_encodes_held_spectral_identity_in_existing_slots():
    frame = _frame()
    spectral = create_spectral("Cryptid")
    spectral.center_key = "c_cryptid"
    frame.state.consumables = [spectral]

    encoded = encode_public_observation(frame)

    assert encoded.shape == (3338,)
    assert encoded.schema_version == "balatro-red-white-public-observation-v8"
    assert _at(encoded, "consumables.0.category") == 3.0
    assert _at(encoded, "consumables.0.center") == 35 + VANILLA_SPECTRAL_CENTER_ORDER.index("c_cryptid")


@pytest.mark.parametrize("center", [None, "c_fool", "c_unknown"])
def test_env_o_v5_rejects_spectral_without_exact_center(center):
    frame = _frame()
    spectral = create_spectral("Cryptid")
    spectral.center_key = center
    frame.state.consumables = [spectral]

    with pytest.raises(PublicObservationEncodingError, match=r"consumables\[0\]\.center"):
        encode_public_observation(frame)


@pytest.mark.parametrize(("kind", "center", "category_id", "center_id"), [
    ("Tarot", "c_fool", 1.0, 1.0),
    ("Planet", "c_mercury", 2.0, 23.0),
])
def test_env_o_v5_preserves_legacy_held_center_codes(kind, center, category_id, center_id):
    frame = _frame()
    frame.state.consumables = [GeneratedShopConsumableItem(kind, center, 3, 3)]

    encoded = encode_public_observation(frame)

    assert _at(encoded, "consumables.0.category") == category_id
    assert _at(encoded, "consumables.0.center") == center_id


def test_env_o_v4_encodes_exact_rocket_cashout_state():
    frame = _frame()
    rocket = RocketJoker()
    rocket.dollars = 7
    frame.state.jokers = [rocket]

    encoded = encode_public_observation(frame)

    assert _at(encoded, "jokers.0.dollars.present") == 1.0
    assert _at(encoded, "jokers.0.dollars") == 7.0
    assert _at(encoded, "jokers.0.increase.present") == 1.0
    assert _at(encoded, "jokers.0.increase") == 2.0


def test_env_o_v4_encodes_cloud9_identity():
    frame = _frame()
    cloud9 = Cloud9Joker()
    cloud9.center = "j_cloud_9"
    frame.state.jokers = [cloud9]

    encoded = encode_public_observation(frame)

    assert _at(encoded, "jokers.0.center") == JOKER_CENTER_KEYS.index("j_cloud_9") + 1


def test_env_o_v4_encodes_castle_suit_and_chip_state():
    frame = _frame()
    castle = CastleJoker("Clubs")
    castle.chips = 12
    frame.state.jokers = [castle]

    encoded = encode_public_observation(frame)

    assert _at(encoded, "jokers.0.suit") == 3.0
    assert _at(encoded, "jokers.0.chip_mod") == 3.0
    assert _at(encoded, "jokers.0.chips") == 12.0


def test_env_o_v4_encodes_exact_vampire_growth_state():
    frame = _frame()
    vampire = VampireJoker()
    vampire.x_mult = 1.7
    frame.state.jokers = [vampire]

    encoded = encode_public_observation(frame)

    assert _at(encoded, "jokers.0.x_mult.present") == 1.0
    assert _at(encoded, "jokers.0.x_mult") == 1.7


def test_env_o_v2_separates_all_voucher_identities_from_mechanics_support():
    assert VOUCHER_KEYS == VANILLA_VOUCHER_CENTER_KEYS
    assert len(VOUCHER_KEYS) == 32
    assert "v_blank" in VOUCHER_KEYS
    assert "v_blank" not in SHOP_BASE_GENERATION_VOUCHER_KEYS

    frame = _frame()
    frame.state.phase = "SHOP"
    frame.state.shop_active = True
    frame.state.money = 20
    frame.state.shop_vouchers = [GeneratedShopVoucherItem("v_blank", 10, 10)]
    encoded = encode_public_observation(frame)
    assert _at(encoded, "shop.vouchers.0.center") > 0.0

    run = HeadlessRunState(public=frame.state, seed="UNSUPPORTED-VOUCHER")
    assert ShopTransitionEngine().legal_actions(run) == (
        # Identity is visible, but Blank redemption remains unsupported.
        EnvAction.from_alias("REROLL_SHOP"),
        EnvAction.from_alias("END_SHOP"),
    )


def test_env_o_v3_represents_all_boss_identities_independently_of_support():
    assert BOSS_NAMES == VANILLA_BOSS_NAMES
    assert len(BOSS_NAMES) == 28
    frame = _frame()
    frame.state.blind = Blind(BlindType.BOSS, 600, reward=5)
    frame.state.boss_name = "The Hook"
    assert _at(encode_public_observation(frame), "state.boss_name") > 0.0


def test_env_o_voucher_pool_features_encode_eligibility_not_catalogue_presence():
    frame = _frame()
    frame.state.voucher_generation_pool_observed = True
    frame.state.voucher_generation_pool = [
        {
            "key": key,
            "cost": 10,
            "unlocked": key == "v_overstock_norm",
            "requires": [] if key == "v_overstock_norm" else ["v_overstock_norm"],
            "no_pool_flag": None,
            "yes_pool_flag": None,
            "eligible": key == "v_overstock_norm",
        }
        for key in VANILLA_VOUCHER_CENTER_KEYS
    ]
    encoded = encode_public_observation(frame)
    assert _at(encoded, "pool.voucher.v_overstock_norm") == 1.0
    assert _at(encoded, "pool.voucher.v_overstock_plus") == 0.0
    assert _at(encoded, "pool.voucher.v_blank") == 0.0

    frame.state.voucher_generation_pool[0]["eligible"] = None
    with pytest.raises(PublicObservationEncodingError, match="invalid eligibility"):
        encode_public_observation(frame)


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


def test_env_o_canonical_deck_views_hide_transient_facing_assignment():
    first = _frame()
    second = _frame()
    for frame in (first, second):
        frame.state.owned_deck[0].facing_observed = True
        frame.state.owned_deck[1].facing_observed = True

    first.state.owned_deck[0].face_down = True
    second.state.owned_deck[1].face_down = True
    first.state.deck = first.state.owned_deck.copy()
    second.state.deck = second.state.owned_deck.copy()

    first_public = public_observation_state(first.state)
    second_public = public_observation_state(second.state)

    assert encode_public_observation(first) == encode_public_observation(second)
    assert all(not card.face_down for card in first_public.owned_deck)
    assert all(not card.face_down for card in first_public.deck)
    assert first_public.owned_deck[0].rank == first.state.owned_deck[0].rank
    assert first_public.owned_deck[0] is not first.state.owned_deck[0]
    assert first.state.owned_deck[0].face_down is True
    assert second.state.owned_deck[1].face_down is True


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
