from __future__ import annotations

import json
from pathlib import Path

from .vision import PhaseTemplate


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
