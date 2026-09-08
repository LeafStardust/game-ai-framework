"""Parity-only capture of Balatro's keyed pseudorandom replay authority.

This module is intentionally separate from ``LiveMemoryBalatroObserver``. The
normal observer is policy-facing and must never expose hidden PRNG state. R5 may
read the same process memory through this explicit diagnostic boundary only to
construct deterministic live/simulator parity fixtures.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

from games.balatro.env.rng import BalatroRNG, pseudohash
from games.balatro.live.runtime.luajit_memory import LuaJITMemoryError
from games.balatro.live.runtime.process_memory import BalatroProcessMemoryError


class LiveRNGReplayCaptureError(RuntimeError):
    """Raised when exact live keyed-RNG replay authority cannot be captured."""


def _require_table_fields(decoder, value, *, name: str) -> dict[str, Any]:
    if value is None or getattr(value, "kind", None) != "table":
        raise LiveRNGReplayCaptureError(f"live Balatro {name} table is unavailable")
    try:
        fields = decoder.string_fields(int(value.value))
    except (BalatroProcessMemoryError, LuaJITMemoryError, TypeError, ValueError) as exc:
        raise LiveRNGReplayCaptureError(f"unable to read live Balatro {name} table") from exc
    if not isinstance(fields, dict):
        raise LiveRNGReplayCaptureError(f"live Balatro {name} table decode is malformed")
    return fields


def rng_replay_snapshot_from_live_memory(decoder, root: Mapping[str, Any]) -> dict[str, Any]:
    """Return an exact ``BalatroRNG.snapshot`` from ``G.GAME.pseudorandom``.

    Vanilla ``pseudoseed`` stores one numeric node per keyed random stream plus
    ``seed`` and ``hashed_seed`` in ``G.GAME.pseudorandom``. Capturing those
    values is sufficient to restore the existing R2 keyed RNG owner without
    reading or exposing LuaJIT's transient ``math.random`` state: every Balatro
    helper reseeds ``math.random`` from the keyed pseudoseed before consuming it.
    """
    if not isinstance(root, Mapping):
        raise TypeError("root must be a mapping")

    game = _require_table_fields(decoder, root.get("GAME"), name="G.GAME")
    pseudorandom = _require_table_fields(
        decoder,
        game.get("pseudorandom"),
        name="G.GAME.pseudorandom",
    )

    seed_value = pseudorandom.get("seed")
    if seed_value is None or getattr(seed_value, "kind", None) != "string":
        raise LiveRNGReplayCaptureError("live Balatro pseudorandom seed is unavailable")
    seed = str(seed_value.value)
    if not seed:
        raise LiveRNGReplayCaptureError("live Balatro pseudorandom seed is empty")

    hashed_value = pseudorandom.get("hashed_seed")
    if hashed_value is None or getattr(hashed_value, "kind", None) != "number":
        raise LiveRNGReplayCaptureError("live Balatro pseudorandom hashed_seed is unavailable")
    try:
        hashed_seed = float(hashed_value.value)
    except (TypeError, ValueError) as exc:
        raise LiveRNGReplayCaptureError("live Balatro pseudorandom hashed_seed is malformed") from exc
    expected_hash = pseudohash(seed)
    if not math.isfinite(hashed_seed) or hashed_seed.hex() != expected_hash.hex():
        raise LiveRNGReplayCaptureError(
            "live Balatro pseudorandom hashed_seed does not match the captured seed"
        )

    nodes: dict[str, float] = {}
    for key, value in pseudorandom.items():
        if key in {"seed", "hashed_seed"}:
            continue
        if not isinstance(key, str) or not key:
            raise LiveRNGReplayCaptureError("live Balatro pseudorandom node key is malformed")
        if value is None or getattr(value, "kind", None) != "number":
            raise LiveRNGReplayCaptureError(
                f"live Balatro pseudorandom node {key!r} is not numeric"
            )
        try:
            number = float(value.value)
        except (TypeError, ValueError) as exc:
            raise LiveRNGReplayCaptureError(
                f"live Balatro pseudorandom node {key!r} is malformed"
            ) from exc
        if not math.isfinite(number):
            raise LiveRNGReplayCaptureError(
                f"live Balatro pseudorandom node {key!r} is not finite"
            )
        nodes[key] = number

    return BalatroRNG(seed=seed, _nodes=nodes).snapshot()


def read_live_rng_replay_snapshot(observer) -> dict[str, Any]:
    """Capture private R5 replay authority without modifying policy observation."""
    try:
        decoder, _, root = observer._root()
    except (OSError, RuntimeError) as exc:
        raise LiveRNGReplayCaptureError("unable to read live Balatro replay authority") from exc
    return rng_replay_snapshot_from_live_memory(decoder, root)
