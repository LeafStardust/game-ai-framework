from __future__ import annotations

"""Allow intentional pre-blind Joker cleanup at the settled blind-select screen.

Pre-round policies such as exhausted Popcorn/Ice Cream cleanup and Riff-Raff slot
cycling deliberately emit SELL_JOKER before SELECT_BLIND.  Balatro permits selling
Jokers there, but the injected dispatcher historically admitted sales only in the
shop, open packs, or Verdant Leaf.  Keep the existing dispatcher unchanged for all
other phases and provide the same semantic postcondition for BLIND_SELECT sales.
"""

from games.balatro.actions import SELL_JOKER

from .action_dispatcher import (
    LiveInjectedActionResult,
    LiveMemoryInjectedActionDispatcher,
    _area_cards,
    _area_item,
    _target_index,
)


def install_preblind_joker_sale_support() -> None:
    if getattr(
        LiveMemoryInjectedActionDispatcher,
        "_preblind_joker_sale_support_installed",
        False,
    ):
        return

    original_dispatch = LiveMemoryInjectedActionDispatcher.dispatch

    def dispatch(self, action, *, state=None, snapshot=None):
        before = snapshot or self.observer.observe()
        if action.name != SELL_JOKER or before.phase != "BLIND_SELECT":
            return original_dispatch(
                self,
                action,
                state=state,
                snapshot=before,
            )

        index = _target_index(action.target)
        item = _area_item(before, "jokers", index)
        before_count = len(_area_cards(before, "jokers"))
        target_live_id = item.get("live_id")
        self.bridge.sell_joker(index)

        def sale_settled(value):
            after_jokers = _area_cards(value, "jokers")
            if (
                value.sequence <= before.sequence
                or value.phase != "BLIND_SELECT"
                or not value.state_complete
                or len(after_jokers) != before_count - 1
            ):
                return False
            if target_live_id is None:
                return True
            return all(
                not isinstance(joker, dict)
                or joker.get("live_id") != target_live_id
                for joker in after_jokers
            )

        after = self._wait(before, sale_settled, "pre-blind joker sale")
        return LiveInjectedActionResult(
            action,
            before,
            after,
            {"area_index": index, "item": item, "sale_context": "BLIND_SELECT"},
        )

    LiveMemoryInjectedActionDispatcher.dispatch = dispatch
    LiveMemoryInjectedActionDispatcher._preblind_joker_sale_support_installed = True
