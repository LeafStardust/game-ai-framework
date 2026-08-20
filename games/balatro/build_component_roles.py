from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from games.balatro.build_health_runtime import RealizedEngineAnalyzer
from games.balatro.strategy import BANNED, BRONZE, GOLD, SILVER


class BuildComponentRole(str, Enum):
    CORE = "CORE"
    ENGINE = "ENGINE"
    SUPPORT = "SUPPORT"
    FILLER = "FILLER"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class BuildComponentAssessment:
    index: int
    name: str
    role: BuildComponentRole
    strategy_id: str | None
    tier: str | None
    realized_engine_id: str | None
    rationale: tuple[str, ...] = ()


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _joker_name(joker: object) -> str:
    return str(
        getattr(joker, "name", None)
        or getattr(joker, "label", None)
        or getattr(joker, "ability_name", None)
        or type(joker).__name__
    )


def _token(joker: object) -> str:
    value = _normalize(_joker_name(joker))
    return value[:-5] if value.endswith("joker") else value


_ENGINE_TOKEN_TO_ID = {
    "hologram": "hologram",
    "blue": "blue_joker",
    "bluejoker": "blue_joker",
    "green": "green_joker",
    "greenjoker": "green_joker",
    "castle": "castle",
    "runner": "runner",
    "redcard": "red_card",
    "burnt": "burnt_joker",
    "burntjoker": "burnt_joker",
    "bull": "cash_scoring",
    "bootstraps": "cash_scoring",
}


def _primary_id(tracker, resolution):
    primary = getattr(resolution, "dominant_strategy_id", None)
    getter = getattr(tracker, "primary_strategy_id", None)
    if callable(getter):
        primary = getter(resolution) or primary
    return primary


class BuildComponentRoleClassifier:
    """Classify each owned Joker relative to the current realized build.

    Roles are structural, not a second score catalogue.  The classifier consumes
    the existing strategy relationship and realized-engine state, preserving their
    provenance in its rationale.
    """

    def __init__(self, *, engine_analyzer: RealizedEngineAnalyzer | None = None) -> None:
        self.engine_analyzer = engine_analyzer or RealizedEngineAnalyzer()

    def classify(self, state, *, strategy_tracker=None) -> tuple[BuildComponentAssessment, ...]:
        engines = {
            engine.engine_id: engine
            for engine in self.engine_analyzer.analyze(state)
        }
        resolution = None
        primary = None
        if strategy_tracker is not None:
            try:
                resolution = strategy_tracker.observe(state)
                primary = _primary_id(strategy_tracker, resolution)
            except (AttributeError, KeyError, TypeError, ValueError):
                resolution = None
                primary = None

        assessments: list[BuildComponentAssessment] = []
        for index, joker in enumerate(getattr(state, "jokers", ()) or ()):
            name = _joker_name(joker)
            token = _token(joker)
            engine_id = _ENGINE_TOKEN_TO_ID.get(token)
            engine = engines.get(engine_id) if engine_id else None
            relation = None
            if strategy_tracker is not None:
                try:
                    relation = strategy_tracker.evaluate_item(state, joker, kind="JOKER")
                except (AttributeError, KeyError, TypeError, ValueError):
                    relation = None

            tier = getattr(relation, "tier", None) if relation is not None else None
            relation_strategy = (
                getattr(relation, "strategy_id", None) if relation is not None else None
            )
            aligned = bool(getattr(relation, "active_alignment", False)) if relation is not None else False
            notes: list[str] = []

            if tier == BANNED and (aligned or relation_strategy == primary):
                role = BuildComponentRole.CONFLICT
                notes.append("current Primary relationship is mechanically Banned")
            elif engine is not None and aligned:
                role = BuildComponentRole.ENGINE
                notes.append(
                    f"realized engine={engine.engine_id} state={engine.state.value} strength={engine.current_strength:.3f}"
                )
            elif aligned and relation_strategy == primary and tier == GOLD:
                role = BuildComponentRole.CORE
                notes.append("Gold component of the current Primary route")
            elif aligned and relation_strategy == primary and tier in {SILVER, BRONZE}:
                role = BuildComponentRole.SUPPORT
                notes.append(f"{tier.title()} component reinforcing the current Primary route")
            elif aligned and tier in {GOLD, SILVER}:
                # Compatible Secondary engines/support remain useful even when they
                # are not the Primary identifier.
                role = BuildComponentRole.ENGINE if engine is not None else BuildComponentRole.SUPPORT
                notes.append("positive component of a compatible active route")
            else:
                role = BuildComponentRole.FILLER
                notes.append("positive/general value may remain, but Joker is not structural to the realized active build")

            assessments.append(
                BuildComponentAssessment(
                    index=index,
                    name=name,
                    role=role,
                    strategy_id=relation_strategy,
                    tier=tier,
                    realized_engine_id=engine_id if engine is not None else None,
                    rationale=tuple(notes),
                )
            )

        return tuple(assessments)
