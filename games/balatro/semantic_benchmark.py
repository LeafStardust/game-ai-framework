from __future__ import annotations

"""Property-based semantic competence benchmark support.

This is deliberately separate from live-run win rate.  A benchmark case asks a
stable behavioral question of the production policy stack and records whether the
observed behavior satisfies that property.  Exact card/action identity should only
be asserted when mechanics require exactness.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Iterable


@dataclass(frozen=True)
class SemanticCheck:
    passed: bool
    observed: str
    expected: str
    detail: str = ""


@dataclass(frozen=True)
class SemanticBenchmarkCase:
    case_id: str
    category: str
    description: str
    evaluate: Callable[[], SemanticCheck]
    source: str = "reconstructed"


@dataclass(frozen=True)
class SemanticBenchmarkOutcome:
    case_id: str
    category: str
    description: str
    passed: bool
    observed: str
    expected: str
    detail: str
    source: str


@dataclass(frozen=True)
class SemanticCategoryScore:
    category: str
    passed: int
    total: int

    @property
    def ratio(self) -> float:
        return 1.0 if self.total == 0 else self.passed / self.total


@dataclass(frozen=True)
class SemanticBenchmarkReport:
    outcomes: tuple[SemanticBenchmarkOutcome, ...]

    @property
    def passed(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.passed)

    @property
    def total(self) -> int:
        return len(self.outcomes)

    @property
    def failed(self) -> tuple[SemanticBenchmarkOutcome, ...]:
        return tuple(outcome for outcome in self.outcomes if not outcome.passed)

    @property
    def categories(self) -> tuple[SemanticCategoryScore, ...]:
        buckets: dict[str, list[bool]] = defaultdict(list)
        for outcome in self.outcomes:
            buckets[outcome.category].append(outcome.passed)
        return tuple(
            SemanticCategoryScore(category, sum(values), len(values))
            for category, values in sorted(buckets.items())
        )

    def render(self) -> str:
        lines = [
            f"Semantic competence: {self.passed}/{self.total}",
            "",
            "Category scores:",
        ]
        for score in self.categories:
            lines.append(f"  {score.category}: {score.passed}/{score.total}")
        if self.failed:
            lines.extend(["", "Failures:"])
            for outcome in self.failed:
                lines.append(
                    f"  [{outcome.category}] {outcome.case_id}: expected {outcome.expected}; "
                    f"observed {outcome.observed}"
                )
                if outcome.detail:
                    lines.append(f"    {outcome.detail}")
        return "\n".join(lines)


def run_semantic_benchmark(
    cases: Iterable[SemanticBenchmarkCase],
) -> SemanticBenchmarkReport:
    outcomes: list[SemanticBenchmarkOutcome] = []
    seen_ids: set[str] = set()
    for case in cases:
        if case.case_id in seen_ids:
            raise ValueError(f"duplicate semantic benchmark case id: {case.case_id}")
        seen_ids.add(case.case_id)
        try:
            check = case.evaluate()
        except Exception as error:  # benchmark failures must remain visible
            check = SemanticCheck(
                passed=False,
                observed=f"{type(error).__name__}: {error}",
                expected="case executes and satisfies its semantic property",
                detail="benchmark case raised before producing a semantic result",
            )
        outcomes.append(
            SemanticBenchmarkOutcome(
                case_id=case.case_id,
                category=case.category,
                description=case.description,
                passed=bool(check.passed),
                observed=str(check.observed),
                expected=str(check.expected),
                detail=str(check.detail),
                source=str(case.source),
            )
        )
    return SemanticBenchmarkReport(tuple(outcomes))
