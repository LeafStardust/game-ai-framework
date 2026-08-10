from __future__ import annotations

import json
from pathlib import Path

from .card_templates import CardTemplateSet, CardVisualTemplate


TEMPLATE_VERSION = 5
RANK_FEATURE = "face-aligned-color-guided-rank-components-v1"
SUIT_FEATURE = "face-aligned-suit-median-rgb-v1"


def save_card_template_set(path: str | Path, templates: CardTemplateSet) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": TEMPLATE_VERSION,
        "columns": templates.columns,
        "rows": templates.rows,
        "rank_feature": RANK_FEATURE,
        "suit_feature": SUIT_FEATURE,
        "ranks": [
            {"label": template.label, "signature": list(template.signature)}
            for template in templates.ranks
        ],
        "suits": [
            {"label": template.label, "signature": list(template.signature)}
            for template in templates.suits
        ],
    }
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output


def load_card_template_set(path: str | Path) -> CardTemplateSet:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    version = payload.get("version")
    if version != TEMPLATE_VERSION:
        if version in {1, 2, 3, 4}:
            raise ValueError(
                f"legacy card template version {version} must be rebuilt from labeled identity crops"
            )
        raise ValueError("unsupported card template version")

    if payload.get("rank_feature") != RANK_FEATURE:
        raise ValueError("unsupported card rank feature format")
    if payload.get("suit_feature") != SUIT_FEATURE:
        raise ValueError("unsupported card suit feature format")

    columns = int(payload["columns"])
    rows = int(payload["rows"])
    rank_expected = columns * rows

    def parse_templates(kind: str, expected: int) -> tuple[CardVisualTemplate, ...]:
        templates = []
        for item in payload.get(kind, []):
            signature = tuple(int(value) for value in item["signature"])
            if len(signature) != expected:
                raise ValueError(f"invalid {kind} template signature length")
            if any(value < 0 or value > 255 for value in signature):
                raise ValueError(f"invalid {kind} template signature value")
            templates.append(CardVisualTemplate(str(item["label"]), signature))
        return tuple(templates)

    return CardTemplateSet(
        columns,
        rows,
        parse_templates("ranks", rank_expected),
        parse_templates("suits", 3),
    )
