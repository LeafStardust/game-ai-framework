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
        if self.columns != other.columns or self.rows != other.rows:
            raise ValueError("signature grid dimensions must match")

        if weights is None:
            weights = tuple(1.0 for _ in self.values)
        if len(weights) != len(self.values):
            raise ValueError("signature distance weights must match channel values")

        total_weight = sum(weights)
        if total_weight <= 0:
            raise ValueError("signature distance weights must have positive total weight")

        difference = sum(
            weight * abs(left - right)
            for left, right, weight in zip(self.values, other.values, weights)
        )
        return difference / (total_weight * 255.0)

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


class BalatroVisualPhaseRecognizer:
    """Recognizes broad Balatro UI phases from externally captured pixels."""

    def __init__(self, templates: list[PhaseTemplate] | None = None):
        self.templates = list(templates or [])
        self._weight_cache: dict[
            tuple[int, int, NormalizedRect],
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
        matches = self._best_match_per_phase(frame)
        return [
            PhaseDetection(
                template.phase,
                max(0.0, 1.0 - distance),
                distance,
            )
            for template, distance in matches
        ]

    def detect(self, frame: BalatroFrame) -> PhaseDetection:
        matches = self._best_match_per_phase(frame)
        if not matches:
            return PhaseDetection(UNKNOWN_PHASE, 0.0, 1.0)

        best_template, best_distance = matches[0]
        if best_distance > best_template.max_distance:
            return PhaseDetection(
                UNKNOWN_PHASE,
                max(0.0, 1.0 - best_distance),
                best_distance,
            )

        return PhaseDetection(
            best_template.phase,
            max(0.0, 1.0 - best_distance),
            best_distance,
        )

    def _best_match_per_phase(
        self,
        frame: BalatroFrame,
    ) -> list[tuple[PhaseTemplate, float]]:
        if not self.templates:
            return []

        viewport = BalatroViewport(frame)
        best_by_phase: dict[str, tuple[PhaseTemplate, float]] = {}

        for template in self.templates:
            candidate = ColorGridSignature.from_region(
                viewport.crop(template.region),
                columns=template.signature.columns,
                rows=template.signature.rows,
            )
            distance = template.signature.weighted_distance(
                candidate,
                self._shared_weights(template),
            )
            previous = best_by_phase.get(template.phase)
            if previous is None or distance < previous[1]:
                best_by_phase[template.phase] = (template, distance)

        return sorted(
            best_by_phase.values(),
            key=lambda item: item[1],
        )

    def _shared_weights(
        self,
        template: PhaseTemplate,
    ) -> tuple[float, ...] | None:
        key = (
            template.signature.columns,
            template.signature.rows,
            template.region,
        )
        if key in self._weight_cache:
            return self._weight_cache[key]

        compatible = [
            item
            for item in self.templates
            if item.signature.columns == template.signature.columns
            and item.signature.rows == template.signature.rows
            and item.region == template.region
        ]
        phases = sorted({item.phase for item in compatible})
        if len(phases) < 2:
            self._weight_cache[key] = None
            return None

        grouped = {
            phase: [item for item in compatible if item.phase == phase]
            for phase in phases
        }
        weights = []

        for index in range(len(template.signature.values)):
            means = {}
            within_total = 0.0
            sample_count = 0

            for phase, items in grouped.items():
                values = [item.signature.values[index] for item in items]
                mean = sum(values) / len(values)
                means[phase] = mean
                within_total += sum(abs(value - mean) for value in values)
                sample_count += len(values)

            overall_mean = sum(means.values()) / len(means)
            between_phase = sum(
                abs(mean - overall_mean) for mean in means.values()
            ) / len(means)
            within_phase = within_total / sample_count

            weight = (between_phase + 1.0) / (within_phase + 4.0)
            weights.append(min(8.0, max(0.05, weight)))

        total = sum(weights)
        scale = len(weights) / total
        normalized = tuple(weight * scale for weight in weights)
        self._weight_cache[key] = normalized
        return normalized
