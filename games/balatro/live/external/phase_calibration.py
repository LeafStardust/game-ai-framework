from __future__ import annotations

import argparse
import time
from pathlib import Path

from .capture import BalatroScreenCapture, save_frame_png
from .phase_templates import load_phase_templates, save_phase_templates
from .vision import BalatroVisualPhaseRecognizer, PhaseTemplate


def capture_phase_templates(
    phase: str,
    capture: BalatroScreenCapture,
    *,
    samples: int = 3,
    delay: float = 0.15,
    columns: int = 24,
    rows: int = 14,
    max_distance: float = 0.18,
    snapshot_path: str | Path | None = None,
) -> list[PhaseTemplate]:
    if samples < 1:
        raise ValueError("phase calibration requires at least one sample")

    recognizer = BalatroVisualPhaseRecognizer()
    templates = []

    for index in range(samples):
        frame = capture.capture()
        if index == 0 and snapshot_path is not None:
            save_frame_png(frame, snapshot_path)
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
    parser.add_argument("--prepare-delay", type=float, default=3.0)
    parser.add_argument("--snapshot")
    parser.add_argument(
        "--replace-phase",
        action="store_true",
        help="Replace existing templates with the same phase label.",
    )
    args = parser.parse_args()

    if args.prepare_delay < 0:
        parser.error("--prepare-delay cannot be negative")

    output = Path(args.output)
    templates = load_phase_templates(output)
    phase = args.phase.upper()

    if args.replace_phase:
        templates = [
            template for template in templates
            if template.phase != phase
        ]

    if args.prepare_delay > 0:
        print(
            f"Capture starts in {args.prepare_delay:g}s; "
            "bring Balatro to the foreground.",
            flush=True,
        )
        time.sleep(args.prepare_delay)

    with BalatroScreenCapture() as capture:
        captured = capture_phase_templates(
            phase,
            capture,
            samples=args.samples,
            delay=args.delay,
            snapshot_path=args.snapshot,
        )

    templates.extend(captured)
    save_phase_templates(output, templates)
    print(
        f"Captured {len(captured)} {phase} visual templates -> {output}"
    )
    if args.snapshot:
        print(f"Saved first captured frame -> {args.snapshot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
