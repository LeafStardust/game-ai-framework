"""Balatro-compatible deterministic RNG primitives for Phase R2.

Balatro layers its own keyed ``pseudohash``/``pseudoseed`` cache over the
``math.randomseed``/``math.random`` implementation supplied by its LÖVE/LuaJIT
runtime.  This module reproduces that boundary directly instead of substituting
Python's unrelated ``random`` module.

The public owner is :class:`BalatroRNG`: every keyed draw advances only that
key's cached pseudoseed value, then reseeds a fresh LuaJIT combined-Tausworthe
state for the one random decision, matching Balatro's helper semantics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import struct
from typing import Any, Mapping


BALATRO_RNG_VERSION = "r2-rng-v1"

_U64_MASK = (1 << 64) - 1
_RANDOM_MANTISSA_MASK = (1 << 52) - 1
_ONE_BITS = 0x3FF0000000000000
_PI = math.pi
_E = math.e


def _double_bits(value: float) -> int:
    return struct.unpack("<Q", struct.pack("<d", value))[0]


def _bits_double(value: int) -> float:
    return struct.unpack("<d", struct.pack("<Q", value & _U64_MASK))[0]


def _lua_mod_one(value: float) -> float:
    """Lua-compatible ``value % 1`` for the finite and non-finite seed path."""
    if not math.isfinite(value):
        return math.nan
    return value % 1.0


def pseudohash(text: str) -> float:
    """Return Balatro's deterministic string hash as an IEEE-754 double."""
    if not isinstance(text, str):
        raise TypeError("pseudohash input must be a string")

    num = 1.0
    encoded = text.encode("utf-8")
    for index in range(len(encoded), 0, -1):
        byte = encoded[index - 1]
        if num == 0.0:
            quotient = math.copysign(math.inf, num)
        else:
            quotient = 1.1239285023 / num
        num = _lua_mod_one(quotient * byte * _PI + _PI * index)
    return num


def _round13(value: float) -> float:
    """Match Balatro's ``tonumber(string.format('%.13f', value))`` update."""
    if not math.isfinite(value):
        return value

    scale = 1e13
    tentative = math.floor(value * scale) / scale
    toward_one = math.nextafter(value, 1.0)
    # This decomposition reproduces the decimal tie behavior used by the
    # reference Balatro seed implementations without depending on locale.
    truncated = ((value * 8192.0) % 1.0) * 1_220_703_125.0
    if (
        tentative != value
        and tentative != toward_one
        and (truncated % 1.0) >= 0.5
    ):
        return (math.floor(value * scale) + 1.0) / scale
    return tentative


class LuaJITRandom:
    """LuaJIT combined-Tausworthe ``math.random`` state for one seed."""

    def __init__(self, seed: float) -> None:
        if not isinstance(seed, (int, float)) or isinstance(seed, bool):
            raise TypeError("LuaJIT RNG seed must be numeric")

        value = float(seed)
        marker = 0x11090601
        state: list[int] = []
        for _ in range(4):
            minimum = 1 << (marker & 0xFF)
            marker >>= 8
            value = value * _PI + _E
            bits = _double_bits(value)
            if bits < minimum:
                bits = (bits + minimum) & _U64_MASK
            state.append(bits)

        self._state = state
        for _ in range(10):
            self._next_u64()

    def _step(self, slot: int, *, k: int, q: int, s: int) -> int:
        value = self._state[slot]
        shifted = (((value << q) & _U64_MASK) ^ value) >> (k - s)
        mask = (_U64_MASK << (64 - k)) & _U64_MASK
        result = shifted ^ (((value & mask) << s) & _U64_MASK)
        result &= _U64_MASK
        self._state[slot] = result
        return result

    def _next_u64(self) -> int:
        result = 0
        result ^= self._step(0, k=63, q=31, s=18)
        result ^= self._step(1, k=58, q=19, s=28)
        result ^= self._step(2, k=55, q=24, s=7)
        result ^= self._step(3, k=47, q=21, s=8)
        return result & _U64_MASK

    def random(self) -> float:
        """Return the next LuaJIT random double in ``[0, 1)``."""
        bits = (self._next_u64() & _RANDOM_MANTISSA_MASK) | _ONE_BITS
        return _bits_double(bits) - 1.0

    def randint(self, minimum: int, maximum: int) -> int:
        """Return LuaJIT ``math.random(minimum, maximum)`` (inclusive)."""
        if isinstance(minimum, bool) or not isinstance(minimum, int):
            raise TypeError("minimum must be an exact integer")
        if isinstance(maximum, bool) or not isinstance(maximum, int):
            raise TypeError("maximum must be an exact integer")
        if minimum > maximum:
            raise ValueError("minimum cannot exceed maximum")
        return math.floor(self.random() * (maximum - minimum + 1)) + minimum


@dataclass
class BalatroRNG:
    """Serializable owner of Balatro's keyed pseudorandom queues."""

    seed: str | int
    _nodes: dict[str, float] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if isinstance(self.seed, bool) or not isinstance(self.seed, (str, int)):
            raise TypeError("Balatro seed must be a string or exact integer")
        if not isinstance(self._nodes, dict):
            raise TypeError("Balatro RNG nodes must be a dictionary")
        for key, value in self._nodes.items():
            if not isinstance(key, str):
                raise TypeError("Balatro RNG node keys must be strings")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError("Balatro RNG node values must be numeric")
        self.seed = str(self.seed)
        self._nodes = {key: float(value) for key, value in self._nodes.items()}
        self._hashed_seed = pseudohash(self.seed)

    def pseudoseed(self, key: str) -> float:
        """Advance and return one Balatro keyed pseudoseed value."""
        if not isinstance(key, str) or not key:
            raise ValueError("Balatro RNG key must be a non-empty string")
        if key == "seed":
            raise ValueError("unkeyed 'seed' randomness is not owned by R2")

        current = self._nodes.get(key)
        if current is None:
            current = pseudohash(key + self.seed)
        updated = _round13(_lua_mod_one(2.134453429141 + current * 1.72431234))
        self._nodes[key] = abs(updated)
        return (self._nodes[key] + self._hashed_seed) / 2.0

    def random(self, key: str) -> float:
        """Match Balatro ``pseudorandom(key)`` for one keyed decision."""
        return LuaJITRandom(self.pseudoseed(key)).random()

    def randint(self, key: str, minimum: int, maximum: int) -> int:
        """Match Balatro ``pseudorandom(key, minimum, maximum)``."""
        return LuaJITRandom(self.pseudoseed(key)).randint(minimum, maximum)

    @property
    def nodes(self) -> Mapping[str, float]:
        """Return an isolated read-only-style snapshot of keyed node values."""
        return dict(self._nodes)

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-safe, bit-preserving R2 RNG checkpoint."""
        return {
            "version": BALATRO_RNG_VERSION,
            "seed": self.seed,
            "nodes": {key: value.hex() for key, value in sorted(self._nodes.items())},
        }

    @classmethod
    def from_snapshot(cls, snapshot: Mapping[str, Any]) -> "BalatroRNG":
        """Restore a checkpoint such that the next keyed result is unchanged."""
        if not isinstance(snapshot, Mapping):
            raise TypeError("Balatro RNG snapshot must be a mapping")
        if snapshot.get("version") != BALATRO_RNG_VERSION:
            raise ValueError("unsupported Balatro RNG snapshot version")

        seed = snapshot.get("seed")
        nodes = snapshot.get("nodes")
        if not isinstance(seed, str):
            raise TypeError("Balatro RNG snapshot seed must be a string")
        if not isinstance(nodes, Mapping):
            raise TypeError("Balatro RNG snapshot nodes must be a mapping")

        restored: dict[str, float] = {}
        for key, value in nodes.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise TypeError("Balatro RNG snapshot nodes must map strings to hex floats")
            try:
                restored[key] = float.fromhex(value)
            except ValueError as exc:
                raise ValueError(f"invalid Balatro RNG node value for {key!r}") from exc
        return cls(seed=seed, _nodes=restored)
