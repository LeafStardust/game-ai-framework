from __future__ import annotations

from dataclasses import dataclass

from .capture import BalatroFrame
from .viewport import BalatroViewport, FrameRegion, NormalizedRect


UNKNOWN_PHASE = "UNKNOWN"


@dataclass(frozen=True)
class ColorGridSignature:
    columns: int
    rows: int
    values: tuple[int, ...]

    def __post_init__(self) -> None:
        expected = self.columns * self.rows * 3
        if self.columns <= 0 or self.rows <= 0:
            raise ValueError("signature grid dimensions must be positive")
        if len(self.values) != expected:
            raise ValueError(
                f"signature expected {expected} channel values, got {len(self.values)}"
            )

    @classmethod
    def from_region(
        cls,
        region: FrameRegion,
        *,
        columns: int = 24,
        rows: int = 14,
    ) -> ColorGridSignature:
        if columns <= 0 or rows <= 0:
            raise ValueError("signature grid dimensions must be positive")

        values: list[int] = []
        for row in range(rows):
            top = row * region.height / rows
            bottom = (row + 1) * region.height / rows
            for column in range(columns):
                left = column * region.width / columns
                right = (column + 1) * region.width / columns
                values.extend(
                    cls._sample_cell(
                        region,
                        left,
                        top,
                        right,
                        bottom,
                    )
                )

        return cls(columns, rows, tuple(values))

    def distance(self, other: ColorGridSignature) -> float:
        return self.weighted_distance(other)

    def weighted_distance(
        self,
        other: ColorGridSignature,
        weights: tuple[float, ...] | None = None,
    ) -> float:
        self._validate_comparison(other, weights)
        active_weights = weights or tuple(1.0 for _ in self.values)
        total_weight = sum(active_weights)
        difference = sum(
            weight * abs(left - right)
            for left, right, weight in zip(
                self.values,
                other.values,
                active_weights,
            )
        )
        return difference / (total_weight * 255.0)

    def relative_values(self) -> tuple[float, ...]:
        cell_count = self.columns * self.rows
        channel_means = tuple(
            sum(self.values[channel::3]) / cell_count
            for channel in range(3)
        )
        return tuple(
            value - channel_means[index % 3]
            for index, value in enumerate(self.values)
        )

    def relative_weighted_distance(
        self,
        other: ColorGridSignature,
        weights: tuple[float, ...] | None = None,
    ) -> float:
        self._validate_comparison(other, weights)
        active_weights = weights or tuple(1.0 for _ in self.values)
        total_weight = sum(active_weights)
        left_values = self.relative_values()
        right_values = other.relative_values()
        difference = sum(
            weight * abs(left - right)
            for left, right, weight in zip(
                left_values,
                right_values,
                active_weights,
            )
        )
        return difference / (total_weight * 510.0)

    def to_dict(self) -> dict:
        return {
            "columns": self.columns,
            "rows": self.rows,
            "values": list(self.values),
        }

    @classmethod
    def from_dict(cls, value: dict) -> ColorGridSignature:
        return cls(
            columns=int(value["columns"]),
            rows=int(value["rows"]),
            values=tuple(int(item) for item in value["values"]),
        )

    def _validate_comparison(
        self,
        other: ColorGridSignature,
        weights: tuple[float, ...] | None,
    ) -> None:
        if self.columns != other.columns or self.rows != other.rows:
            raise ValueError("signature grid dimensions must match")
        if weights is not None and len(weights) != len(self.values):
            raise ValueError("signature distance weights must match channel values")
        if weights is not None and sum(weights) <= 0:
            raise ValueError("signature distance weights must have positive total weight")

    @staticmethod
    def _sample_cell(
        region: FrameRegion,
        left: float,
        top: float,
        right: float,
        bottom: float,
    ) -> tuple[int, int, int]:
        positions = (
            (0.25, 0.25),
            (0.75, 0.25),
            (0.50, 0.50),
            (0.25, 0.75),
            (0.75, 0.75),
        )
        red = green = blue = 0

        for x_fraction, y_fraction in positions:
            x = min(
                region.width - 1,
                max(0, int(left + (right - left) * x_fraction)),
            )
            y = min(
                region.height - 1,
                max(0, int(top + (bottom - top) * y_fraction)),
            )
            index = (y * region.width + x) * 4
            blue += region.bgra[index]
            green += region.bgra[index + 1]
            red += region.bgra[index + 2]

        count = len(positions)
        return (
            round(red / count),
            round(green / count),
            round(blue / count),
        )


@dataclass(frozen=True)
class PhaseTemplate:
    phase: str
    signature: ColorGridSignature
    region: NormalizedRect = NormalizedRect(0.0, 0.0, 1.0, 1.0)
    max_distance: float = 0.18

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "region": {
                "left": self.region.left,
                "top": self.region.top,
                "width": self.region.width,
                "height": self.region.height,
            },
            "max_distance": self.max_distance,
            "signature": self.signature.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: dict) -> PhaseTemplate:
        region = value.get("region") or {}
        return cls(
            phase=str(value["phase"]),
            region=NormalizedRect(
                float(region.get("left", 0.0)),
                float(region.get("top", 0.0)),
                float(region.get("width", 1.0)),
                float(region.get("height", 1.0)),
            ),
            max_distance=float(value.get("max_distance", 0.18)),
            signature=ColorGridSignature.from_dict(value["signature"]),
        )


@dataclass(frozen=True)
class PhaseDetection:
    phase: str
    confidence: float
    distance: float
    wins: float = 0.0
    margin: float = 0.0


@dataclass(frozen=True)
class _PhaseMatch:
    template: PhaseTemplate
    distance: float
    wins: float
    margin: float


class BalatroVisualPhaseRecognizer:
    """Recognizes broad Balatro UI phases from externally captured pixels."""

    def __init__(self, templates: list[PhaseTemplate] | None = None):
        self.templates = list(templates or [])
        self._weight_cache: dict[
            tuple[str, str, int, int, NormalizedRect],
            tuple[float, ...] | None,
        ] = {}

    def add_template(self, template: PhaseTemplate) -> None:
        self.templates.append(template)
        self._weight_cache.clear()

    def template_from_frame(
        self,
        phase: str,
        frame: BalatroFrame,
        *,
        region: NormalizedRect = NormalizedRect(0.0, 0.0, 1.0, 1.0),
        columns: int = 24,
        rows: int = 14,
        max_distance: float = 0.18,
    ) -> PhaseTemplate:
        viewport = BalatroViewport(frame)
        signature = ColorGridSignature.from_region(
            viewport.crop(region),
            columns=columns,
            rows=rows,
        )
        return PhaseTemplate(
            phase=phase,
            signature=signature,
            region=region,
            max_distance=max_distance,
        )

    def rank(self, frame: BalatroFrame) -> list[PhaseDetection]:
        return [
            PhaseDetection(
                match.template.phase,
                max(0.0, 1.0 - match.distance),
                match.distance,
                match.wins,
                match.margin,
            )
            for match in self._best_match_per_phase(frame)
        ]

    def detect(self, frame: BalatroFrame) -> PhaseDetection:
        matches = self._best_match_per_phase(frame)
        if not matches:
            return PhaseDetection(UNKNOWN_PHASE, 0.0, 1.0)

        best = matches[0]
        if best.distance > best.template.max_distance:
            return PhaseDetection(
                UNKNOWN_PHASE,
                max(0.0, 1.0 - best.distance),
                best.distance,
                best.wins,
                best.margin,
            )

        return PhaseDetection(
            best.template.phase,
            max(0.0, 1.0 - best.distance),
            best.distance,
            best.wins,
            best.margin,
        )

    def _best_match_per_phase(self, frame: BalatroFrame) -> list[_PhaseMatch]:
        if not self.templates:
            return []

        geometry = self._primary_geometry()
        compatible = [
            template
            for template in self.templates
            if self._geometry(template) == geometry
        ]
        grouped = {
            phase: [template for template in compatible if template.phase == phase]
            for phase in sorted({template.phase for template in compatible})
        }
        if not grouped:
            return []

        sample = compatible[0]
        candidate = ColorGridSignature.from_region(
            BalatroViewport(frame).crop(sample.region),
            columns=sample.signature.columns,
            rows=sample.signature.rows,
        )

        if len(grouped) == 1:
            phase = next(iter(grouped))
            template, distance = self._nearest(
                grouped[phase],
                candidate,
                None,
            )
            return [_PhaseMatch(template, distance, 0.0, 0.0)]

        wins = {phase: 0.0 for phase in grouped}
        margins = {phase: 0.0 for phase in grouped}
        distances: dict[str, list[float]] = {phase: [] for phase in grouped}
        phases = sorted(grouped)

        for left_index, left_phase in enumerate(phases):
            for right_phase in phases[left_index + 1:]:
                weights = self._pair_weights(
                    left_phase,
                    right_phase,
                    grouped[left_phase],
                    grouped[right_phase],
                )
                _, left_distance = self._nearest(
                    grouped[left_phase],
                    candidate,
                    weights,
                )
                _, right_distance = self._nearest(
                    grouped[right_phase],
                    candidate,
                    weights,
                )

                distances[left_phase].append(left_distance)
                distances[right_phase].append(right_distance)
                difference = right_distance - left_distance
                margins[left_phase] += difference
                margins[right_phase] -= difference

                if abs(difference) <= 1e-9:
                    wins[left_phase] += 0.5
                    wins[right_phase] += 0.5
                elif difference > 0:
                    wins[left_phase] += 1.0
                else:
                    wins[right_phase] += 1.0

        matches = []
        for phase, templates in grouped.items():
            representative = min(
                templates,
                key=lambda template: self._comparison_distance(
                    template.signature,
                    candidate,
                    None,
                ),
            )
            phase_distances = distances[phase]
            average_distance = sum(phase_distances) / len(phase_distances)
            matches.append(
                _PhaseMatch(
                    representative,
                    average_distance,
                    wins[phase],
                    margins[phase],
                )
            )

        return sorted(
            matches,
            key=lambda match: (
                -match.wins,
                -match.margin,
                match.distance,
            ),
        )

    def _nearest(
        self,
        templates: list[PhaseTemplate],
        candidate: ColorGridSignature,
        weights: tuple[float, ...] | None,
    ) -> tuple[PhaseTemplate, float]:
        matches = [
            (
                template,
                self._comparison_distance(
                    template.signature,
                    candidate,
                    weights,
                ),
            )
            for template in templates
        ]
        return min(matches, key=lambda item: item[1])

    @staticmethod
    def _comparison_distance(
        template: ColorGridSignature,
        candidate: ColorGridSignature,
        weights: tuple[float, ...] | None,
    ) -> float:
        relative = template.relative_weighted_distance(candidate, weights)
        raw = template.weighted_distance(candidate, weights)
        return 0.85 * relative + 0.15 * raw

    def _pair_weights(
        self,
        left_phase: str,
        right_phase: str,
        left_templates: list[PhaseTemplate],
        right_templates: list[PhaseTemplate],
    ) -> tuple[float, ...] | None:
        sample = left_templates[0]
        phase_key = tuple(sorted((left_phase, right_phase)))
        key = (
            phase_key[0],
            phase_key[1],
            sample.signature.columns,
            sample.signature.rows,
            sample.region,
        )
        if key in self._weight_cache:
            return self._weight_cache[key]

        left_features = [
            template.signature.relative_values()
            for template in left_templates
        ]
        right_features = [
            template.signature.relative_values()
            for template in right_templates
        ]
        weights = []

        for index in range(len(sample.signature.values)):
            left_values = [values[index] for values in left_features]
            right_values = [values[index] for values in right_features]
            left_mean = sum(left_values) / len(left_values)
            right_mean = sum(right_values) / len(right_values)
            within = (
                sum(abs(value - left_mean) for value in left_values)
                + sum(abs(value - right_mean) for value in right_values)
            ) / (len(left_values) + len(right_values))
            between = abs(left_mean - right_mean)
            weight = (between + 1.0) / (within + 4.0)
            weights.append(min(8.0, max(0.05, weight)))

        total = sum(weights)
        scale = len(weights) / total
        normalized = tuple(weight * scale for weight in weights)
        self._weight_cache[key] = normalized
        return normalized

    def _primary_geometry(self) -> tuple[int, int, NormalizedRect]:
        counts: dict[tuple[int, int, NormalizedRect], int] = {}
        for template in self.templates:
            key = self._geometry(template)
            counts[key] = counts.get(key, 0) + 1
        return max(counts, key=counts.get)

    @staticmethod
    def _geometry(template: PhaseTemplate) -> tuple[int, int, NormalizedRect]:
        return (
            template.signature.columns,
            template.signature.rows,
            template.region,
        )
