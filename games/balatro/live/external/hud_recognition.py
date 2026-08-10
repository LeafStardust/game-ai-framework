from __future__ import annotations

from dataclasses import dataclass

from .card_templates import RGBImage
from .hud_digit_templates import HudDigitTemplateSet
from .hud_digits import extract_hud_digit_signatures, signature_distance


@dataclass(frozen=True)
class HudDigitMatch:
    digit: str
    distance: float
    runner_up: str | None
    margin: float | None


@dataclass(frozen=True)
class HudNumberRecognition:
    field: str
    value: int
    digits: tuple[HudDigitMatch, ...]


def recognize_hud_digit(
    signature: tuple[int, ...],
    templates: HudDigitTemplateSet,
) -> HudDigitMatch:
    if not templates.templates:
        raise ValueError("HUD digit template set is empty")

    best_by_digit = {}
    for template in templates.templates:
        distance = signature_distance(signature, template.signature)
        current = best_by_digit.get(template.digit)
        if current is None or distance < current:
            best_by_digit[template.digit] = distance

    ranked = sorted(best_by_digit.items(), key=lambda item: (item[1], item[0]))
    digit, distance = ranked[0]
    if len(ranked) == 1:
        return HudDigitMatch(digit, distance, None, None)

    runner_up, runner_up_distance = ranked[1]
    return HudDigitMatch(
        digit,
        distance,
        runner_up,
        runner_up_distance - distance,
    )


def recognize_hud_number(
    image: RGBImage,
    field: str,
    templates: HudDigitTemplateSet,
) -> HudNumberRecognition:
    signatures = extract_hud_digit_signatures(
        image,
        field,
        columns=templates.columns,
        rows=templates.rows,
    )
    matches = tuple(
        recognize_hud_digit(signature, templates)
        for signature in signatures
    )
    if not matches:
        raise ValueError(f"HUD field {field} contains no recognized digits")
    return HudNumberRecognition(
        field,
        int("".join(match.digit for match in matches)),
        matches,
    )


def rgb_image_from_bgra(width: int, height: int, bgra: bytes) -> RGBImage:
    expected = width * height * 4
    if len(bgra) != expected:
        raise ValueError(
            f"BGRA pixel buffer must contain {expected} bytes, got {len(bgra)}"
        )

    rgb = bytearray(width * height * 3)
    destination = 0
    for index in range(0, len(bgra), 4):
        blue, green, red = bgra[index : index + 3]
        rgb[destination : destination + 3] = bytes((red, green, blue))
        destination += 3
    return RGBImage(width, height, bytes(rgb))
