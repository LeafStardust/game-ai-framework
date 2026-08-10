from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .phase_templates import load_phase_templates
from .vision import ColorGridSignature, PhaseTemplate


@dataclass(frozen=True)
class PhaseDistance:
    phase: str
    raw: float
    relative: float


@dataclass(frozen=True)
class CellDrift:
    column: int
    row: int
    raw: float
    relative: float


def nearest_phase_distances(
    baseline: list[PhaseTemplate],
    sample: PhaseTemplate,
) -> list[PhaseDistance]:
    compatible = [
        template
        for template in baseline
        if template.signature.columns == sample.signature.columns
        and template.signature.rows == sample.signature.rows
        and template.region == sample.region
    ]
    grouped: dict[str, list[PhaseTemplate]] = defaultdict(list)
    for template in compatible:
        grouped[template.phase].append(template)

    distances = []
    for phase, templates in grouped.items():
        raw = min(
            template.signature.distance(sample.signature)
            for template in templates
        )
        relative = min(
            template.signature.relative_weighted_distance(sample.signature)
            for template in templates
        )
        distances.append(PhaseDistance(phase, raw, relative))

    return sorted(distances, key=lambda item: (item.relative, item.raw, item.phase))


def centroid(templates: list[PhaseTemplate]) -> ColorGridSignature:
    if not templates:
        raise ValueError("at least one phase template is required")

    first = templates[0].signature
    for template in templates[1:]:
        signature = template.signature
        if signature.columns != first.columns or signature.rows != first.rows:
            raise ValueError("phase templates use inconsistent grid dimensions")
        if template.region != templates[0].region:
            raise ValueError("phase templates use inconsistent regions")

    values = tuple(
        round(sum(template.signature.values[index] for template in templates) / len(templates))
        for index in range(len(first.values))
    )
    return ColorGridSignature(first.columns, first.rows, values)


def cell_drift(
    baseline: list[PhaseTemplate],
    diagnostic: list[PhaseTemplate],
) -> list[CellDrift]:
    baseline_signature = centroid(baseline)
    diagnostic_signature = centroid(diagnostic)
    baseline_relative = baseline_signature.relative_values()
    diagnostic_relative = diagnostic_signature.relative_values()

    cells = []
    for row in range(baseline_signature.rows):
        for column in range(baseline_signature.columns):
            start = (row * baseline_signature.columns + column) * 3
            stop = start + 3
            raw = sum(
                abs(left - right)
                for left, right in zip(
                    baseline_signature.values[start:stop],
                    diagnostic_signature.values[start:stop],
                )
            ) / (3 * 255.0)
            relative = sum(
                abs(left - right)
                for left, right in zip(
                    baseline_relative[start:stop],
                    diagnostic_relative[start:stop],
                )
            ) / (3 * 510.0)
            cells.append(CellDrift(column, row, raw, relative))

    return sorted(cells, key=lambda item: (item.relative, item.raw), reverse=True)


def baseline_intra_phase_distance(templates: list[PhaseTemplate]) -> tuple[float, float]:
    if len(templates) < 2:
        return 0.0, 0.0

    raw = []
    relative = []
    for index, template in enumerate(templates):
        others = templates[:index] + templates[index + 1:]
        raw.append(min(other.signature.distance(template.signature) for other in others))
        relative.append(
            min(
                other.signature.relative_weighted_distance(template.signature)
                for other in others
            )
        )
    return sum(raw) / len(raw), sum(relative) / len(relative)


def _group_by_phase(templates: list[PhaseTemplate]) -> dict[str, list[PhaseTemplate]]:
    grouped: dict[str, list[PhaseTemplate]] = defaultdict(list)
    for template in templates:
        grouped[template.phase].append(template)
    return dict(grouped)


def analyze_file(
    baseline: list[PhaseTemplate],
    path: str | Path,
    *,
    top_cells: int = 8,
) -> None:
    diagnostic = load_phase_templates(path)
    if not diagnostic:
        raise ValueError(f"diagnostic file contains no templates: {path}")

    phases = sorted({template.phase for template in diagnostic})
    if len(phases) != 1:
        raise ValueError(f"diagnostic file must contain exactly one phase: {path}")
    expected = phases[0]

    baseline_by_phase = _group_by_phase(baseline)
    if expected not in baseline_by_phase:
        raise ValueError(f"baseline has no {expected} templates")

    print(f"\n{Path(path)} expected={expected} samples={len(diagnostic)}")
    own_raw = []
    own_relative = []
    other_raw = []
    other_relative = []

    for index, sample in enumerate(diagnostic, start=1):
        ranking = nearest_phase_distances(baseline, sample)
        expected_distance = next(item for item in ranking if item.phase == expected)
        best_other = min(
            (item for item in ranking if item.phase != expected),
            key=lambda item: (item.relative, item.raw),
        )
        own_raw.append(expected_distance.raw)
        own_relative.append(expected_distance.relative)
        other_raw.append(best_other.raw)
        other_relative.append(best_other.relative)
        print(
            f"  sample {index}: "
            f"own raw={expected_distance.raw:.4f} rel={expected_distance.relative:.4f}; "
            f"best-other={best_other.phase} raw={best_other.raw:.4f} "
            f"rel={best_other.relative:.4f}"
        )

    original_raw, original_relative = baseline_intra_phase_distance(
        baseline_by_phase[expected]
    )
    mean_own_raw = sum(own_raw) / len(own_raw)
    mean_own_relative = sum(own_relative) / len(own_relative)
    mean_other_raw = sum(other_raw) / len(other_raw)
    mean_other_relative = sum(other_relative) / len(other_relative)

    print(
        "  baseline intra-phase: "
        f"raw={original_raw:.4f} rel={original_relative:.4f}"
    )
    print(
        "  fresh -> original phase: "
        f"raw={mean_own_raw:.4f} rel={mean_own_relative:.4f}"
    )
    print(
        "  fresh -> nearest rival: "
        f"raw={mean_other_raw:.4f} rel={mean_other_relative:.4f}"
    )
    print(
        "  classification margins: "
        f"raw={mean_other_raw - mean_own_raw:+.4f} "
        f"rel={mean_other_relative - mean_own_relative:+.4f}"
    )

    drifts = cell_drift(baseline_by_phase[expected], diagnostic)
    print(f"  highest-drift cells (of {drifts[0].column * 0 + len(drifts)}):")
    for drift in drifts[:top_cells]:
        print(
            f"    col={drift.column:02d} row={drift.row:02d} "
            f"raw={drift.raw:.4f} rel={drift.relative:.4f}"
        )


def compare_diagnostics(paths: list[str | Path]) -> None:
    loaded = [(Path(path), load_phase_templates(path)) for path in paths]
    loaded = [(path, templates) for path, templates in loaded if templates]
    if len(loaded) < 2:
        return

    print("\nFresh diagnostic centroid distances:")
    for left_index, (left_path, left_templates) in enumerate(loaded):
        left_phase = sorted({template.phase for template in left_templates})
        if len(left_phase) != 1:
            continue
        left = centroid(left_templates)
        for right_path, right_templates in loaded[left_index + 1:]:
            right_phase = sorted({template.phase for template in right_templates})
            if len(right_phase) != 1:
                continue
            right = centroid(right_templates)
            print(
                f"  {left_phase[0]} ({left_path.name}) vs "
                f"{right_phase[0]} ({right_path.name}): "
                f"raw={left.distance(right):.4f} "
                f"rel={left.relative_weighted_distance(right):.4f}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare fresh Balatro phase signatures with calibration data."
    )
    parser.add_argument(
        "--baseline",
        default="balatro-phase-templates.json",
    )
    parser.add_argument(
        "--diagnostic",
        action="append",
        required=True,
        help="Diagnostic phase-template JSON. Repeat for multiple files.",
    )
    parser.add_argument("--top-cells", type=int, default=8)
    args = parser.parse_args()

    if args.top_cells < 1:
        parser.error("--top-cells must be at least 1")

    baseline = load_phase_templates(args.baseline)
    if not baseline:
        parser.error("baseline phase template file contains no templates")

    try:
        for path in args.diagnostic:
            analyze_file(baseline, path, top_cells=args.top_cells)
        compare_diagnostics(args.diagnostic)
    except ValueError as error:
        parser.error(str(error))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
