from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from .phase_templates import load_phase_templates, save_phase_templates
from .vision import PhaseTemplate


def merge_phase_template_sources(
    templates_path: str | Path,
    source_paths: list[str | Path],
    *,
    output_path: str | Path | None = None,
    replace_phases: set[str] | None = None,
) -> Counter:
    if not source_paths:
        raise ValueError("at least one phase dataset source is required")

    base_path = Path(templates_path)
    output = Path(output_path) if output_path is not None else base_path
    base_templates = load_phase_templates(base_path)
    source_templates: list[PhaseTemplate] = []
    source_phases: set[str] = set()

    for source_path in source_paths:
        source = Path(source_path)
        templates = load_phase_templates(source)
        if not templates:
            raise ValueError(f"phase dataset source contains no templates: {source}")

        phases = {template.phase for template in templates}
        if len(phases) != 1:
            raise ValueError(
                f"phase dataset source must contain exactly one phase: {source}"
            )

        source_phase = next(iter(phases))
        source_phases.add(source_phase)
        source_templates.extend(templates)

    phases_to_replace = {
        phase.upper() for phase in (replace_phases or source_phases)
    }
    missing_sources = phases_to_replace - source_phases
    if missing_sources:
        raise ValueError(
            "replacement phase has no dataset source: "
            + ", ".join(sorted(missing_sources))
        )

    merged = [
        template
        for template in base_templates
        if template.phase not in phases_to_replace
    ]
    merged.extend(source_templates)
    save_phase_templates(output, merged)
    return Counter(template.phase for template in merged)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge representative Balatro phase calibration datasets."
    )
    parser.add_argument(
        "--templates",
        default="balatro-phase-templates.json",
        help="Existing template set used as the merge base.",
    )
    parser.add_argument(
        "--source",
        action="append",
        required=True,
        help="Single-phase calibration file to merge; may be repeated.",
    )
    parser.add_argument(
        "--output",
        help="Output file. Defaults to overwriting --templates.",
    )
    parser.add_argument(
        "--replace-phase",
        action="append",
        help=(
            "Phase to replace from the base set. May be repeated. "
            "Defaults to every phase represented by --source files."
        ),
    )
    args = parser.parse_args()

    try:
        counts = merge_phase_template_sources(
            args.templates,
            args.source,
            output_path=args.output,
            replace_phases=(
                {phase.upper() for phase in args.replace_phase}
                if args.replace_phase
                else None
            ),
        )
    except ValueError as error:
        parser.error(str(error))

    output = args.output or args.templates
    print(
        "Merged phase templates: "
        + ", ".join(
            f"{phase}={counts[phase]}"
            for phase in sorted(counts)
        )
    )
    print(f"Saved -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
