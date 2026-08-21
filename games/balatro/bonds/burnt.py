from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from games.balatro.bonds.model import (
    BondContribution,
    BondDevelopment,
    BondRank,
    BondRealization,
)


BURNt_BOND_ID = "burnt"

# Provisional Red/White calibration. These are weighted contribution thresholds,
# not sequential item requirements.
BURNT_RANK_THRESHOLDS: dict[BondRank, float] = {
    BondRank.R1: 8.0,
    BondRank.R2: 12.0,
    BondRank.R3: 17.0,
    BondRank.R4: 23.0,
    BondRank.R5: 30.0,
}


@dataclass(frozen=True)
class BurntBondContext:
    """External composition context needed by the Burnt Bond.

    ``target_hand`` is selected by the combined-build/poker-hand Bond layer.
    Until that layer is implemented, Burnt defaults to HIGH_CARD exactly as the
    design contract specifies.
    """

    target_hand: str | None = None
    discards_per_round: int | None = None


def _name(value: Any) -> str:
    raw = getattr(value, "name", None)
    if raw is None:
        raw = value.__class__.__name__
    return "".join(ch for ch in str(raw).lower() if ch.isalnum())


def _contains_named(values: Iterable[Any], *tokens: str) -> bool:
    normalized = {_name(value) for value in values}
    return any(
        any(token in candidate for candidate in normalized)
        for token in tokens
    )


def _owned_deck(state: Any) -> list[Any]:
    owned = getattr(state, "owned_deck", None)
    if owned is not None:
        return list(owned)
    return list(getattr(state, "deck", ()) or ())


def _blue_seal_contribution(state: Any) -> float:
    count = sum(
        1
        for card in _owned_deck(state)
        if str(getattr(card, "seal", "") or "").strip().lower() == "blue"
    )
    if count <= 0:
        return 0.0
    if count == 1:
        return 1.0
    if count == 2:
        return 3.0
    if count == 3:
        return 5.0
    return 6.0


def _target_level_contribution(state: Any, target_hand: str) -> float:
    levels = getattr(state, "hand_levels", {}) or {}
    level = int(levels.get(target_hand, 1) or 1)
    if level <= 1:
        return 0.0
    if level <= 3:
        return 1.0
    if level <= 6:
        return 3.0
    if level <= 10:
        return 5.0
    return 7.0


def _extra_discard_contribution(context: BurntBondContext) -> float:
    # Three discards is Balatro's ordinary baseline. Extra discard capacity is
    # useful Burnt infrastructure, but it is deliberately capped because it
    # improves reliability/cost rather than the engine's direct leveling rate.
    if context.discards_per_round is None:
        return 0.0
    bonus = max(0, int(context.discards_per_round) - 3)
    return float(min(3, bonus))


def _rank_for(total: float) -> tuple[BondRank, float | None]:
    rank = BondRank.LOCKED
    for candidate in (
        BondRank.R1,
        BondRank.R2,
        BondRank.R3,
        BondRank.R4,
        BondRank.R5,
    ):
        if total >= BURNT_RANK_THRESHOLDS[candidate]:
            rank = candidate
        else:
            return rank, BURNT_RANK_THRESHOLDS[candidate]
    return BondRank.R5, None


def evaluate_burnt_bond(
    state: Any,
    *,
    context: BurntBondContext | None = None,
) -> BondDevelopment:
    """Evaluate structural Burnt Bond development from public persistent state.

    Burnt Joker is the only hard unlock prerequisite. After unlock, every valid
    source feeds one shared weighted contribution pool. Telescope, Blueprint,
    Brainstorm, Blue Seals, target-hand investment, Space Joker and additional
    discard capacity are alternative/additive progression paths; none is a
    sequential rank gate.

    This evaluator intentionally does not infer actual execution quality. Until
    the realization layer consumes round telemetry, an unlocked Burnt Bond is
    reported PARTIAL rather than pretending that its first-discard prescription
    has been followed correctly.
    """

    context = context or BurntBondContext()
    target_hand = (context.target_hand or "HIGH_CARD").upper()
    jokers = list(getattr(state, "jokers", ()) or ())

    has_burnt = _contains_named(jokers, "burntjoker")
    if not has_burnt:
        return BondDevelopment(
            bond_id=BURNt_BOND_ID,
            unlocked=False,
            contribution=0.0,
            rank=BondRank.LOCKED,
            next_rank_threshold=BURNT_RANK_THRESHOLDS[BondRank.R1],
            contributions=(),
            target=target_hand,
            realization=BondRealization.DORMANT,
        )

    parts: list[BondContribution] = [BondContribution("Burnt Joker", 8.0)]

    if _contains_named(jokers, "blueprintjoker", "blueprint"):
        parts.append(BondContribution("Blueprint", 5.0))
    if _contains_named(jokers, "brainstormjoker", "brainstorm"):
        parts.append(BondContribution("Brainstorm", 5.0))
    if _contains_named(jokers, "spacejoker"):
        parts.append(BondContribution("Space Joker", 2.0))

    vouchers = list(getattr(state, "vouchers", ()) or ())
    if _contains_named(vouchers, "telescope"):
        parts.append(BondContribution("Telescope", 4.0))

    blue_seals = _blue_seal_contribution(state)
    if blue_seals > 0.0:
        parts.append(BondContribution("Blue Seal infrastructure", blue_seals))

    target_level = _target_level_contribution(state, target_hand)
    if target_level > 0.0:
        parts.append(
            BondContribution(
                f"{target_hand} permanent specialization",
                target_level,
            )
        )

    extra_discards = _extra_discard_contribution(context)
    if extra_discards > 0.0:
        parts.append(BondContribution("Extra discard capacity", extra_discards))

    total = sum(part.value for part in parts)
    rank, next_threshold = _rank_for(total)

    return BondDevelopment(
        bond_id=BURNt_BOND_ID,
        unlocked=True,
        contribution=total,
        rank=rank,
        next_rank_threshold=next_threshold,
        contributions=tuple(parts),
        target=target_hand,
        realization=BondRealization.PARTIAL,
    )
