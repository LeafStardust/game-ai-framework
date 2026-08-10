from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .card_templates import (
    CardTemplateSet,
    CardVisualTemplate,
    RGBImage,
    load_rgb_png,
    parse_card_label,
)


FACE_LEFT = 0.08
FACE_RIGHT = 0.42
FACE_SCAN_BOTTOM = 0.48
FACE_NEUTRAL_MIN = 170
FACE_CHROMA_MAX = 45
FACE_ROW_FRACTION = 0.60

RANK_LEFT = 0.08
RANK_RIGHT = 0.44
RANK_TOP_OFFSET = 0.09
RANK_BOTTOM_OFFSET = 0.34
RANK_COMPONENT_THRESHOLD = 45
RANK_PADDING = 2

SUIT_LEFT = 0.08
SUIT_RIGHT = 0.44
SUIT_TOP_OFFSET = 0.31
SUIT_BOTTOM_OFFSET = 0.55
FOREGROUND_THRESHOLD = 35
BACKGROUND_FRACTION = 0.40
COLOR_LINE_RESIDUAL = 30.0
COLOR_LINE_MIN_ALPHA = 0.06


@dataclass(frozen=True)
class _Component:
    points: tuple[tuple[int, int], ...]
    min_x: int
    max_x: int
    min_y: int
    max_y: int

    @property
    def area(self) -> int:
        return len(self.points)

    @property
    def height(self) -> int:
        return self.max_y - self.min_y + 1


def detect_card_face_top(image: RGBImage) -> int:
    left = max(0, round(FACE_LEFT * image.width))
    right = min(image.width, max(left + 1, round(FACE_RIGHT * image.width)))
    scan_bottom = min(
        image.height,
        max(2, round(FACE_SCAN_BOTTOM * image.height)),
    )

    fractions = []
    for y in range(scan_bottom):
        neutral = 0
        for x in range(left, right):
            red, green, blue = _pixel_rgb(image, x, y)
            neutral += int(
                min(red, green, blue) >= FACE_NEUTRAL_MIN
                and max(red, green, blue) - min(red, green, blue) <= FACE_CHROMA_MAX
            )
        fractions.append(neutral / max(1, right - left))

    for y in range(len(fractions) - 1):
        if fractions[y] >= FACE_ROW_FRACTION and fractions[y + 1] >= FACE_ROW_FRACTION:
            return y
    raise ValueError("unable to locate playing-card face top")


def aligned_suit_color_signature(
    image: RGBImage,
    *,
    foreground_threshold: int = FOREGROUND_THRESHOLD,
) -> tuple[int, int, int]:
    face_top = detect_card_face_top(image)
    left, top, right, bottom = _aligned_bounds(
        image,
        face_top,
        SUIT_LEFT,
        SUIT_RIGHT,
        SUIT_TOP_OFFSET,
        SUIT_BOTTOM_OFFSET,
    )
    background = _background_rgb(image, left, top, right, bottom)
    foreground = []

    for y in range(top, bottom):
        for x in range(left, right):
            pixel = _pixel_rgb(image, x, y)
            distance = _color_distance(pixel, background)
            if distance >= foreground_threshold:
                foreground.append((distance, pixel))

    if not foreground:
        raise ValueError("aligned suit glyph region contains no foreground pixels")

    foreground.sort(key=lambda item: item[0])
    strong = foreground[len(foreground) // 2 :]
    return tuple(_median(channel) for channel in zip(*(pixel for _, pixel in strong)))


def aligned_rank_shape_signature(
    image: RGBImage,
    glyph_color: tuple[int, int, int],
    *,
    columns: int,
    rows: int,
) -> tuple[int, ...]:
    if columns < 5 or rows < 5:
        raise ValueError("rank signature dimensions must be at least 5")

    face_top = detect_card_face_top(image)
    left, top, right, bottom = _aligned_bounds(
        image,
        face_top,
        RANK_LEFT,
        RANK_RIGHT,
        RANK_TOP_OFFSET,
        RANK_BOTTOM_OFFSET,
    )
    background = _background_rgb(image, left, top, right, bottom)
    width = right - left
    height = bottom - top
    strengths = [0] * (width * height)
    direction = tuple(glyph - bg for glyph, bg in zip(glyph_color, background))
    denominator = sum(value * value for value in direction)
    if denominator <= 0:
        raise ValueError("rank glyph color is indistinguishable from card background")

    for local_y, y in enumerate(range(top, bottom)):
        for local_x, x in enumerate(range(left, right)):
            pixel = _pixel_rgb(image, x, y)
            vector = tuple(value - bg for value, bg in zip(pixel, background))
            alpha = sum(value * axis for value, axis in zip(vector, direction)) / denominator
            reconstructed = tuple(
                bg + alpha * axis for bg, axis in zip(background, direction)
            )
            residual = sum(
                abs(value - expected) for value, expected in zip(pixel, reconstructed)
            ) / 3.0
            if alpha >= COLOR_LINE_MIN_ALPHA and residual <= COLOR_LINE_RESIDUAL:
                strengths[local_y * width + local_x] = round(
                    255 * min(1.0, max(0.0, alpha))
                )

    components = _rank_components(strengths, width, height)
    selected = _select_rank_components(components, width, height)
    if not selected:
        raise ValueError("aligned rank glyph region contains no rank component")

    selected_points = {
        point
        for component in selected
        for point in component.points
    }
    min_x = min(x for x, _ in selected_points)
    max_x = max(x for x, _ in selected_points)
    min_y = min(y for _, y in selected_points)
    max_y = max(y for _, y in selected_points)
    glyph_width = max_x - min_x + 1
    glyph_height = max_y - min_y + 1

    inner_columns = columns - 2 * RANK_PADDING
    inner_rows = rows - 2 * RANK_PADDING
    scale = min(inner_columns / glyph_width, inner_rows / glyph_height)
    rendered_width = max(1, min(inner_columns, round(glyph_width * scale)))
    rendered_height = max(1, min(inner_rows, round(glyph_height * scale)))
    offset_x = (columns - rendered_width) // 2
    offset_y = (rows - rendered_height) // 2

    canvas = [0] * (columns * rows)
    for target_y in range(rendered_height):
        source_y = min(
            max_y,
            min_y + int((target_y + 0.5) * glyph_height / rendered_height),
        )
        for target_x in range(rendered_width):
            source_x = min(
                max_x,
                min_x + int((target_x + 0.5) * glyph_width / rendered_width),
            )
            if (source_x, source_y) not in selected_points:
                continue
            value = strengths[source_y * width + source_x]
            canvas[(offset_y + target_y) * columns + offset_x + target_x] = value

    return _smooth_signature(canvas, columns, rows)


def aligned_templates_from_labeled_images(
    image_paths: list[str | Path],
    labels: list[str],
    *,
    columns: int,
    rows: int,
) -> CardTemplateSet:
    if len(image_paths) != len(labels):
        raise ValueError("image and label counts must match")
    if not image_paths:
        raise ValueError("at least one labeled card image is required")

    ranks = []
    suits = []
    for image_path, label in zip(image_paths, labels):
        rank, suit = parse_card_label(label)
        image = load_rgb_png(image_path)
        suit_signature = aligned_suit_color_signature(image)
        ranks.append(
            CardVisualTemplate(
                rank,
                aligned_rank_shape_signature(
                    image,
                    suit_signature,
                    columns=columns,
                    rows=rows,
                ),
            )
        )
        suits.append(CardVisualTemplate(suit, suit_signature))

    return CardTemplateSet(columns, rows, tuple(ranks), tuple(suits))


def _rank_components(
    strengths: list[int],
    width: int,
    height: int,
) -> list[_Component]:
    active = [value >= RANK_COMPONENT_THRESHOLD for value in strengths]
    visited = [False] * len(active)
    components = []

    for y in range(height):
        for x in range(width):
            index = y * width + x
            if not active[index] or visited[index]:
                continue
            stack = [(x, y)]
            visited[index] = True
            points = []
            while stack:
                current_x, current_y = stack.pop()
                points.append((current_x, current_y))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        next_x = current_x + dx
                        next_y = current_y + dy
                        if not (0 <= next_x < width and 0 <= next_y < height):
                            continue
                        next_index = next_y * width + next_x
                        if active[next_index] and not visited[next_index]:
                            visited[next_index] = True
                            stack.append((next_x, next_y))

            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            components.append(
                _Component(
                    tuple(points),
                    min(xs),
                    max(xs),
                    min(ys),
                    max(ys),
                )
            )
    return components


def _select_rank_components(
    components: list[_Component],
    width: int,
    height: int,
) -> list[_Component]:
    minimum_area = max(3, round(width * height * 0.02))
    substantial = [component for component in components if component.area >= minimum_area]
    if not substantial:
        return []

    substantial.sort(key=lambda component: (component.min_y, -component.area))
    anchor = substantial[0]
    selected = []
    for component in substantial:
        overlap = max(
            0,
            min(anchor.max_y, component.max_y)
            - max(anchor.min_y, component.min_y)
            + 1,
        )
        overlap_fraction = overlap / max(1, min(anchor.height, component.height))
        if component.min_y <= anchor.min_y + 4 or overlap_fraction >= 0.50:
            selected.append(component)
    return selected


def _aligned_bounds(
    image: RGBImage,
    face_top: int,
    left_ratio: float,
    right_ratio: float,
    top_offset: float,
    bottom_offset: float,
) -> tuple[int, int, int, int]:
    left = max(0, round(left_ratio * image.width))
    right = min(image.width, max(left + 1, round(right_ratio * image.width)))
    top = max(0, face_top + round(top_offset * image.height))
    bottom = min(
        image.height,
        max(top + 1, face_top + round(bottom_offset * image.height)),
    )
    return left, top, right, bottom


def _background_rgb(
    image: RGBImage,
    left: int,
    top: int,
    right: int,
    bottom: int,
) -> tuple[int, int, int]:
    pixels = [
        _pixel_rgb(image, x, y)
        for y in range(top, bottom)
        for x in range(left, right)
    ]
    count = max(1, round(len(pixels) * BACKGROUND_FRACTION))
    brightest = sorted(pixels, key=sum, reverse=True)[:count]
    return tuple(_median(channel) for channel in zip(*brightest))


def _pixel_rgb(image: RGBImage, x: int, y: int) -> tuple[int, int, int]:
    index = (y * image.width + x) * 3
    red, green, blue = image.rgb[index : index + 3]
    return red, green, blue


def _color_distance(
    left: tuple[int, int, int],
    right: tuple[int, int, int],
) -> float:
    return sum(abs(a - b) for a, b in zip(left, right)) / 3.0


def _median(values) -> int:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return int(ordered[middle])
    return round((ordered[middle - 1] + ordered[middle]) / 2)


def _smooth_signature(
    canvas: list[int],
    columns: int,
    rows: int,
) -> tuple[int, ...]:
    result = []
    for y in range(rows):
        for x in range(columns):
            total = count = 0
            for sample_y in range(max(0, y - 1), min(rows, y + 2)):
                for sample_x in range(max(0, x - 1), min(columns, x + 2)):
                    total += canvas[sample_y * columns + sample_x]
                    count += 1
            result.append(round(total / count))
    return tuple(result)
