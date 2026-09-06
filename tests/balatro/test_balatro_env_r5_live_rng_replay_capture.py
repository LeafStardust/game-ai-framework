import pytest

from games.balatro.env.rng import BalatroRNG, pseudohash
from games.balatro.live.rng_replay_capture import (
    LiveRNGReplayCaptureError,
    rng_replay_snapshot_from_live_memory,
)
from games.balatro.live.runtime.luajit_memory import LuaValue


def _lua(kind, value):
    return LuaValue(kind=kind, value=value, raw=0)


class _Decoder:
    def __init__(self, tables):
        self.tables = tables

    def string_fields(self, address):
        return dict(self.tables[address])


def _fixture(*, seed="R5SEED01", nodes=None, hashed_seed=None):
    nodes = {"shop": 0.125, "Joker1": 0.75} if nodes is None else nodes
    hashed_seed = pseudohash(seed) if hashed_seed is None else hashed_seed
    pseudorandom = {
        "seed": _lua("string", seed),
        "hashed_seed": _lua("number", hashed_seed),
        **{key: _lua("number", value) for key, value in nodes.items()},
    }
    decoder = _Decoder(
        {
            100: {"pseudorandom": _lua("table", 200)},
            200: pseudorandom,
        }
    )
    root = {"GAME": _lua("table", 100)}
    return decoder, root


def test_env_r5_live_rng_replay_capture_round_trips_existing_r2_snapshot_format():
    decoder, root = _fixture()

    snapshot = rng_replay_snapshot_from_live_memory(decoder, root)
    restored = BalatroRNG.from_snapshot(snapshot)

    assert snapshot["seed"] == "R5SEED01"
    assert restored.seed == "R5SEED01"
    assert restored.nodes == {"Joker1": 0.75, "shop": 0.125}
    assert snapshot == restored.snapshot()


def test_env_r5_live_rng_replay_capture_preserves_node_float_bits():
    value = float.fromhex("0x1.123456789abcdp-3")
    decoder, root = _fixture(nodes={"shop": value})

    snapshot = rng_replay_snapshot_from_live_memory(decoder, root)

    assert snapshot["nodes"]["shop"] == value.hex()


def test_env_r5_live_rng_replay_capture_rejects_seed_hash_mismatch():
    decoder, root = _fixture(hashed_seed=0.5)

    with pytest.raises(LiveRNGReplayCaptureError, match="does not match"):
        rng_replay_snapshot_from_live_memory(decoder, root)


def test_env_r5_live_rng_replay_capture_rejects_non_numeric_nodes():
    decoder, root = _fixture()
    decoder.tables[200]["shop"] = _lua("string", "not-a-number")

    with pytest.raises(LiveRNGReplayCaptureError, match="node 'shop' is not numeric"):
        rng_replay_snapshot_from_live_memory(decoder, root)


def test_env_r5_live_rng_replay_capture_rejects_missing_pseudorandom_table():
    decoder = _Decoder({100: {}})
    root = {"GAME": _lua("table", 100)}

    with pytest.raises(LiveRNGReplayCaptureError, match="G.GAME.pseudorandom table is unavailable"):
        rng_replay_snapshot_from_live_memory(decoder, root)
