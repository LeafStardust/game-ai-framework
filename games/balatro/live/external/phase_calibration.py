from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .capture import BalatroScreenCapture
from .vision import BalatroVisualPhaseRecognizer, PhaseTemplate


def load_phase_templates(path: str | Path) -> list[PhaseTemplate]:
    file_path = Path(path)
    if not file_path.exists():
        return []

    data = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("phase template file must contain a JSON list")
    return [PhaseTemplate.from_dict(item) for item in data]


def save_phase_templates(
    path: str | Path,
    templates: list[PhaseTemplate],
) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(
            [template.to_dict() for template in templates],
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def capture_phase_templates(
    phase: str,
    capture: BalatroScreenCapture,
    *,
    samples: int = 3,
    delay: float = 0.15,
    columns: int = 24,
    rows: int = 14,
    max_distance: float = 0.18,
) -> list[PhaseTemplate]:
    if samples < 1:
        raise ValueError("phase calibration requires at least one sample")

    recognizer = BalatroVisualPhaseRecognizer()
    templates = []

    for index in range(samples):
        frame = capture.capture()
        templates.append(
            recognizer.template_from_frame(
                phase,
                frame,
                columns=columns,
                rows=rows,
                max_distance=max_distance,
            )
        )
        if index + 1 < samples and delay > 0:
            time.sleep(delay)

    return templates


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture external visual signatures for a Balatro UI phase."
    )
    parser.add_argument("--phase", required=True)
    parser.add_argument(
        "--output",
        default="balatro-phase-templates.json",
    )
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--delay", type=float, default=0.15)
    parser.add_argument(
        "--replace-phase",
        action="store_true",
        help="Replace existing templates with the same phase label.",
    )
    args = parser.parse_args()

    output = Path(args.output)
    templates = load_phase_templates(output)
    phase = args.phase.upper()

    if args.replace_phase:
        templates = [
            template for template in templates
            if template.phase != phase
        ]

    with BalatroScreenCapture() as capture:
        captured = capture_phase_templates(
            phase,
            capture,
            samples=args.samples,
            delay=args.delay,
        )

    templates.extend(captured)
    save_phase_templates(output, templates)
    print(
        f"Captured {len(captured)} {phase} visual templates -> {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
