import json

import pytest

from games.balatro.env.blind_progression import BlindProgressionState
from games.balatro.env.parity import canonical_public_state_signature
from games.balatro.env.performance import _tactical_play_template
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.serialization import HEADLESS_RUN_STATE_SCHEMA
from games.balatro.env.shop_booster_generation import GeneratedShopBoosterItem
from games.balatro.env.shop_consumable_items import GeneratedShopConsumableItem
from games.balatro.env.shop_items import GeneratedShopJokerItem
from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


def _card_ids(cards):
    return tuple(id(card) for card in cards)


def test_env_r6_headless_state_round_trip_preserves_exact_state_rng_and_identity():
    run = apply_supported_ordinary_play(_tactical_play_template(), (0,))
    run.blind_progression_state = BlindProgressionState(
        small_status="Current",
        blind_on_deck="Small",
    )

    payload = run.serialize()
    restored = HeadlessRunState.restore(json.loads(json.dumps(payload)))

    assert payload["schema"] == HEADLESS_RUN_STATE_SCHEMA
    assert restored is not run
    assert canonical_public_state_signature(restored.public) == canonical_public_state_signature(run.public)
    assert restored.rng_snapshot() == run.rng_snapshot()
    assert restored.blind_progression_state == run.blind_progression_state
    assert restored.serialize() == payload

    order_ids = set(_card_ids(restored.require_playing_card_order()))
    assert set(_card_ids(restored.public.owned_deck)) == order_ids
    assert set(_card_ids(restored.public.hand)).issubset(order_ids)
    assert set(_card_ids(restored.public.deck)).issubset(order_ids)
    assert set(_card_ids(restored.public.discard_pile)).issubset(order_ids)
    assert _card_ids(restored.draw_pile) == tuple(
        id(restored.require_playing_card_order()[index])
        for index in payload["private_zones"]["draw_pile"]
    )

    continued = apply_supported_ordinary_play(restored, (0,))
    expected = apply_supported_ordinary_play(run, (0,))
    assert canonical_public_state_signature(continued.public) == canonical_public_state_signature(expected.public)
    assert continued.rng_snapshot() == expected.rng_snapshot()


def test_env_r6_headless_state_snapshot_is_detached_from_source():
    run = _tactical_play_template()
    payload = run.serialize()

    payload["public"]["money"] = 999
    payload["cards"][0]["rank"] = "?"

    assert run.public.money == 0
    assert run.require_playing_card_order()[0].rank != "?"


def test_env_r6_headless_state_round_trips_exact_generated_shop_metadata():
    run = _tactical_play_template()
    run.public.phase = "SHOP"
    run.public.shop_active = True
    run.generation_discovery = {
        "j_joker": True,
        "c_fool": False,
        "v_blank": False,
        "p_buffoon_normal_1": False,
    }
    run.public.shop_jokers = [
        GeneratedShopJokerItem("j_joker", 1, 2, None, 2, True)
    ]
    run.public.shop_consumables = [
        GeneratedShopConsumableItem("Tarot", "c_fool", 3, 3, False)
    ]
    run.public.shop_vouchers = [
        GeneratedShopVoucherItem("v_blank", 10, 10, None, False)
    ]
    run.public.shop_boosters = [
        GeneratedShopBoosterItem(
            "p_buffoon_normal_1", "Buffoon", "Buffoon Pack", 4, 4, 2, 1, 1, False
        )
    ]

    payload = run.serialize()
    restored = HeadlessRunState.restore(json.loads(json.dumps(payload)))

    assert restored.public.shop_jokers == run.public.shop_jokers
    assert restored.public.shop_consumables == run.public.shop_consumables
    assert restored.public.shop_vouchers == run.public.shop_vouchers
    assert restored.public.shop_boosters == run.public.shop_boosters
    assert restored.generation_discovery == run.generation_discovery
    assert restored.serialize() == payload

    payload["public"]["shop_jokers"][0]["fields"]["discovered"] = False
    with pytest.raises(HeadlessTransitionError, match="invalid headless run-state snapshot"):
        HeadlessRunState.restore(payload)


def test_env_r6_headless_state_round_trips_and_validates_boss_selection_state():
    from games.balatro.env.episode_backend import pristine_red_white_reset

    run = pristine_red_white_reset("R6-BOSS-SELECTION")
    payload = run.serialize()
    restored = HeadlessRunState.restore(json.loads(json.dumps(payload)))

    assert restored.boss_selection_state == run.boss_selection_state
    assert restored.blind_progression_state.boss_name == (
        run.blind_progression_state.boss_name
    )
    assert restored.serialize() == payload

    selected_key = next(
        key
        for key, count in payload["boss_selection"]["usage_counts"].items()
        if count == 1
    )
    payload["boss_selection"]["usage_counts"].pop(selected_key)
    with pytest.raises(HeadlessTransitionError):
        HeadlessRunState.restore(payload)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload.__setitem__("schema", "unknown"),
        lambda payload: payload.pop("rng"),
        lambda payload: payload["private_zones"]["draw_pile"].__setitem__(0, -1),
        lambda payload: payload["cards"][0].pop("rank"),
        lambda payload: payload["public"].pop("phase"),
        lambda payload: payload["public"]["shop_jokers"].append(
            {"type": "JOKER", "fields": {"center_key": "j_joker"}}
        ),
    ],
)
def test_env_r6_headless_state_restore_fails_closed_on_malformed_payload(mutate):
    payload = _tactical_play_template().serialize()
    mutate(payload)

    with pytest.raises(HeadlessTransitionError):
        HeadlessRunState.restore(payload)


def test_env_r6_headless_state_serialize_fails_closed_on_unowned_objects():
    run = _tactical_play_template()
    run.public.jokers = [object()]

    with pytest.raises(HeadlessTransitionError, match="nonempty jokers"):
        run.serialize()

    pack_run = _tactical_play_template()
    pack_run.pack_choices = [object()]
    with pytest.raises(HeadlessTransitionError, match="pack-choice"):
        pack_run.serialize()
