from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from .card_calibration import load_labeled_identity_manifest
from .card_templates import (
    RGBImage,
    load_rgb_png,
    parse_card_label,
    rank_shape_signature,
)


DEFAULT_MANIFESTS = (
    "balatro-card-identities/labels.json",
    "balatro-card-identities-02/labels.json",
    "balatro-card-identities-03/labels.json",
)


@dataclass(frozen=True)
class LabeledRankImage:
    rank: str
    image: RGBImage


@dataclass(frozen=True)
class RankZoneScore:
    zone: tuple[float, float, float, float]
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


def candidate_rank_zones() -> list[tuple[float, float, float, float]]:
    zones = []
    for left in (0.04, 0.06, 0.08, 0.10):
        for top in (0.08, 0.10, 0.12, 0.14, 0.16, 0.18, 0.20):
            for width in (0.24, 0.28, 0.32, 0.36):
                for height in (0.12, 0.14, 0.16, 0.18, 0.20):
                    if left + width <= 0.48 and top + height < 0.30:
                        zones.append((left, top, width, height))
    return zones


def load_rank_samples(manifests: list[str | Path]) -> list[LabeledRankImage]:
    samples = []
    for manifest in manifests:
        image_paths, labels = load_labeled_identity_manifest(manifest)
        for image_path, label in zip(image_paths, labels):
            rank, _ = parse_card_label(label)
            samples.append(LabeledRankImage(rank, load_rgb_png(image_path)))
    return samples


def score_rank_zone(
    samples: list[LabeledRankImage],
    zone: tuple[float, float, float, float],
) -> RankZoneScore:
    signatures = [rank_shape_signature(sample.image, zone=zone) for sample in samples]
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
                    _signature_distance(signatures[index], signatures[other_index]),
                    other.rank,
                )
            )
        candidates.sort()
        total += 1
        correct += int(candidates[0][1] == sample.rank)

    collisions = 0
    same_distances = []
    cross_distances = []
    for left_index, left in enumerate(samples):
        for right_index in range(left_index + 1, len(samples)):
            right = samples[right_index]
            distance = _signature_distance(signatures[left_index], signatures[right_index])
            if left.rank == right.rank:
                same_distances.append(distance)
            else:
                cross_distances.append(distance)
                collisions += int(distance == 0.0)

    return RankZoneScore(
        zone=zone,
        leave_one_out_correct=correct,
        leave_one_out_total=total,
        exact_cross_rank_collisions=collisions,
        same_rank_distance=sum(same_distances) / max(1, len(same_distances)),
        nearest_cross_rank_distance=min(cross_distances, default=0.0),
    )


def rank_zone_sort_key(score: RankZoneScore) -> tuple:
    return (
        -score.leave_one_out_accuracy,
        score.exact_cross_rank_collisions,
        score.same_rank_distance,
        -score.nearest_cross_rank_distance,
    )


def _signature_distance(left: tuple[int, ...], right: tuple[int, ...]) -> float:
    return sum(abs(a - b) for a, b in zip(left, right)) / (len(left) * 255.0)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find rank-glyph crop zones using labeled Balatro calibration samples."
    )
    parser.add_argument(
        "--manifest",
        action="append",
        dest="manifests",
        help="Calibration manifest. Repeat to supply multiple datasets.",
    )
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    if args.top < 1:
        parser.error("--top must be positive")

    manifests = args.manifests or list(DEFAULT_MANIFESTS)
    try:
        samples = load_rank_samples(manifests)
        scores = [score_rank_zone(samples, zone) for zone in candidate_rank_zones()]
    except (OSError, ValueError) as error:
        parser.error(str(error))

    scores.sort(key=rank_zone_sort_key)
    print(f"Calibration rank samples: {len(samples)}")
    print(f"Candidate rank zones: {len(scores)}")
    for index, score in enumerate(scores[: args.top], start=1):
        left, top, width, height = score.zone
        print(
            f"{index}: zone=({left:.2f}, {top:.2f}, {width:.2f}, {height:.2f}) "
            f"loo={score.leave_one_out_correct}/{score.leave_one_out_total} "
            f"collisions={score.exact_cross_rank_collisions} "
            f"same_distance={score.same_rank_distance:.4f} "
            f"nearest_cross={score.nearest_cross_rank_distance:.4f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
