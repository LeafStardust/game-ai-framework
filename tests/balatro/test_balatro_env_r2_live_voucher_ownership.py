from games.balatro.live import DefaultBalatroStateTranslator, LiveBalatroSnapshot
from games.balatro.live.runtime.live_memory_observer import (
    snapshot_payload_from_live_memory,
)
from games.balatro.live.runtime.luajit_memory import LuaValue


class _FakeDecoder:
    def __init__(self, tables):
        self.tables = tables

    def string_fields(self, address):
        return self.tables[address]

    def array_items(self, address):
        return ()


def _table(address):
    return LuaValue("table", address, 0)


def _boolean(value):
    return LuaValue("boolean", bool(value), 0)


def _integer(value):
    return LuaValue("integer", int(value), 0)


def _snapshot_payload(used_vouchers_marker=...):
    game_address = 100
    tables = {game_address: {}}
    if used_vouchers_marker is not ...:
        used_vouchers_address = 101
        tables[game_address]["used_vouchers"] = _table(used_vouchers_address)
        tables[used_vouchers_address] = used_vouchers_marker
    decoder = _FakeDecoder(tables)
    payload, _, _ = snapshot_payload_from_live_memory(
        decoder,
        {"GAME": _table(game_address)},
    )
    return payload


def _translate(payload):
    return DefaultBalatroStateTranslator().translate(
        LiveBalatroSnapshot(
            sequence=1,
            phase="SHOP",
            state_complete=True,
            payload=payload,
        )
    )


def test_env_r2_live_observer_distinguishes_authoritative_empty_voucher_ownership():
    payload = _snapshot_payload({})

    assert payload["vouchers_observed"] is True
    assert payload["vouchers"] == []

    state = _translate(payload)
    assert state.vouchers_observed is True
    assert state.vouchers == []


def test_env_r2_live_observer_exposes_only_true_redeemed_voucher_keys_canonically():
    payload = _snapshot_payload(
        {
            "v_wasteful": _boolean(True),
            "v_antimatter": _boolean(False),
            "v_crystal_ball": _boolean(True),
        }
    )

    assert payload["vouchers_observed"] is True
    assert payload["vouchers"] == ["v_crystal_ball", "v_wasteful"]

    state = _translate(payload)
    assert state.vouchers_observed is True
    assert state.vouchers == ["v_crystal_ball", "v_wasteful"]


def test_env_r2_live_observer_fails_closed_when_used_vouchers_is_missing():
    payload = _snapshot_payload()

    assert payload["vouchers_observed"] is False
    assert "vouchers" not in payload

    state = _translate(payload)
    assert state.vouchers_observed is False
    assert state.vouchers == []


def test_env_r2_live_observer_fails_closed_for_malformed_used_voucher_key():
    payload = _snapshot_payload({"not_a_voucher": _boolean(True)})

    assert payload["vouchers_observed"] is False
    assert "vouchers" not in payload


def test_env_r2_live_observer_fails_closed_for_nonboolean_used_voucher_value():
    payload = _snapshot_payload({"v_grabber": _integer(1)})

    assert payload["vouchers_observed"] is False
    assert "vouchers" not in payload


def test_env_r2_translator_requires_exact_observed_voucher_list():
    invalid_payloads = (
        {"vouchers_observed": True},
        {"vouchers_observed": True, "vouchers": "v_grabber"},
        {"vouchers_observed": True, "vouchers": ["bad"]},
        {"vouchers_observed": True, "vouchers": ["v_grabber", "v_grabber"]},
        {"vouchers_observed": "yes", "vouchers": ["v_grabber"]},
    )

    for payload in invalid_payloads:
        state = _translate(payload)
        assert state.vouchers_observed is False
        assert state.vouchers == []


def test_env_r2_state_copy_preserves_voucher_ownership_observation():
    state = _translate(
        {
            "vouchers_observed": True,
            "vouchers": ["v_grabber", "v_crystal_ball"],
        }
    )

    copied = state.copy()

    assert copied.vouchers_observed is True
    assert copied.vouchers == ["v_grabber", "v_crystal_ball"]
    assert copied.vouchers is not state.vouchers
