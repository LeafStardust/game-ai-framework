from __future__ import annotations

"""State-dependent relationship promotions learned from the latest five-run batch.

The production state-aware/tree trackers consume promotions through their existing
conditional relationship surfaces.  A few public callers and contract tests still
construct the flat ``BalatroStrategyTracker`` directly, so this module also gives
that exact base class a non-recursive post-processing path.  Subclasses are never
post-processed here.
"""

from dataclasses import replace

from games.balatro import strategy_conditional_relationships as conditional
from games.balatro.strategy import (
    AVAILABLE,
    CANDIDATE,
    COMMITTED,
    GOLD,
    HIGHLIGHTED,
    MATURE,
    SILVER,
    BalatroStrategyTracker,
)


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _item_tokens(item: object) -> frozenset[str]:
    values = (
        type(item).__name__,
        getattr(item, "name", ""),
        getattr(item, "label", ""),
        getattr(item, "ability_name", ""),
    )
    return frozenset(token for value in values if (token := _normalize(value)))


def _owned_tokens(state) -> frozenset[str]:
    values: set[str] = set()
    for joker in getattr(state, "jokers", ()) or ():
        values.update(_item_tokens(joker))
    return frozenset(values)


def _throwback_item_scaled(item: object) -> bool:
    public = getattr(item, "public_state", None)
    value = getattr(item, "x_mult", None)
    if value is None and isinstance(public, dict):
        value = public.get("x_mult", 1.0)
    elif value is None and public is not None:
        value = getattr(public, "x_mult", 1.0)
    try:
        return float(value if value is not None else 1.0) > 1.0 + 1e-12
    except (TypeError, ValueError):
        return False


def _promotion(state, strategy_id: str, item: object) -> str | None:
    tokens = _item_tokens(item)
    owned = _owned_tokens(state)
    if (
        strategy_id == "ten_four"
        and tokens & {"walkietalkie", "walkietalkiejoker"}
        and owned & {"evensteven", "evenstevenjoker"}
    ):
        return GOLD
    if (
        strategy_id == "throwback"
        and tokens & {"throwback", "throwbackjoker"}
        and _throwback_item_scaled(item)
    ):
        return GOLD
    return None


def _status_for_score(tracker: BalatroStrategyTracker, state, score: float) -> str:
    config = tracker._config(state)
    thresholds = (
        (MATURE, tracker._number(config, "mature_threshold", 16.0)),
        (COMMITTED, tracker._number(config, "commit_threshold", 9.0)),
        (HIGHLIGHTED, tracker._number(config, "highlight_threshold", 3.5)),
        (CANDIDATE, tracker._number(config, "candidate_threshold", 1.5)),
    )
    return next((name for name, floor in thresholds if score >= floor), AVAILABLE)


def _promoted_count(state, strategy_id: str) -> int:
    return sum(
        1
        for joker in getattr(state, "jokers", ()) or ()
        if _promotion(state, strategy_id, joker) == GOLD
    )


def install_latest_five_run_relationship_promotions() -> None:
    if getattr(conditional, "_latest_five_run_relationship_promotions_installed", False):
        return

    # Production state-aware owned-item assessment.
    original_view_relationship = conditional._ConditionalDefinitionView.relationship_for

    def relationship_for(self, item: object, *, kind: str) -> str:
        if str(kind).upper() == "JOKER":
            promoted = _promotion(self._state, self._definition.strategy_id, item)
            if promoted is not None:
                return promoted
        return original_view_relationship(self, item, kind=kind)

    conditional._ConditionalDefinitionView.relationship_for = relationship_for

    # Production state-aware candidate relationship mapping.
    original_relationships_for = conditional.StateAwareBalatroStrategyTracker._relationships_for

    def _relationships_for(self, item: object, *, kind: str) -> dict[str, str]:
        found = original_relationships_for(self, item, kind=kind)
        if str(kind).upper() != "JOKER" or self._relationship_state is None:
            return found
        for strategy_id in self.definitions:
            promoted = _promotion(self._relationship_state, strategy_id, item)
            if promoted is not None:
                found[strategy_id] = promoted
        return found

    conditional.StateAwareBalatroStrategyTracker._relationships_for = _relationships_for

    # Flat/base tracker compatibility.  This is deliberately exact-type-only: tree
    # and state-aware subclasses already resolve the relationship above and must not
    # be post-processed a second time.
    original_assess = BalatroStrategyTracker.assess

    def assess(self, state):
        assessments = original_assess(self, state)
        if type(self) is not BalatroStrategyTracker:
            return assessments

        promoted = []
        for assessment in assessments:
            count = _promoted_count(state, assessment.strategy_id)
            if count <= 0:
                promoted.append(assessment)
                continue
            # Static catalogue entries for these realized relationships are Silver.
            # Replace exactly one Silver contribution per promoted owned Joker with
            # the active Gold contribution, preserving effectiveness/base score.
            gold_delta = self.relationship_score(state, GOLD) - self.relationship_score(state, SILVER)
            score = float(assessment.score) + count * gold_delta * float(assessment.effectiveness)
            promoted.append(
                replace(
                    assessment,
                    score=score,
                    status=_status_for_score(self, state, score),
                    gold_owned=int(assessment.gold_owned) + count,
                    silver_owned=max(0, int(assessment.silver_owned) - count),
                    rationale=(
                        *assessment.rationale,
                        f"realized relationship promotion: {count} Silver->Gold component(s)",
                    ),
                )
            )
        return tuple(sorted(promoted, key=lambda value: (-value.score, value.strategy_id)))

    BalatroStrategyTracker.assess = assess

    original_evaluate_item = BalatroStrategyTracker.evaluate_item

    def evaluate_item(self, state, item, *, kind: str):
        result = original_evaluate_item(self, state, item, kind=kind)
        if type(self) is not BalatroStrategyTracker or str(kind).upper() != "JOKER":
            return result
        strategy_id = getattr(result, "strategy_id", None)
        if strategy_id is None or _promotion(state, strategy_id, item) != GOLD:
            return result
        if getattr(result, "tier", None) == GOLD:
            return result
        return replace(
            result,
            tier=GOLD,
            rationale=(
                *result.rationale,
                "realized relationship promotion exposes Gold tier to flat-tracker consumers",
            ),
        )

    BalatroStrategyTracker.evaluate_item = evaluate_item
    conditional._latest_five_run_relationship_promotions_installed = True
