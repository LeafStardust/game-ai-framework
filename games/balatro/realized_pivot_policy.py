from __future__ import annotations

"""Realized-maturity measurements for buildup-sensitive Bond pivots.

The canonical Bond/composition layer can consume these measurements when judging
whether a candidate engine has enough current progress and runway.  This module
contains no installer or dependency on the retired categorical strategy tracker.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PivotReadiness:
    readiness: float
    buildup_cost: float
    rationale: tuple[str, ...]


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _token(item: object) -> str:
    return _normalize(
        getattr(item, "name", None)
        or getattr(item, "label", None)
        or getattr(item, "ability_name", None)
        or type(item).__name__
    )


def _owned_tokens(state) -> set[str]:
    values: set[str] = set()
    for joker in getattr(state, "jokers", ()) or ():
        token = _token(joker)
        if token:
            values.add(token)
            if token.endswith("joker"):
                values.add(token[:-5])
    return values


def _deck_size(state) -> int:
    owned = getattr(state, "owned_deck", None)
    try:
        return len(owned if owned is not None else getattr(state, "deck", ()) or ())
    except TypeError:
        return 0


def pivot_readiness(state, item: object) -> PivotReadiness:
    """Return current-state readiness for known buildup-sensitive pivot engines."""
    token = _token(item)
    ante = max(1, int(getattr(state, "ante", 1) or 1))

    if token in {"runner", "runnerjoker"}:
        counts = getattr(state, "hand_play_counts", {}) or {}
        straight_plays = int(counts.get("STRAIGHT", counts.get("Straight", 0)) or 0)
        target = max(2, ante - 1)
        readiness = min(1.0, straight_plays / float(target))
        return PivotReadiness(
            readiness=readiness,
            buildup_cost=1.0 - readiness,
            rationale=(
                f"Runner realized pivot readiness={readiness:.3f}",
                f"Straight history={straight_plays}; late-pivot reference={target}",
            ),
        )

    if token in {"hologram", "hologramjoker"}:
        owned = _owned_tokens(state)
        generator = any(
            value in owned
            for value in {"certificate", "certificatejoker", "marble", "marblejoker"}
        )
        readiness = 0.75 if generator else (0.25 if ante >= 4 else 0.50)
        return PivotReadiness(
            readiness=readiness,
            buildup_cost=1.0 - readiness,
            rationale=(
                f"Hologram realized pivot readiness={readiness:.3f}",
                f"card generator already owned={'yes' if generator else 'no'}",
            ),
        )

    if token in {"bluejoker"}:
        cards = _deck_size(state)
        readiness = min(1.0, max(0.60, cards / 60.0)) if cards > 0 else 0.60
        return PivotReadiness(
            readiness=readiness,
            buildup_cost=max(0.0, 1.0 - readiness),
            rationale=(
                f"Blue Joker realized pivot readiness={readiness:.3f}",
                f"owned deck size={cards}",
            ),
        )

    if token in {"bull", "bulljoker", "bootstraps", "bootstrapsjoker"}:
        money = max(0, int(getattr(state, "money", 0) or 0))
        target = max(10.0, float(ante * 5))
        readiness = min(1.0, money / target)
        return PivotReadiness(
            readiness=readiness,
            buildup_cost=1.0 - readiness,
            rationale=(
                f"cash-scoring realized pivot readiness={readiness:.3f}",
                f"cash=${money}; Ante {ante} immediate-readiness reference=${target:.0f}",
            ),
        )

    return PivotReadiness(
        readiness=1.0,
        buildup_cost=0.0,
        rationale=("candidate has no registered historical-buildup pivot penalty",),
    )
