from __future__ import annotations

from dataclasses import dataclass

from .live_memory_observer import _exact_integral_number, _table_fields


@dataclass(frozen=True)
class LiveShopRerollTerms:
    """Exact public current-shop reroll terms read from Balatro process memory."""

    cost: int
    free_rerolls: int


def read_live_shop_reroll_terms(observer) -> LiveShopRerollTerms:
    """Read exact current reroll cost/free-reroll count without writing game state.

    REROLL_SHOP legality and execution must never infer integer economics from a
    malformed or fractional Lua value. Missing free-reroll state is also treated
    as unavailable rather than silently substituted with zero.
    """

    decoder, _, root = observer._root()
    game = _table_fields(decoder, root.get("GAME"))
    current_round = _table_fields(decoder, game.get("current_round"))

    cost = _exact_integral_number(current_round.get("reroll_cost"), minimum=0)
    free_rerolls = _exact_integral_number(
        current_round.get("free_rerolls"),
        minimum=0,
    )
    if cost is None:
        raise RuntimeError("live Balatro reroll_cost is not an exact nonnegative integer")
    if free_rerolls is None:
        raise RuntimeError("live Balatro free_rerolls is not an exact nonnegative integer")

    return LiveShopRerollTerms(
        cost=cost,
        free_rerolls=free_rerolls,
    )