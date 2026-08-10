from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from .card_calibration import load_labeled_identity_manifest
from .card_rank_zone_diagnostics import DEFAULT_MANIFESTS, LabeledRankImage, load_rank_samples
from .card_templates import RGBImage, parse_card_label


DEFAULT_HOLDOUT = "balatro-card-unseen-01/labels.json"
GRID_COLUMNS = 24
GRID_ROWS = 12
MAX_SHIFT = 1


@dataclass(frozen=True)
class FixedRankScore:
    zone: tuple[float, float, float, float]
    mode: str
    leave_one_out_correct: int
    leave_one_out_total: int
    exact_cross_rank_collisions: int
    same_rank_distance: float
    nearest_cross_rank_distance: float

    @property
    def leave_one_out_accuracy(self) -> float:
        if not self.leave_one_out_total:
            return 0.0
        return self.leave_one_out_correct / self.leave_one_out_total


def candidate_fixed_rank_zones() -> list[tuple[float, float, float, float]]:
    zones = []
    for left in (0.06, 0.08, 0.10):
        for top in (0.12, 0.14, 0.16):
            for width in (0.28, 0.32, 0.36):
                for height in (0.10, 0.12, 0.14):
                    zones.append((left, top, width, height))
    return zones


def fixed_rank_signature(
    image: RGBImage,
    zone: tuple[float, float, float, float],
    *,
    mode: str,
    columns: int = GRID_COLUMNS,
    rows: int = GRID_ROWS,
) -> tuple[int, ...]:
    if mode not in {"binary", "strength"}:
        raise ValueError("rank feature mode must be binary or strength")
    if columns < 1 or rows < 1:
        raise ValueError("rank feature grid dimensions must be positive")

    left, top, right, bottom = _zone_bounds(image, zone)
    background = _background_rgb(image, left, top, right, bottom)
    strengths = []

    for grid_y in range(rows):
        source_y = min(
            bottom - 1,
            top + int((grid_y + 0.5) * (bottom - top) / rows),
        )
        for grid_x in range(columns):
            source_x = min(
                right - 1,
                left + int((grid_x + 0.5) * (right - left) / columns),
            )
            strengths.append(
                _color_distance(_pixel_rgb(image, source_x, source_y), background)
            )

    maximum = max(strengths, default=0.0)
    if maximum <= 0.0:
        return (0,) * (columns * rows)

    if mode == "binary":
        threshold = maximum * 0.30
        return tuple(255 if value >= threshold else 0 for value in strengths)

    return tuple(round(255 * value / maximum) for value in strengths)


def shifted_rank_distance(
    left: tuple[int, ...],
    right: tuple[int, ...],
    *,
    columns: int = GRID_COLUMNS,
    rows: int = GRID_ROWS,
    max_shift: int = MAX_SHIFT,
) -> float:
    if len(left) != columns * rows or len(right) != columns * rows:
        raise ValueError("rank signature dimensions do not match grid")
    if max_shift < 0:
        raise ValueError("max_shift cannot be negative")

    best = 1.0
    for shift_y in range(-max_shift, max_shift + 1):
        for shift_x in range(-max_shift, max_shift + 1):
            total = 0
            for y in range(rows):
                other_y = y + shift_y
                for x in range(columns):
                    other_x = x + shift_x
                    other_value = 0
                    if 0 <= other_x < columns and 0 <= other_y < rows:
                        other_value = right[other_y * columns + other_x]
                    total += abs(left[y * columns + x] - other_value)
            best = min(best, total / (columns * rows * 255.0))
    return best


def score_fixed_rank_feature(
    samples: list[LabeledRankImage],
    zone: tuple[float, float, float, float],
    *,
    mode: str,
) -> FixedRankScore:
    signatures = [fixed_rank_signature(sample.image, zone, mode=mode) for sample in samples]
    duplicate_ranks = {
        rank
        for rank in {sample.rank for sample in samples}
        if sum(sample.rank == rank for sample in samples) > 1
    }

    correct = total = 0
    for index, sample in enumerate(samples):
        if sample.rank not in duplicate_ranks:
            continue
        candidates = []
        for other_index, other in enumerate(samples):
            if other_index == index:
                continue
            candidates.append(
                (
                    shifted_rank_distance(signatures[index], signatures[other_index]),
                    other.rank,
                )
            )
        candidates.sort()
        total += 1
        correct += int(candidates[0][1] == sample.rank)

    collisions = 0
    same_distances = []
    cross_distances = []
    for left_index, left_sample in enumerate(samples):
        for right_index in range(left_index + 1, len(samples)):
            right_sample = samples[right_index]
            distance = shifted_rank_distance(signatures[left_index], signatures[right_index])
            if left_sample.rank == right_sample.rank:
                same_distances.append(distance)
            else:
                cross_distances.append(distance)
                collisions += int(distance == 0.0)

    return FixedRankScore(
        zone=zone,
        mode=mode,
        leave_one_out_correct=correct,
        leave_one_out_total=total,
        exact_cross_rank_collisions=collisions,
        same_rank_distance=sum(same_distances) / max(1, len(same_distances)),
        nearest_cross_rank_distance=min(cross_distances, default=0.0),
    )


def fixed_rank_sort_key(score: FixedRankScore) -> tuple:
    return (
        -score.leave_one_out_accuracy,
        score.exact_cross_rank_collisions,
        score.same_rank_distance,
        -score.nearest_cross_rank_distance,
    )


def evaluate_holdout(
    calibration_samples: list[LabeledRankImage],
    holdout_manifest: str | Path,
    score: FixedRankScore,
) -> tuple[int, int, list[tuple[str, str, float]]]:
    calibration_signatures = [
        fixed_rank_signature(sample.image, score.zone, mode=score.mode)
        for sample in calibration_samples
    ]
    image_paths, labels = load_labeled_identity_manifest(holdout_manifest)
    failures = []
    correct = 0

    for image_path, label in zip(image_paths, labels):
        expected, _ = parse_card_label(label)
        signature = fixed_rank_signature(
            _load_image(image_path),
            score.zone,
            mode=score.mode,
        )
        distances: dict[str, float] = {}
        for sample, template_signature in zip(calibration_samples, calibration_signatures):
            distance = shifted_rank_distance(signature, template_signature)
            current = distances.get(sample.rank)
            if current is None or distance < current:
                distances[sample.rank] = distance
        detected, distance = min(distances.items(), key=lambda item: item[1])
        correct += int(detected == expected)
        if detected != expected:
            failures.append((expected, detected, distance))

    return correct, len(labels), failures


def _load_image(path: str | Path) -> RGBImage:
    from .card_templates import load_rgb_png

    return load_rgb_png(path)


def _zone_bounds(
    image: RGBImage,
    zone: tuple[float, float, float, float],
) -> tuple[int, int, int, int]:
    left_ratio, top_ratio, width_ratio, height_ratio = zone
    left = round(left_ratio * image.width)
    top = round(top_ratio * image.height)
    right = min(image.width, max(left + 1, round((left_ratio + width_ratio) * image.width)))
    bottom = min(image.height, max(top + 1, round((top_ratio + height_ratio) * image.height)))
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
    brightest = sorted(pixels, key=sum, reverse=True)[: max(1, round(len(pixels) * 0.40))]
    return tuple(_median(channel) for channel in zip(*brightest))


def _pixel_rgb(image: RGBImage, x: int, y: int) -> tuple[int, int, int]:
    index = (y * image.width + x) * 3
    red, green, blue = image.rgb[index : index + 3]
    return red, green, blue


def _color_distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> float:
    return sum(abs(a - b) for a, b in zip(left, right)) / 3.0


def _median(values) -> int:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return int(ordered[middle])
    return round((ordered[middle - 1] + ordered[middle]) / 2)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate fixed-position Balatro rank features on calibration data."
    )
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--holdout", default=DEFAULT_HOLDOUT)
    args = parser.parse_args()

    if args.top < 1:
        parser.error("--top must be positive")

    try:
        samples = load_rank_samples(list(DEFAULT_MANIFESTS))
        scores = [
            score_fixed_rank_feature(samples, zone, mode=mode)
            for zone in candidate_fixed_rank_zones()
            for mode in ("binary", "strength")
        ]
        scores.sort(key=fixed_rank_sort_key)
        best = scores[0]
        holdout_correct, holdout_total, holdout_failures = evaluate_holdout(
            samples,
            args.holdout,
            best,
        )
    except (OSError, ValueError) as error:
        parser.error(str(error))

    print(f"Calibration rank samples: {len(samples)}")
    print(f"Candidate fixed features: {len(scores)}")
    for index, score in enumerate(scores[: args.top], start=1):
        left, top, width, height = score.zone
        print(
            f"{index}: mode={score.mode} "
            f"zone=({left:.2f}, {top:.2f}, {width:.2f}, {height:.2f}) "
            f"loo={score.leave_one_out_correct}/{score.leave_one_out_total} "
            f"collisions={score.exact_cross_rank_collisions} "
            f"same_distance={score.same_rank_distance:.4f} "
            f"nearest_cross={score.nearest_cross_rank_distance:.4f}"
        )

    print(
        f"Best calibration-selected feature holdout: "
        f"{holdout_correct}/{holdout_total}"
    )
    for expected, detected, distance in holdout_failures:
        print(
            f"HOLDOUT FAIL: expected={expected} detected={detected} "
            f"distance={distance:.4f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
