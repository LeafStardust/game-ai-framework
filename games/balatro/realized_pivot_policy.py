from __future__ import annotations

"""Realized-maturity guard for strategy pivots.

Catalogue Gold relationships may identify a high-ceiling route, but they do not
prove that a late run has enough current progress or runway to realize it.  This
layer only suppresses already-proposed pivots that require material buildup; it
never fabricates a pivot from an otherwise non-pivot candidate.
"""

from dataclasses import dataclass, replace

from games.balatro.strategy_tree_tracker import TreeAwareStateAwareBalatroStrategyTracker


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
        # Blue is already an immediate scorer at a normal deck size.  Additional
        # deck growth raises readiness rather than being required for activation.
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


def install_realized_pivot_policy() -> None:
    if getattr(
        TreeAwareStateAwareBalatroStrategyTracker,
        "_realized_pivot_policy_installed",
        False,
    ):
        return

    original_evaluate_item = TreeAwareStateAwareBalatroStrategyTracker.evaluate_item

    def evaluate_item(self, state, item: object, *, kind: str):
        evaluation = original_evaluate_item(self, state, item, kind=kind)
        if str(kind).upper() != "JOKER" or not evaluation.pivot_candidate:
            return evaluation

        readiness = pivot_readiness(state, item)
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        # Foundation/early Convergence remains deliberately exploratory.  The
        # realized-maturity veto starts only once a late-developing route can waste
        # a meaningful fraction of the remaining Red/White runway.
        if ante < 4 or readiness.readiness >= 0.50:
            return replace(
                evaluation,
                rationale=(*evaluation.rationale, *readiness.rationale),
            )

        return replace(
            evaluation,
            pivot_candidate=False,
            value=float(evaluation.value) * max(0.25, readiness.readiness),
            rationale=(
                *evaluation.rationale,
                *readiness.rationale,
                "pivot suppressed: theoretical route requires too much unrealized buildup for the current runway",
            ),
        )

    TreeAwareStateAwareBalatroStrategyTracker.evaluate_item = evaluate_item
    TreeAwareStateAwareBalatroStrategyTracker._realized_pivot_policy_installed = True
