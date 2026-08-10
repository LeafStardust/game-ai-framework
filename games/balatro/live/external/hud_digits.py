from __future__ import annotations

from dataclasses import dataclass

from .card_templates import RGBImage


DIGIT_COLUMNS = 20
DIGIT_ROWS = 30
DIGIT_PADDING = 1
COLOR_TOLERANCE = 90.0
MIN_COMPONENT_AREA = 20
MIN_COMPONENT_HEIGHT_FRACTION = 0.35


@dataclass(frozen=True)
class HudFieldStyle:
    rgb: tuple[int, int, int]
    prefix_components: int = 0


HUD_FIELD_STYLES = {
    "ante": HudFieldStyle((255, 143, 0)),
    "blind_target": HudFieldStyle((255, 76, 64)),
    "discards": HudFieldStyle((255, 76, 64)),
    "hands": HudFieldStyle((0, 147, 255)),
    "money": HudFieldStyle((245, 178, 68), prefix_components=1),
    "round": HudFieldStyle((255, 143, 0)),
    "score": HudFieldStyle((255, 255, 255), prefix_components=1),
}


@dataclass(frozen=True)
class HudGlyphComponent:
    points: tuple[tuple[int, int], ...]
    min_x: int
    max_x: int
    min_y: int
    max_y: int

    @property
    def area(self) -> int:
        return len(self.points)

    @property
    def width(self) -> int:
        return self.max_x - self.min_x + 1

    @property
    def height(self) -> int:
        return self.max_y - self.min_y + 1


def extract_hud_digit_signatures(
    image: RGBImage,
    field: str,
    *,
    expected_digits: int | None = None,
    columns: int = DIGIT_COLUMNS,
    rows: int = DIGIT_ROWS,
) -> tuple[tuple[int, ...], ...]:
    style = HUD_FIELD_STYLES.get(field)
    if style is None:
        raise ValueError(f"unknown HUD field: {field}")
    if columns < 5 or rows < 5:
        raise ValueError("HUD digit signature dimensions must be at least 5")
    if expected_digits is not None and expected_digits < 1:
        raise ValueError("expected digit count must be positive")

    mask = _color_mask(image, style.rgb)
    components = _connected_components(mask, image.width, image.height)
    minimum_height = max(6, round(image.height * MIN_COMPONENT_HEIGHT_FRACTION))
    components = [
        component
        for component in components
        if component.area >= MIN_COMPONENT_AREA
        and component.height >= minimum_height
    ]
    components.sort(key=lambda component: component.min_x)

    if len(components) <= style.prefix_components:
        raise ValueError(f"HUD field {field} contains no digit components")
    digits = components[style.prefix_components :]

    if expected_digits is not None and len(digits) != expected_digits:
        raise ValueError(
            f"HUD field {field} expected {expected_digits} digit components, "
            f"found {len(digits)}"
        )

    return tuple(
        _component_signature(component, columns=columns, rows=rows)
        for component in digits
    )


def signature_distance(left: tuple[int, ...], right: tuple[int, ...]) -> float:
    if len(left) != len(right):
        raise ValueError("HUD digit signatures must have equal dimensions")
    if not left:
        raise ValueError("HUD digit signatures cannot be empty")
    return sum(abs(a - b) for a, b in zip(left, right)) / (255.0 * len(left))


def _color_mask(image: RGBImage, target: tuple[int, int, int]) -> list[bool]:
    tolerance_squared = COLOR_TOLERANCE * COLOR_TOLERANCE
    mask = []
    for index in range(0, len(image.rgb), 3):
        pixel = image.rgb[index : index + 3]
        distance_squared = sum(
            (channel - expected) ** 2
            for channel, expected in zip(pixel, target)
        )
        mask.append(distance_squared <= tolerance_squared)
    return mask


def _connected_components(
    mask: list[bool],
    width: int,
    height: int,
) -> list[HudGlyphComponent]:
    if len(mask) != width * height:
        raise ValueError("HUD glyph mask dimensions do not match image")

    visited = [False] * len(mask)
    components = []
    for y in range(height):
        for x in range(width):
            index = y * width + x
            if not mask[index] or visited[index]:
                continue

            stack = [(x, y)]
            visited[index] = True
            points = []
            while stack:
                current_x, current_y = stack.pop()
                points.append((current_x, current_y))
                for delta_y in (-1, 0, 1):
                    for delta_x in (-1, 0, 1):
                        if delta_x == 0 and delta_y == 0:
                            continue
                        next_x = current_x + delta_x
                        next_y = current_y + delta_y
                        if not (0 <= next_x < width and 0 <= next_y < height):
                            continue
                        next_index = next_y * width + next_x
                        if mask[next_index] and not visited[next_index]:
                            visited[next_index] = True
                            stack.append((next_x, next_y))

            components.append(
                HudGlyphComponent(
                    tuple(points),
                    min(point[0] for point in points),
                    max(point[0] for point in points),
                    min(point[1] for point in points),
                    max(point[1] for point in points),
                )
            )
    return components


def _component_signature(
    component: HudGlyphComponent,
    *,
    columns: int,
    rows: int,
) -> tuple[int, ...]:
    inner_columns = columns - 2 * DIGIT_PADDING
    inner_rows = rows - 2 * DIGIT_PADDING
    scale = min(
        inner_columns / component.width,
        inner_rows / component.height,
    )
    rendered_width = max(1, min(inner_columns, round(component.width * scale)))
    rendered_height = max(1, min(inner_rows, round(component.height * scale)))
    offset_x = (columns - rendered_width) // 2
    offset_y = (rows - rendered_height) // 2
    points = set(component.points)

    canvas = [0] * (columns * rows)
    for target_y in range(rendered_height):
        source_y = min(
            component.max_y,
            component.min_y
            + int((target_y + 0.5) * component.height / rendered_height),
        )
        for target_x in range(rendered_width):
            source_x = min(
                component.max_x,
                component.min_x
                + int((target_x + 0.5) * component.width / rendered_width),
            )
            if (source_x, source_y) in points:
                canvas[(offset_y + target_y) * columns + offset_x + target_x] = 255

    return tuple(canvas)
