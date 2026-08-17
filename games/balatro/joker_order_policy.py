from __future__ import annotations

import copy
from dataclasses import dataclass
from itertools import combinations, permutations

from games.balatro.actions import REORDER_JOKERS, BalatroAction
from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
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

    Balatro resolves independent Joker effects from left to right. Exhaustively
    scoring at most five ordinary slots is both cheap and more reliable than a
    hand-written additive/XMult sort: it also captures validated Blueprint and
    Brainstorm copy targets. At BLIND_SELECT, each permutation additionally
    projects Ceremonial Dagger's mandatory right-neighbour sacrifice.
    """

    STABLE_PHASES = frozenset({"BLIND_SELECT", "SELECTING_HAND", "SHOP"})

    def __init__(
        self,
        *,
        evaluator: JokerBuildValueEvaluator | None = None,
        minimum_improvement: float = 0.0,
    ) -> None:
        self.evaluator = evaluator or JokerBuildValueEvaluator()
        self.projector = LiveJokerScoreProjector(self.evaluator.scorer)
        self.minimum_improvement = max(0.0, float(minimum_improvement))

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
        phase = str(phase or getattr(state, "phase", ""))
        jokers = tuple(getattr(state, "jokers", ()) or ())
        if phase not in self.STABLE_PHASES or len(jokers) < 2:
            return None

        current = tuple(range(len(jokers)))
        current_score, current_notes = self._score(state, current, phase=phase)
        best_permutation = current
        best_score = current_score
        best_notes = current_notes

        if len(current) <= 6:
            candidates = permutations(current)
        else:
            # Negative editions can exceed the ordinary five-slot cap. A complete
            # factorial search would then be an avoidable latency hazard; every
            # one-swap neighbour still permits copy targeting, Dagger feeding, and
            # additive/XMult pair correction in successive settled steps.
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
            if score > best_score:
                best_permutation = permutation
                best_score = score
                best_notes = notes

        improvement = best_score - current_score
        if best_permutation == current or improvement <= self.minimum_improvement:
            return None

        labels = tuple(type(jokers[index]).__name__ for index in best_permutation)
        return JokerOrderDecision(
            permutation=best_permutation,
            current_score=current_score,
            ordered_score=best_score,
            rationale=(
                f"whole-build Joker-order score {current_score:.3f}->{best_score:.3f}",
                f"recommended order={labels}",
                *best_notes,
            ),
        )
