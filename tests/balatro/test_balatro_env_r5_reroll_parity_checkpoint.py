from copy import deepcopy

import pytest

from games.balatro.env.rng import pseudohash
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.reroll_parity_checkpoint import (
    LiveRerollParityCheckpoint,
    LiveRerollParityCheckpointError,
    capture_live_reroll_parity_checkpoint,
    headless_reroll_run_from_live_checkpoint,
)
from games.balatro.live.runtime.live_memory_shop_terms import LiveShopRerollTerms
from games.balatro.live.runtime.luajit_memory import LuaValue


def _lua(kind, value):
    return LuaValue(kind=kind, value=value, raw=0)


class _Decoder:
    def __init__(self, tables, arrays=None):
        self.tables = tables
        self.arrays = arrays or {}

    def string_fields(self, address):
        return dict(self.tables[address])

    def array_items(self, address):
        return list(self.arrays.get(address, []))


class _Observer:
    def __init__(self, snapshots, decoder, root):
        self.snapshots = list(snapshots)
        self.decoder = decoder
        self.root = root
        self.calls = 0

    def observe(self):
        index = min(self.calls, len(self.snapshots) - 1)
        self.calls += 1
        return deepcopy(self.snapshots[index])

    def _root(self):
        return self.decoder, 0, self.root


def _snapshot(*, sequence=1, money=20):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase="SHOP",
        state_complete=True,
        payload={
            "deck": "RED",
            "stake": "WHITE",
            "money": money,
            "round": {"hands_left": 4, "discards_left": 3, "chips": 300},
            "hand": {"limit": 8, "cards": []},
            "cards": {"cards": []},
            "vouchers_observed": True,
            "vouchers": [],
        },
    )


def _observer(*, tags=0, free_rerolls=0, reroll_cost=5, snapshots=None):
    seed = "R5SEED01"
    tables = {
        100: {
            "pseudorandom": _lua("table", 200),
            "current_round": _lua("table", 300),
            "tags": _lua("table", 400),
        },
        200: {
            "seed": _lua("string", seed),
            "hashed_seed": _lua("number", pseudohash(seed)),
            "shop": _lua("number", 0.125),
        },
        300: {
            "reroll_cost": _lua("number", reroll_cost),
            "free_rerolls": _lua("number", free_rerolls),
        },
    }
    tag_items = [(index + 1, _lua("table", 500 + index)) for index in range(tags)]
    decoder = _Decoder(tables, arrays={400: tag_items})
    root = {"GAME": _lua("table", 100)}
    snapshots = snapshots or [_snapshot(), _snapshot()]
    return _Observer(snapshots, decoder, root)


def test_env_r5_reroll_checkpoint_captures_stable_public_and_private_authority():
    checkpoint = capture_live_reroll_parity_checkpoint(_observer())

    assert checkpoint.public_snapshot.phase == "SHOP"
    assert checkpoint.public_snapshot.payload["money"] == 20
    assert checkpoint.rng_snapshot["seed"] == "R5SEED01"
    assert checkpoint.rng_snapshot["nodes"]["shop"] == float(0.125).hex()
    assert checkpoint.reroll_terms == LiveShopRerollTerms(cost=5, free_rerolls=0)
    assert checkpoint.active_tag_count == 0


def test_env_r5_reroll_checkpoint_rejects_public_change_during_capture():
    observer = _observer(snapshots=[_snapshot(sequence=1, money=20), _snapshot(sequence=2, money=19)])

    with pytest.raises(LiveRerollParityCheckpointError, match="public state changed"):
        capture_live_reroll_parity_checkpoint(observer)


def test_env_r5_reroll_checkpoint_restores_headless_rng_and_current_cost():
    checkpoint = capture_live_reroll_parity_checkpoint(_observer(reroll_cost=7))

    run = headless_reroll_run_from_live_checkpoint(checkpoint)

    assert run.seed == "R5SEED01"
    assert run.rng_snapshot() == checkpoint.rng_snapshot
    assert run.base_reroll_cost == 5
    assert run.reroll_cost == 7
    assert run.tags == []
    assert run.public.phase == "SHOP"
    assert run.public.shop_active is True
    assert run.public.money == 20


def test_env_r5_reroll_checkpoint_rejects_active_tags():
    checkpoint = capture_live_reroll_parity_checkpoint(_observer(tags=1))

    with pytest.raises(LiveRerollParityCheckpointError, match="does not admit active Tags"):
        headless_reroll_run_from_live_checkpoint(checkpoint)


def test_env_r5_reroll_checkpoint_rejects_free_rerolls():
    checkpoint = capture_live_reroll_parity_checkpoint(_observer(free_rerolls=1, reroll_cost=0))

    with pytest.raises(LiveRerollParityCheckpointError, match="does not admit free rerolls"):
        headless_reroll_run_from_live_checkpoint(checkpoint)


def test_env_r5_reroll_checkpoint_rejects_unobserved_voucher_state():
    checkpoint = capture_live_reroll_parity_checkpoint(_observer())
    payload = deepcopy(checkpoint.public_snapshot.payload)
    payload["vouchers_observed"] = False
    payload.pop("vouchers", None)
    unsupported = LiveRerollParityCheckpoint(
        public_snapshot=LiveBalatroSnapshot(
            sequence=checkpoint.public_snapshot.sequence,
            phase="SHOP",
            state_complete=True,
            payload=payload,
        ),
        rng_snapshot=checkpoint.rng_snapshot,
        reroll_terms=checkpoint.reroll_terms,
        active_tag_count=0,
    )

    with pytest.raises(LiveRerollParityCheckpointError, match="exact Voucher"):
        headless_reroll_run_from_live_checkpoint(unsupported)
