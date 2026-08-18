from __future__ import annotations

import copy
from dataclasses import dataclass
from itertools import combinations, permutations

from games.balatro.actions import REORDER_JOKERS, BalatroAction
from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.joker_edition import joker_has_negative_edition
from games.balatro.live.joker_projection import LiveJokerScoreProjector


@dataclass(frozen=True)
class JokerOrderDecision:
    permutation: tuple[int, ...]
    current_score: float
    ordered_score: float
    rationale: tuple[str, ...]

    def to_action(self) -> BalatroAction:
        return BalatroAction(REORDER_JOKERS, target=self.permutation)


class JokerOrderPolicy:
    """Choose an auditable whole-build Joker permutation.

    Balatro resolves independent Joker effects from left to right. Small boards
    can be searched exhaustively; larger boards use bounded one-swap neighbours
    and converge over successive settled checkpoints. At BLIND_SELECT, ordinary
    scoring order is deferred until the hand is visible. Only Ceremonial Dagger
    justifies delaying blind selection for a pre-blind rearrangement.
    """

    STABLE_PHASES = frozenset({"BLIND_SELECT", "SELECTING_HAND", "SHOP"})
    MAX_EXHAUSTIVE_JOKERS = 4

    def __init__(
        self,
        *,
        evaluator: JokerBuildValueEvaluator | None = None,
        minimum_improvement: float = 0.0,
    ) -> None:
        self.evaluator = evaluator or JokerBuildValueEvaluator()
        self.projector = LiveJokerScoreProjector(self.evaluator.scorer)
        self.minimum_improvement = max(0.0, float(minimum_improvement))
        self.last_negative_retention_diagnostics: tuple[str, ...] = ()

    @staticmethod
    def _project_dagger_sacrifices(state) -> tuple[str, ...]:
        notes: list[str] = []
        index = 0
        while index < len(state.jokers):
            dagger = state.jokers[index]
            if type(dagger).__name__ != "DaggerJoker" or index + 1 >= len(state.jokers):
                index += 1
                continue

            target = state.jokers[index + 1]
            sell_value = max(
                0,
                int(
                    getattr(
                        target,
                        "sell_value",
                        getattr(target, "sell_cost", 0),
                    )
                    or 0
                ),
            )
            dagger.mult = int(getattr(dagger, "mult", 0) or 0) + 2 * sell_value
            removed = state.jokers.pop(index + 1)
            notes.append(
                f"projected Ceremonial Dagger sacrifice={type(removed).__name__} "
                f"for +{2 * sell_value} Mult"
            )
            index += 1
        return tuple(notes)

    @staticmethod
    def _dagger_sacrifice_targets(jokers) -> tuple[object, ...]:
        """Return the targets destroyed by the supplied resolved Joker order."""

        projected = list(jokers)
        targets: list[object] = []
        index = 0
        while index < len(projected):
            if (
                type(projected[index]).__name__ == "DaggerJoker"
                and index + 1 < len(projected)
            ):
                targets.append(projected.pop(index + 1))
            index += 1
        return tuple(targets)

    def _active_dagger_strategy(self, state) -> bool:
        tracker = getattr(self.evaluator, "strategy_tracker", None)
        if tracker is None:
            return False
        resolution = tracker.observe(state)
        if str(getattr(resolution, "active_status", "")) not in {
            "HIGHLIGHTED",
            "COMMITTED",
            "MATURE",
        }:
            return False
        strategy_id = getattr(resolution, "dominant_strategy_id", None)
        if strategy_id is None:
            return False
        topology = getattr(tracker, "topology", None)
        path = (
            tuple(topology.path(strategy_id))
            if topology is not None
            else (str(strategy_id),)
        )
        return "dagger_sacrifice" in path

    def _negative_dagger_targets(self, jokers, permutation) -> tuple[object, ...]:
        ordered = [jokers[index] for index in permutation]
        return tuple(
            target
            for target in self._dagger_sacrifice_targets(ordered)
            if joker_has_negative_edition(target)
        )

    def _score(self, state, permutation, *, phase: str) -> tuple[float, tuple[str, ...]]:
        projected = copy.deepcopy(state)
        projected.jokers = [projected.jokers[index] for index in permutation]
        notes: tuple[str, ...] = ()
        if phase == "BLIND_SELECT":
            notes = self._project_dagger_sacrifices(projected)

        totals: list[float] = []
        for hand, template_cards in self.evaluator._scoring_probes(projected):
            probe = copy.deepcopy(projected)
            cards = copy.deepcopy(list(template_cards))
            probe.hand = copy.deepcopy(cards)
            try:
                result = self.projector.score(
                    hand,
                    probe,
                    cards,
                    resolve_random_effects=False,
                )
            except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
                continue
            totals.append(float(result.score.total))
        return (sum(totals) / len(totals) if totals else 0.0), notes

    def recommend(self, state, *, phase: str | None = None) -> JokerOrderDecision | None:
        self.last_negative_retention_diagnostics = ()
        phase = str(phase or getattr(state, "phase", ""))
        jokers = tuple(getattr(state, "jokers", ()) or ())
        if phase not in self.STABLE_PHASES or len(jokers) < 2:
            return None
        if phase == "BLIND_SELECT" and not any(
            type(joker).__name__ == "DaggerJoker" for joker in jokers
        ):
            # Selecting the blind is time-sensitive and no other Joker resolves
            # before the hand appears. Scoring order can be optimized immediately
            # afterward without blocking the round transition.
            return None

        current = tuple(range(len(jokers)))
        current_score, current_notes = self._score(state, current, phase=phase)
        active_dagger_strategy = (
            phase == "BLIND_SELECT" and self._active_dagger_strategy(state)
        )
        current_negative_targets = (
            self._negative_dagger_targets(jokers, current)
            if phase == "BLIND_SELECT"
            else ()
        )
        current_negative_count = (
            0 if active_dagger_strategy else len(current_negative_targets)
        )
        if active_dagger_strategy and current_negative_targets:
            self.last_negative_retention_diagnostics = (
                "Negative retention exception=ACTIVE_DAGGER_STRATEGY_INTENTIONAL_SACRIFICE",
                "active Dagger strategy accepts projected Negative target(s)="
                + ", ".join(type(target).__name__ for target in current_negative_targets),
            )
        best_permutation = current
        best_score = current_score
        best_notes = current_notes
        best_negative_count = current_negative_count

        if len(current) <= self.MAX_EXHAUSTIVE_JOKERS:
            candidates = permutations(current)
        else:
            # Negative editions can exceed the ordinary slot cap. Every one-swap
            # neighbour still permits copy targeting, Dagger feeding, and
            # additive/XMult correction without factorial latency.
            candidates = (
                tuple(
                    current[right] if index == left else
                    current[left] if index == right else
                    current[index]
                    for index in current
                )
                for left, right in combinations(current, 2)
            )

        for permutation in candidates:
            if permutation == current:
                continue
            score, notes = self._score(state, permutation, phase=phase)
            negative_targets = (
                self._negative_dagger_targets(jokers, permutation)
                if phase == "BLIND_SELECT"
                else ()
            )
            negative_count = 0 if active_dagger_strategy else len(negative_targets)
            if negative_count < best_negative_count or (
                negative_count == best_negative_count and score > best_score
            ):
                best_permutation = permutation
                best_score = score
                best_notes = notes
                best_negative_count = negative_count

        improvement = best_score - current_score
        retention_improved = best_negative_count < current_negative_count
        if best_permutation == current or (
            not retention_improved and improvement <= self.minimum_improvement
        ):
            return None

        labels = tuple(type(jokers[index]).__name__ for index in best_permutation)
        selected_negative_targets = (
            self._negative_dagger_targets(jokers, best_permutation)
            if phase == "BLIND_SELECT"
            else ()
        )
        # The early diagnostic describes the current order. Once a different
        # permutation is selected, report only the selected order's outcome.
        self.last_negative_retention_diagnostics = ()
        retention_notes: list[str] = []
        if retention_improved:
            retention_notes.extend(
                (
                    "Negative retention result=PROTECTED_FROM_DAGGER_SACRIFICE",
                    "Negative Dagger targets "
                    f"{len(current_negative_targets)}->{len(selected_negative_targets)}; "
                    "retention safety overrides ordinary score ordering",
                )
            )
            self.last_negative_retention_diagnostics = tuple(retention_notes)
        elif active_dagger_strategy and selected_negative_targets:
            retention_notes.append(
                "Negative retention exception=ACTIVE_DAGGER_STRATEGY_INTENTIONAL_SACRIFICE"
            )
            self.last_negative_retention_diagnostics = tuple(retention_notes)
        return JokerOrderDecision(
            permutation=best_permutation,
            current_score=current_score,
            ordered_score=best_score,
            rationale=(
                f"whole-build Joker-order score {current_score:.3f}->{best_score:.3f}",
                f"recommended order={labels}",
                *retention_notes,
                *best_notes,
            ),
        )
