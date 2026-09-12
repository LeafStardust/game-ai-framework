import json

import pytest

from games.balatro.env.blind_progression import BlindProgressionState
from games.balatro.env.parity import canonical_public_state_signature
from games.balatro.env.performance import _tactical_play_template
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.serialization import HEADLESS_RUN_STATE_SCHEMA
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


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload.__setitem__("schema", "unknown"),
        lambda payload: payload.pop("rng"),
        lambda payload: payload["private_zones"]["draw_pile"].__setitem__(0, -1),
        lambda payload: payload["cards"][0].pop("rank"),
        lambda payload: payload["public"].pop("phase"),
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
