from __future__ import annotations

import argparse
import ast
import inspect
import textwrap
from collections import Counter
from dataclasses import dataclass

from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.live.joker_state_contract import public_joker_state_fields

from .joker_coverage import JokerCoverageAuditor


HYDRATED = "HYDRATED"
STATELESS = "STATELESS"
GAP = "GAP"
ERROR = "ERROR"


@dataclass(frozen=True)
class JokerLiveStateEntry:
    module: str
    class_name: str
    status: str
    mutable_fields: tuple[str, ...] = ()
    hydrated_fields: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class JokerLiveStateReport:
    entries: tuple[JokerLiveStateEntry, ...]

    @property
    def counts(self) -> tuple[tuple[str, int], ...]:
        counts = Counter(entry.status for entry in self.entries)
        return tuple(sorted(counts.items()))

    @property
    def gaps(self) -> tuple[JokerLiveStateEntry, ...]:
        return tuple(entry for entry in self.entries if entry.status in {GAP, ERROR})

    def count(self, status: str) -> int:
        return dict(self.counts).get(status, 0)


class JokerLiveStateFidelityAuditor:
    """Audit whether mutable model-local Joker state can be reconstructed live.

    The semantic coverage audit answers whether we understand what each Joker
    does. This audit answers a different question: if a Joker mutates one of its
    own instance fields during a run, does the live observer/factory path carry
    enough public state to restore that field instead of silently using the
    constructor default?

    Mutable fields are discovered from model source rather than a Joker-name list:
    assignments to ``self.<field>`` outside ``__init__`` are treated as run-state
    requirements. Constructor-only configuration therefore does not become a
    false positive (for example FlatMultJoker.mult = 4).
    """

    def audit(self) -> JokerLiveStateReport:
        entries: list[JokerLiveStateEntry] = []
        factory_fields = frozenset(LiveJokerFactory.PUBLIC_STATE_FIELDS)

        for module_name, joker_class in JokerCoverageAuditor._classes():
            try:
                mutable = self._mutable_instance_fields(joker_class)
            except Exception as exc:
                entries.append(
                    JokerLiveStateEntry(
                        module=module_name,
                        class_name=joker_class.__name__,
                        status=ERROR,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
                continue

            if not mutable:
                entries.append(
                    JokerLiveStateEntry(
                        module=module_name,
                        class_name=joker_class.__name__,
                        status=STATELESS,
                    )
                )
                continue

            observed = public_joker_state_fields(joker_class.__name__)
            hydrated = mutable & observed & factory_fields
            missing = mutable - hydrated
            entries.append(
                JokerLiveStateEntry(
                    module=module_name,
                    class_name=joker_class.__name__,
                    status=HYDRATED if not missing else GAP,
                    mutable_fields=tuple(sorted(mutable)),
                    hydrated_fields=tuple(sorted(hydrated)),
                    missing_fields=tuple(sorted(missing)),
                )
            )

        return JokerLiveStateReport(entries=tuple(entries))

    @classmethod
    def _mutable_instance_fields(cls, joker_class: type) -> frozenset[str]:
        source = textwrap.dedent(inspect.getsource(joker_class))
        tree = ast.parse(source)
        fields: set[str] = set()

        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            for member in node.body:
                if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if member.name == "__init__":
                    continue
                for child in ast.walk(member):
                    if isinstance(child, ast.Assign):
                        for target in child.targets:
                            fields.update(cls._self_fields(target))
                    elif isinstance(child, ast.AnnAssign):
                        fields.update(cls._self_fields(child.target))
                    elif isinstance(child, ast.AugAssign):
                        fields.update(cls._self_fields(child.target))
                    elif isinstance(child, ast.Call):
                        fields.update(cls._literal_setattr_field(child))

        return frozenset(fields)

    @staticmethod
    def _self_fields(target: ast.AST) -> set[str]:
        result: set[str] = set()
        for node in ast.walk(target):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "self"
            ):
                result.add(node.attr)
        return result

    @staticmethod
    def _literal_setattr_field(call: ast.Call) -> set[str]:
        if not isinstance(call.func, ast.Name) or call.func.id != "setattr":
            return set()
        if len(call.args) < 2:
            return set()
        target, field = call.args[0], call.args[1]
        if not isinstance(target, ast.Name) or target.id != "self":
            return set()
        if not isinstance(field, ast.Constant) or not isinstance(field.value, str):
            return set()
        return {field.value}


def _print_report(report: JokerLiveStateReport, *, all_entries: bool) -> None:
    print("Balatro Joker live-state fidelity -> READY")
    print(f"Joker classes -> {len(report.entries)}")
    for status in (HYDRATED, STATELESS, GAP, ERROR):
        print(f"{status} -> {report.count(status)}")

    entries = report.entries if all_entries else report.gaps
    if not entries:
        print("Live-state gaps -> 0")
        return

    print("Live-state entries:")
    for entry in entries:
        detail: list[str] = []
        if entry.mutable_fields:
            detail.append("mutable=" + ",".join(entry.mutable_fields))
        if entry.hydrated_fields:
            detail.append("hydrated=" + ",".join(entry.hydrated_fields))
        if entry.missing_fields:
            detail.append("missing=" + ",".join(entry.missing_fields))
        if entry.error:
            detail.append("error=" + entry.error)
        suffix = f" ({'; '.join(detail)})" if detail else ""
        print(f"  {entry.status:<9} {entry.module}.{entry.class_name}{suffix}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit live reconstruction of mutable Balatro Joker model state"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="print stateless and already hydrated Jokers too",
    )
    args = parser.parse_args(argv)

    report = JokerLiveStateFidelityAuditor().audit()
    _print_report(report, all_entries=args.all)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
