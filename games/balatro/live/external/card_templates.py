from __future__ import annotations

import json
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path


RANKS = ("A", "K", "Q", "J", "10", "9", "8", "7", "6", "5", "4", "3", "2")
SUITS = ("Hearts", "Diamonds", "Spades", "Clubs")
SUIT_ALIASES = {
    "H": "Hearts",
    "D": "Diamonds",
    "S": "Spades",
    "C": "Clubs",
    "♥": "Hearts",
    "♦": "Diamonds",
    "♠": "Spades",
    "♣": "Clubs",
}
TEMPLATE_VERSION = 2
TEMPLATE_COLUMNS = 10
TEMPLATE_ROWS = 10
RANK_ZONE = (0.06, 0.06, 0.32, 0.20)
SUIT_ZONE = (0.06, 0.27, 0.32, 0.22)
FOREGROUND_THRESHOLD = 35
BACKGROUND_FRACTION = 0.40


@dataclass(frozen=True)
class RGBImage:
    width: int
    height: int
    rgb: bytes


@dataclass(frozen=True)
class CardVisualTemplate:
    label: str
    signature: tuple[int, ...]


@dataclass(frozen=True)
class CardTemplateSet:
    columns: int
    rows: int
    ranks: tuple[CardVisualTemplate, ...]
    suits: tuple[CardVisualTemplate, ...]

    @property
    def rank_coverage(self) -> set[str]:
        return {template.label for template in self.ranks}

    @property
    def suit_coverage(self) -> set[str]:
        return {template.label for template in self.suits}


def parse_card_label(value: str) -> tuple[str, str]:
    token = value.strip()
    if len(token) < 2:
        raise ValueError(f"invalid card label: {value}")

    suit_token = token[-1].upper() if token[-1].isascii() else token[-1]
    suit = SUIT_ALIASES.get(suit_token)
    if suit is None:
        raise ValueError(f"unknown card suit in label: {value}")

    rank = token[:-1].upper()
    if rank not in RANKS:
        raise ValueError(f"unknown card rank in label: {value}")
    return rank, suit


def load_rgb_png(path: str | Path) -> RGBImage:
    data = Path(path).read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"not a PNG file: {path}")

    position = 8
    width = height = None
    bit_depth = color_type = interlace = None
    compressed = bytearray()

    while position + 12 <= len(data):
        length = struct.unpack(">I", data[position : position + 4])[0]
        kind = data[position + 4 : position + 8]
        chunk = data[position + 8 : position + 8 + length]
        position += 12 + length

        if kind == b"IHDR":
            if len(chunk) != 13:
                raise ValueError("invalid PNG IHDR")
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
                ">IIBBBBB", chunk
            )
            if compression != 0 or filter_method != 0:
                raise ValueError("unsupported PNG compression/filter method")
        elif kind == b"IDAT":
            compressed.extend(chunk)
        elif kind == b"IEND":
            break

    if width is None or height is None:
        raise ValueError("PNG is missing IHDR")
    if bit_depth != 8 or color_type != 2 or interlace != 0:
        raise ValueError("card template PNG must be non-interlaced 8-bit RGB")

    raw = zlib.decompress(bytes(compressed))
    stride = width * 3
    expected = height * (stride + 1)
    if len(raw) != expected:
        raise ValueError(
            f"unexpected PNG scanline size: expected {expected}, got {len(raw)}"
        )

    output = bytearray(width * height * 3)
    previous = bytearray(stride)
    source = 0
    destination = 0

    for _ in range(height):
        filter_type = raw[source]
        source += 1
        row = bytearray(raw[source : source + stride])
        source += stride
        _unfilter_scanline(row, previous, filter_type, 3)
        output[destination : destination + stride] = row
        destination += stride
        previous = row

    return RGBImage(width, height, bytes(output))


def rank_shape_signature(
    image: RGBImage,
    zone: tuple[float, float, float, float] = RANK_ZONE,
    *,
    columns: int = TEMPLATE_COLUMNS,
    rows: int = TEMPLATE_ROWS,
    foreground_threshold: int = FOREGROUND_THRESHOLD,
) -> tuple[int, ...]:
    if columns < 1 or rows < 1:
        raise ValueError("signature grid dimensions must be positive")
    if not 0 <= foreground_threshold <= 255:
        raise ValueError("foreground_threshold must be between 0 and 255")

    left, top, right, bottom = _zone_bounds(image, zone)
    background = _background_rgb(image, left, top, right, bottom)
    signature = []

    for grid_y in range(rows):
        y0 = top + (bottom - top) * grid_y // rows
        y1 = max(y0 + 1, top + (bottom - top) * (grid_y + 1) // rows)
        for grid_x in range(columns):
            x0 = left + (right - left) * grid_x // columns
            x1 = max(x0 + 1, left + (right - left) * (grid_x + 1) // columns)
            foreground = count = 0
            for y in range(y0, min(y1, bottom)):
                for x in range(x0, min(x1, right)):
                    pixel = _pixel_rgb(image, x, y)
                    foreground += int(
                        _color_distance(pixel, background) >= foreground_threshold
                    )
                    count += 1
            signature.append(round(255 * foreground / max(1, count)))

    return tuple(signature)


def suit_color_signature(
    image: RGBImage,
    zone: tuple[float, float, float, float] = SUIT_ZONE,
    *,
    foreground_threshold: int = FOREGROUND_THRESHOLD,
) -> tuple[int, int, int]:
    if not 0 <= foreground_threshold <= 255:
        raise ValueError("foreground_threshold must be between 0 and 255")

    left, top, right, bottom = _zone_bounds(image, zone)
    background = _background_rgb(image, left, top, right, bottom)
    pixels = []

    for y in range(top, bottom):
        for x in range(left, right):
            pixel = _pixel_rgb(image, x, y)
            if _color_distance(pixel, background) >= foreground_threshold:
                pixels.append(pixel)

    if not pixels:
        raise ValueError("suit glyph zone contains no foreground pixels")

    return tuple(_median(channel) for channel in zip(*pixels))


def templates_from_labeled_images(
    image_paths: list[str | Path],
    labels: list[str],
    *,
    columns: int = TEMPLATE_COLUMNS,
    rows: int = TEMPLATE_ROWS,
) -> CardTemplateSet:
    if len(image_paths) != len(labels):
        raise ValueError("image and label counts must match")
    if not image_paths:
        raise ValueError("at least one labeled card image is required")

    rank_templates = []
    suit_templates = []
    for image_path, label in zip(image_paths, labels):
        rank, suit = parse_card_label(label)
        image = load_rgb_png(image_path)
        rank_templates.append(
            CardVisualTemplate(
                rank,
                rank_shape_signature(image, columns=columns, rows=rows),
            )
        )
        suit_templates.append(
            CardVisualTemplate(suit, suit_color_signature(image))
        )

    return CardTemplateSet(
        columns,
        rows,
        tuple(rank_templates),
        tuple(suit_templates),
    )


def merge_card_template_sets(
    base: CardTemplateSet | None,
    additions: CardTemplateSet,
) -> CardTemplateSet:
    if base is None:
        return additions
    if base.columns != additions.columns or base.rows != additions.rows:
        raise ValueError("card template grid dimensions do not match")
    return CardTemplateSet(
        base.columns,
        base.rows,
        base.ranks + additions.ranks,
        base.suits + additions.suits,
    )


def save_card_template_set(path: str | Path, templates: CardTemplateSet) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": TEMPLATE_VERSION,
        "columns": templates.columns,
        "rows": templates.rows,
        "rank_feature": "binary-glyph-shape",
        "suit_feature": "glyph-median-rgb",
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
        if version == 1:
            raise ValueError(
                "legacy card template version 1 must be rebuilt from labeled identity crops"
            )
        raise ValueError("unsupported card template version")

    columns = int(payload["columns"])
    rows = int(payload["rows"])
    rank_expected = columns * rows

    def parse_templates(
        kind: str,
        expected: int,
    ) -> tuple[CardVisualTemplate, ...]:
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


def coverage_report(templates: CardTemplateSet) -> dict:
    rank_coverage = templates.rank_coverage
    suit_coverage = templates.suit_coverage
    return {
        "ranks": sorted(rank_coverage, key=RANKS.index),
        "suits": sorted(suit_coverage, key=SUITS.index),
        "missing_ranks": [rank for rank in RANKS if rank not in rank_coverage],
        "missing_suits": [suit for suit in SUITS if suit not in suit_coverage],
        "complete": rank_coverage == set(RANKS) and suit_coverage == set(SUITS),
    }


def _zone_bounds(
    image: RGBImage,
    zone: tuple[float, float, float, float],
) -> tuple[int, int, int, int]:
    left_ratio, top_ratio, width_ratio, height_ratio = zone
    if (
        left_ratio < 0.0
        or top_ratio < 0.0
        or width_ratio <= 0.0
        or height_ratio <= 0.0
        or left_ratio + width_ratio > 1.0
        or top_ratio + height_ratio > 1.0
    ):
        raise ValueError("signature zone must fit inside image")

    left = round(left_ratio * image.width)
    top = round(top_ratio * image.height)
    right = min(
        image.width,
        max(left + 1, round((left_ratio + width_ratio) * image.width)),
    )
    bottom = min(
        image.height,
        max(top + 1, round((top_ratio + height_ratio) * image.height)),
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
    sample_count = max(1, round(len(pixels) * BACKGROUND_FRACTION))
    brightest = sorted(pixels, key=sum, reverse=True)[:sample_count]
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


def _unfilter_scanline(
    row: bytearray,
    previous: bytearray,
    filter_type: int,
    bytes_per_pixel: int,
) -> None:
    if filter_type == 0:
        return
    if filter_type not in {1, 2, 3, 4}:
        raise ValueError(f"unsupported PNG filter type: {filter_type}")

    for index in range(len(row)):
        left = row[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        up = previous[index]
        up_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        if filter_type == 1:
            predictor = left
        elif filter_type == 2:
            predictor = up
        elif filter_type == 3:
            predictor = (left + up) // 2
        else:
            predictor = _paeth(left, up, up_left)
        row[index] = (row[index] + predictor) & 0xFF


def _paeth(left: int, up: int, up_left: int) -> int:
    estimate = left + up - up_left
    left_distance = abs(estimate - left)
    up_distance = abs(estimate - up)
    upper_left_distance = abs(estimate - up_left)
    if left_distance <= up_distance and left_distance <= upper_left_distance:
        return left
    if up_distance <= upper_left_distance:
        return up
    return up_left
