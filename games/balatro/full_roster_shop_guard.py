from __future__ import annotations

"""Authoritative full-roster guard for live SHOP Joker purchases.

D2 replacement is a two-checkpoint transaction: sell an incumbent, observe the
settled SHOP, then buy from the fresh state.  No policy wrapper may bypass that
contract by emitting BUY_JOKER while Balatro's public Joker area is full.
"""

from copy import copy

from games.balatro.actions import BUY_JOKER
from games.balatro.joker_edition import joker_has_negative_edition
from games.balatro.live.runtime.live_memory_autonomous_step_injected import (
    LiveMemoryInjectedSingleStepRunner,
)


def authoritative_joker_capacity(snapshot) -> tuple[int, int]:
    area = getattr(snapshot, "payload", {}).get("jokers")
    if not isinstance(area, dict):
        return 0, 0
    cards = area.get("cards")
    cards = cards if isinstance(cards, list) else []
    try:
        limit = max(0, int(area.get("limit", len(cards))))
    except (TypeError, ValueError):
        limit = len(cards)
    return len(cards), limit


def _remove_visible_jokers(state):
    safe = copy(state)
    safe.shop_jokers = []
    return safe


def install_full_roster_shop_guard() -> None:
    if getattr(LiveMemoryInjectedSingleStepRunner, "_full_roster_shop_guard_installed", False):
        return

    original_recommend_shop = LiveMemoryInjectedSingleStepRunner._recommend_shop

    def recommend_shop(self, state, snapshot):
        action, notes = original_recommend_shop(self, state, snapshot)
        if str(getattr(action, "name", "")) != BUY_JOKER:
            return action, notes
        if joker_has_negative_edition(getattr(action, "target", None)):
            return action, notes

        occupied, limit = authoritative_joker_capacity(snapshot)
        if limit <= 0 or occupied < limit:
            return action, notes

        # Re-evaluate the canonical D2 Joker child on the already translated state.
        # With authoritative occupancy preserved by the translator, any ordinary
        # Joker upgrade must be represented as JOKER_REPLACE_SELL, never BUY_JOKER.
        replacement = self.shop_arbiter._best_joker_decision(state)
        if replacement is not None and replacement.source == "JOKER_REPLACE_SELL":
            selected = replacement.decision.selected
            extra = (
                "authoritative full-roster guard: blocked direct Joker BUY at "
                f"{occupied}/{limit} slots",
                "replacement execution normalized to SELL_JOKER; follow-up BUY requires a fresh settled SHOP observation",
            )
            if selected is not None:
                extra += (
                    f"D2 replacement slot={selected.replace_index} incumbent={selected.replace_joker}",
                )
            return replacement.action, (*extra, *notes)

        # If D2 cannot construct a legal replacement, remove Joker offers from this
        # one arbitration pass and choose among voucher/booster/reroll/END_SHOP.
        # This fails closed without hiding the offers from the next fresh checkpoint.
        fallback_action, fallback_notes = original_recommend_shop(
            self,
            _remove_visible_jokers(state),
            snapshot,
        )
        if str(getattr(fallback_action, "name", "")) == BUY_JOKER:
            raise RuntimeError(
                "full-roster shop guard failed closed: non-Negative BUY_JOKER remained after Joker offers were removed"
            )
        return fallback_action, (
            f"authoritative full-roster guard: rejected direct Joker BUY at {occupied}/{limit} slots",
            "D2 produced no legal replacement; re-arbitrated this checkpoint without Joker purchases",
            *fallback_notes,
            *notes,
        )

    LiveMemoryInjectedSingleStepRunner._recommend_shop = recommend_shop
    LiveMemoryInjectedSingleStepRunner._full_roster_shop_guard_installed = True
