"""Strict canonical translation for live Tarot/Planet generation eligibility."""

from __future__ import annotations

from typing import Any

from games.balatro.live.voucher_generation_pool_translation import (
    translate_voucher_generation_pool_payload,
)
from games.balatro.state import BalatroState


_REQUIRED_TYPES = ("Tarot", "Planet")
_REQUIRED_FIELDS = {
    "type",
    "key",
    "cost",
    "unlocked",
    "no_pool_flag",
    "yes_pool_flag",
    "softlock",
    "hand_type",
}


def _exact_nonnegative_rate(value: Any, default: float) -> float:
    """Return an exact live shop type rate or the normal-mode base default.

    Missing/malformed reads never infer Voucher ownership. If a Merchant/Tycoon
    Voucher is observed, the capability layer compares this translated value with
    ownership and fails closed when the live rate was unavailable or inconsistent.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    rate = float(value)
    return rate if rate >= 0.0 else default


def translate_consumable_generation_pool_payload(
    state: BalatroState,
    payload: dict[str, Any],
) -> None:
    """Install authoritative ordinary generation catalogues and shop type rates.

    Voucher translation shares this already-canonical live-generation translation
    boundary so the main state translator cannot accidentally install Tarot/Planet
    eligibility without also validating the ordered Voucher catalogue.

    Tarot/Planet catalogue translation is all-or-nothing. A claimed observation
    with either type missing, any malformed record, duplicate key, or unexpected
    record field is rejected as unobserved instead of silently dropping the bad
    fragment. The scalar normal-shop type rates are independent persistent
    ``G.GAME`` fields and are translated even when generation catalogues are absent.
    """
    translate_voucher_generation_pool_payload(state, payload)

    state.tarot_rate = _exact_nonnegative_rate(payload.get("tarot_rate"), 4.0)
    state.planet_rate = _exact_nonnegative_rate(payload.get("planet_rate"), 4.0)

    state.consumable_generation_pool_observed = False
    state.consumable_generation_pools = {}

    if payload.get("consumable_generation_pool_observed") is not True:
        return
    pools = payload.get("consumable_generation_pools")
    if not isinstance(pools, dict) or set(pools) != set(_REQUIRED_TYPES):
        return

    normalized: dict[str, list[dict]] = {}
    seen: set[str] = set()
    for card_type in _REQUIRED_TYPES:
        records = pools.get(card_type)
        if not isinstance(records, list):
            return
        copied: list[dict] = []
        for record in records:
            if not isinstance(record, dict) or set(record) != _REQUIRED_FIELDS:
                return
            if record.get("type") != card_type:
                return
            key = record.get("key")
            if not isinstance(key, str) or not key or key in seen:
                return
            seen.add(key)
            cost = record.get("cost")
            if type(cost) is not int or cost < 0:
                return
            unlocked = record.get("unlocked")
            if unlocked is not None and not isinstance(unlocked, bool):
                return
            for flag_name in ("no_pool_flag", "yes_pool_flag"):
                flag = record.get(flag_name)
                if flag is not None and (not isinstance(flag, str) or not flag):
                    return
            softlock = record.get("softlock")
            if not isinstance(softlock, bool):
                return
            hand_type = record.get("hand_type")
            if hand_type is not None and (not isinstance(hand_type, str) or not hand_type):
                return
            if card_type == "Tarot" and (softlock or hand_type is not None):
                return
            if card_type == "Planet" and softlock and hand_type is None:
                return
            copied.append(dict(record))
        normalized[card_type] = copied

    state.consumable_generation_pools = normalized
    state.consumable_generation_pool_observed = True
