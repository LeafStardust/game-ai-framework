from __future__ import annotations

import argparse
import importlib
import inspect
import pkgutil
from collections import Counter
from dataclasses import dataclass

import games.balatro.jokers as joker_package
from games.balatro.joker import Joker

from .joker_lifecycle import LifecycleJokerBehaviorAnalyzer
from .joker_semantics import SemanticEffectDescriptor


COVERED = "COVERED"
PARTIAL = "PARTIAL"
OPAQUE = "OPAQUE"
PARAMETERIZED = "PARAMETERIZED"
ERROR = "ERROR"
UNANALYZED = "UNANALYZED"


@dataclass(frozen=True)
class JokerCoverageEntry:
    module: str
    class_name: str
    status: str
    required_parameters: tuple[str, ...] = ()
    known_features: tuple[str, ...] = ()
    unknown_signals: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class JokerCoverageReport:
    entries: tuple[JokerCoverageEntry, ...]

    @property
    def counts(self) -> tuple[tuple[str, int], ...]:
        counts = Counter(entry.status for entry in self.entries)
        return tuple(sorted(counts.items()))

    @property
    def gaps(self) -> tuple[JokerCoverageEntry, ...]:
        return tuple(entry for entry in self.entries if entry.status != COVERED)

    def count(self, status: str) -> int:
        return dict(self.counts).get(status, 0)


class JokerCoverageAuditor:
    """Enumerate every repository Joker class and measure semantic coverage.

    This is deliberately repository-driven: adding a new file/class automatically
    places it in the audit. Parameterized classes are reported separately because
    the current live Joker factory cannot instantiate constructors that require
    arguments. Constructible classes are behavior-probed; opaque raw context signals
    never count as complete semantic coverage.
    """

    def __init__(self, *, analyzer: LifecycleJokerBehaviorAnalyzer | None = None) -> None:
        self.analyzer = analyzer or LifecycleJokerBehaviorAnalyzer()

    def audit(self, *, analyze_semantics: bool = True) -> JokerCoverageReport:
        entries: list[JokerCoverageEntry] = []
        for module_name, joker_class in self._classes():
            required = self._required_parameters(joker_class)
            if required:
                entries.append(
                    JokerCoverageEntry(
                        module=module_name,
                        class_name=joker_class.__name__,
                        status=PARAMETERIZED,
                        required_parameters=required,
                    )
                )
                continue

            if not analyze_semantics:
                entries.append(
                    JokerCoverageEntry(
                        module=module_name,
                        class_name=joker_class.__name__,
                        status=UNANALYZED,
                    )
                )
                continue

            try:
                joker = joker_class()
                descriptor = self.analyzer.describe(joker)
            except Exception as exc:  # audit must report one bad model, not abort all
                entries.append(
                    JokerCoverageEntry(
                        module=module_name,
                        class_name=joker_class.__name__,
                        status=ERROR,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
                continue

            entries.append(self._classify(module_name, joker_class.__name__, descriptor))

        return JokerCoverageReport(entries=tuple(entries))

    @staticmethod
    def _classify(
        module_name: str,
        class_name: str,
        descriptor: SemanticEffectDescriptor,
    ) -> JokerCoverageEntry:
        produced = set(descriptor.produces)
        unknown = sorted(feature for feature in produced if feature.startswith("signal:"))
        known_produced = {feature for feature in produced if not feature.startswith("signal:")}
        known = set(known_produced)
        known.update(descriptor.requires)
        known.update(descriptor.scales_with)
        known.update(descriptor.amplifies)
        known.update(descriptor.transforms)
        known.update(descriptor.penalizes)

        if known and not unknown:
            status = COVERED
        elif known:
            status = PARTIAL
        else:
            status = OPAQUE

        return JokerCoverageEntry(
            module=module_name,
            class_name=class_name,
            status=status,
            known_features=tuple(sorted(known)),
            unknown_signals=tuple(unknown),
        )

    @staticmethod
    def _classes() -> tuple[tuple[str, type[Joker]], ...]:
        found: list[tuple[str, type[Joker]]] = []
        prefix = f"{joker_package.__name__}."
        for module_info in pkgutil.iter_modules(joker_package.__path__):
            if module_info.name.startswith("_"):
                continue
            module = importlib.import_module(prefix + module_info.name)
            classes = [
                value
                for value in vars(module).values()
                if inspect.isclass(value)
                and value is not Joker
                and issubclass(value, Joker)
                and value.__module__ == module.__name__
                and not inspect.isabstract(value)
            ]
            for joker_class in classes:
                found.append((module_info.name, joker_class))
        return tuple(sorted(found, key=lambda item: (item[0], item[1].__name__)))

    @staticmethod
    def _required_parameters(joker_class: type[Joker]) -> tuple[str, ...]:
        try:
            signature = inspect.signature(joker_class)
        except (TypeError, ValueError):
            return ()
        return tuple(
            parameter.name
            for parameter in signature.parameters.values()
            if parameter.kind
            in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD, parameter.KEYWORD_ONLY)
            and parameter.default is inspect.Parameter.empty
        )


def _print_report(report: JokerCoverageReport, *, gaps_only: bool) -> None:
    print("Balatro Joker semantic coverage -> READY")
    print(f"Joker classes -> {len(report.entries)}")
    for status in (COVERED, PARTIAL, OPAQUE, PARAMETERIZED, ERROR, UNANALYZED):
        print(f"{status} -> {report.count(status)}")

    entries = report.gaps if gaps_only else report.entries
    if not entries:
        print("Coverage gaps -> 0")
        return

    print("Coverage entries:")
    for entry in entries:
        detail: list[str] = []
        if entry.required_parameters:
            detail.append("required=" + ",".join(entry.required_parameters))
        if entry.unknown_signals:
            detail.append("unknown=" + ",".join(entry.unknown_signals))
        if entry.error:
            detail.append("error=" + entry.error)
        suffix = f" ({'; '.join(detail)})" if detail else ""
        print(f"  {entry.status:<13} {entry.module}.{entry.class_name}{suffix}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit semantic coverage of all Balatro Jokers")
    parser.add_argument(
        "--inventory-only",
        action="store_true",
        help="enumerate constructor coverage without running behavior probes",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="print covered Jokers too; default output lists only gaps",
    )
    args = parser.parse_args(argv)

    report = JokerCoverageAuditor().audit(analyze_semantics=not args.inventory_only)
    _print_report(report, gaps_only=not args.all)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
