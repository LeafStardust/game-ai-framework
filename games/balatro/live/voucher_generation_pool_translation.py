"""Strict canonical translation for live Voucher-generation eligibility."""

from __future__ import annotations

from typing import Any

from games.balatro.state import BalatroState


_REQUIRED_FIELDS = {
    "key",
    "cost",
    "unlocked",
    "requires",
    "no_pool_flag",
    "yes_pool_flag",
    "eligible",
}


def translate_voucher_generation_pool_payload(
    state: BalatroState,
    payload: dict[str, Any],
) -> None:
    """Install one authoritative ordered Voucher catalogue or leave unobserved."""
    state.voucher_generation_pool_observed = False
    state.voucher_generation_pool = []

    if payload.get("voucher_generation_pool_observed") is not True:
        return
    records = payload.get("voucher_generation_pool")
    if not isinstance(records, list) or not records:
        return

    copied: list[dict] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != _REQUIRED_FIELDS:
            return
        key = record.get("key")
        if not isinstance(key, str) or not key.startswith("v_") or key in seen:
            return
        seen.add(key)
        cost = record.get("cost")
        if type(cost) is not int or cost < 0:
            return
        unlocked = record.get("unlocked")
        if unlocked is not None and not isinstance(unlocked, bool):
            return
        requires = record.get("requires")
        if not isinstance(requires, list):
            return
        if any(not isinstance(item, str) or not item.startswith("v_") for item in requires):
            return
        if len(requires) != len(set(requires)):
            return
        for flag_name in ("no_pool_flag", "yes_pool_flag"):
            flag = record.get(flag_name)
            if flag is not None and (not isinstance(flag, str) or not flag):
                return
        if not isinstance(record.get("eligible"), bool):
            return
        copied.append(
            {
                "key": key,
                "cost": cost,
                "unlocked": unlocked,
                "requires": list(requires),
                "no_pool_flag": record.get("no_pool_flag"),
                "yes_pool_flag": record.get("yes_pool_flag"),
                "eligible": record["eligible"],
            }
        )

    state.voucher_generation_pool = copied
    state.voucher_generation_pool_observed = True
