from __future__ import annotations

from dataclasses import dataclass

from .live_memory_observer import _number, _table_fields


@dataclass(frozen=True)
class LiveShopRerollTerms:
    """Public current-shop reroll terms read from Balatro process memory."""

    cost: float
    free_rerolls: int


def read_live_shop_reroll_terms(observer) -> LiveShopRerollTerms:
    """Read the current reroll cost/free-reroll count without writing game state."""

    decoder, _, root = observer._root()
    game = _table_fields(decoder, root.get("GAME"))
    current_round = _table_fields(decoder, game.get("current_round"))

    cost = _number(current_round.get("reroll_cost"))
    free_rerolls = _number(current_round.get("free_rerolls"))
    if cost is None:
        raise RuntimeError("live Balatro reroll_cost is unavailable")

    return LiveShopRerollTerms(
        cost=float(cost),
        free_rerolls=int(free_rerolls or 0),
    )
