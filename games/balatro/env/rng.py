"""Balatro-compatible deterministic RNG primitives for Phase R2.

Balatro layers its own keyed ``pseudohash``/``pseudoseed`` cache over the
``math.randomseed``/``math.random`` implementation supplied by its LÖVE/LuaJIT
runtime. This module reproduces that boundary directly instead of substituting
Python's unrelated ``random`` module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import struct
from typing import Any, Callable, Mapping, MutableSequence, TypeVar


BALATRO_RNG_VERSION = "r2-rng-v1"

_U64_MASK = (1 << 64) - 1
_RANDOM_MANTISSA_MASK = (1 << 52) - 1
_ONE_BITS = 0x3FF0000000000000
_PI = math.pi
_E = math.e
_T = TypeVar("_T")


def _double_bits(value: float) -> int:
    return struct.unpack("<Q", struct.pack("<d", value))[0]


def _bits_double(value: int) -> float:
    return struct.unpack("<d", struct.pack("<Q", value & _U64_MASK))[0]


def _lua_mod_one(value: float) -> float:
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
        quotient = math.copysign(math.inf, num) if num == 0.0 else 1.1239285023 / num
        num = _lua_mod_one(quotient * byte * _PI + _PI * index)
    return num


def _round13(value: float) -> float:
    """Match Balatro's ``tonumber(string.format('%.13f', value))`` update."""
    if not math.isfinite(value):
        return value

    scale = 1e13
    tentative = math.floor(value * scale) / scale
    toward_one = math.nextafter(value, 1.0)
    truncated = ((value * 8192.0) % 1.0) * 1_220_703_125.0
    if tentative != value and tentative != toward_one and (truncated % 1.0) >= 0.5:
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
        bits = (self._next_u64() & _RANDOM_MANTISSA_MASK) | _ONE_BITS
        return _bits_double(bits) - 1.0

    def randint(self, minimum: int, maximum: int) -> int:
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

    def generator(self, key: str) -> LuaJITRandom:
        """Advance one keyed pseudoseed and return its freshly seeded LuaJIT RNG.

        Balatro's helpers such as ``pseudoshuffle`` call ``pseudoseed`` once,
        then consume several ``math.random`` results from that single seeded
        state. Keeping this operation explicit prevents accidentally advancing
        the Balatro node once per swap.
        """
        return LuaJITRandom(self.pseudoseed(key))

    def random(self, key: str) -> float:
        return self.generator(key).random()

    def randint(self, key: str, minimum: int, maximum: int) -> int:
        return self.generator(key).randint(minimum, maximum)

    def shuffle_in_place(
        self,
        values: MutableSequence[_T],
        key: str,
        *,
        sort_key: Callable[[_T], Any] | None = None,
    ) -> None:
        """Match Balatro ``pseudoshuffle(list, pseudoseed(key))``.

        Vanilla sorts card-like values by their stable ``sort_id`` before the
        Fisher-Yates swaps. The caller must provide the corresponding exact
        ordering key when that pre-sort is required; R2 does not guess one.
        """
        if not isinstance(values, MutableSequence):
            raise TypeError("shuffle target must be a mutable sequence")
        if sort_key is not None:
            values[:] = sorted(values, key=sort_key)

        rng = self.generator(key)
        for size in range(len(values), 1, -1):
            other = rng.randint(1, size) - 1
            current = size - 1
            values[current], values[other] = values[other], values[current]

    def pseudorandom_element_index(self, length: int, key: str) -> int:
        """Return the zero-based Lua-array index chosen by ``pseudorandom_element``.

        Vanilla receives ``pseudoseed(key)`` as a numeric seed, calls
        ``math.randomseed(seed)``, materializes the array's numeric keys, sorts
        those keys ascending, and performs exactly one ``math.random(#keys)``.
        For a dense Lua array that is therefore one inclusive integer draw from
        ``1..length`` on the freshly seeded LuaJIT generator. No Fisher-Yates
        shuffle occurs in ``pseudorandom_element`` itself.
        """
        if isinstance(length, bool) or not isinstance(length, int):
            raise TypeError("pseudorandom element length must be an exact integer")
        if length <= 0:
            raise ValueError("pseudorandom element requires a non-empty sequence")

        rng = self.generator(key)
        return rng.randint(1, length) - 1

    @property
    def nodes(self) -> Mapping[str, float]:
        return dict(self._nodes)

    def snapshot(self) -> dict[str, Any]:
        return {
            "version": BALATRO_RNG_VERSION,
            "seed": self.seed,
            "nodes": {key: value.hex() for key, value in sorted(self._nodes.items())},
        }

    @classmethod
    def from_snapshot(cls, snapshot: Mapping[str, Any]) -> "BalatroRNG":
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
