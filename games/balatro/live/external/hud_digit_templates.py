from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .hud_digits import DIGIT_COLUMNS, DIGIT_ROWS


TEMPLATE_VERSION = 1
FEATURE_NAME = "color_component_shape_v1"
DIGITS = tuple(str(value) for value in range(10))


@dataclass(frozen=True)
class HudDigitTemplate:
    digit: str
    signature: tuple[int, ...]


@dataclass(frozen=True)
class HudDigitTemplateSet:
    columns: int
    rows: int
    templates: tuple[HudDigitTemplate, ...]

    @property
    def coverage(self) -> set[str]:
        return {template.digit for template in self.templates}

    @property
    def complete(self) -> bool:
        return self.coverage == set(DIGITS)


def save_hud_digit_templates(
    templates: HudDigitTemplateSet,
    path: str | Path,
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": TEMPLATE_VERSION,
        "feature": FEATURE_NAME,
        "columns": templates.columns,
        "rows": templates.rows,
        "templates": [
            {
                "digit": template.digit,
                "signature": list(template.signature),
            }
            for template in templates.templates
        ],
    }
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output


def load_hud_digit_templates(path: str | Path) -> HudDigitTemplateSet:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    version = payload.get("version")
    if version != TEMPLATE_VERSION:
        raise ValueError(
            f"unsupported HUD digit template version {version}; "
            f"expected {TEMPLATE_VERSION}"
        )
    if payload.get("feature") != FEATURE_NAME:
        raise ValueError("HUD digit template feature does not match runtime extractor")

    columns = int(payload.get("columns", 0))
    rows = int(payload.get("rows", 0))
    if columns < 5 or rows < 5:
        raise ValueError("HUD digit template dimensions are invalid")

    expected_length = columns * rows
    templates = []
    for item in payload.get("templates", []):
        digit = str(item.get("digit", ""))
        if digit not in DIGITS:
            raise ValueError(f"invalid HUD digit template label: {digit}")
        signature = tuple(int(value) for value in item.get("signature", []))
        if len(signature) != expected_length:
            raise ValueError(
                f"HUD digit template {digit} has invalid signature length"
            )
        if any(value < 0 or value > 255 for value in signature):
            raise ValueError(f"HUD digit template {digit} contains invalid values")
        templates.append(HudDigitTemplate(digit, signature))

    return HudDigitTemplateSet(columns, rows, tuple(templates))


def empty_hud_digit_templates() -> HudDigitTemplateSet:
    return HudDigitTemplateSet(DIGIT_COLUMNS, DIGIT_ROWS, ())


def merge_hud_digit_templates(
    base: HudDigitTemplateSet,
    additions: list[HudDigitTemplate],
) -> HudDigitTemplateSet:
    if base.columns != DIGIT_COLUMNS or base.rows != DIGIT_ROWS:
        raise ValueError("HUD digit template dimensions do not match extractor")

    seen = {(template.digit, template.signature) for template in base.templates}
    merged = list(base.templates)
    for template in additions:
        if template.digit not in DIGITS:
            raise ValueError(f"invalid HUD digit template label: {template.digit}")
        key = (template.digit, template.signature)
        if key not in seen:
            merged.append(template)
            seen.add(key)
    return HudDigitTemplateSet(base.columns, base.rows, tuple(merged))
