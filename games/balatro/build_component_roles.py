from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.model import BondRank, BondRealization
from games.balatro.build_health_runtime import RealizedEngineAnalyzer


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
    bond_id: str | None
    bond_rank: BondRank | None
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


def _source_matches_joker(source: object, joker_token: str) -> bool:
    source_token = _normalize(source)
    if not source_token or not joker_token:
        return False
    source_without_joker = source_token.replace("joker", "")
    return (
        joker_token == source_token
        or joker_token == source_without_joker
        or source_token.startswith(joker_token)
        or source_without_joker.startswith(joker_token)
    )


def _matching_developments(joker: object, developments) -> tuple:
    token = _token(joker)
    matches = []
    for development in developments:
        if any(
            _source_matches_joker(contribution.source, token)
            for contribution in development.contributions
        ):
            matches.append(development)
    return tuple(matches)


def _development_priority(development) -> tuple[float, float, float]:
    realization = {
        BondRealization.DORMANT: 0.0,
        BondRealization.PARTIAL: 1.0,
        BondRealization.ACTIVE: 2.0,
        BondRealization.MATURE: 3.0,
    }.get(development.realization, 0.0)
    return (
        float(max(0, int(development.rank))),
        realization,
        float(development.contribution),
    )


class BuildComponentRoleClassifier:
    """Classify owned Jokers from canonical Bond composition and realized engines.

    This classifier is structural rather than a second value catalogue. A Joker is
    an ENGINE when it participates in a realized scaling engine, CORE when it is a
    direct contributor to a mature/high-rank selected Bond, SUPPORT when it directly
    contributes to another selected Bond, CONFLICT when its only structural Bond is
    rejected by the composition conflict resolver, and FILLER otherwise.
    """

    def __init__(self, *, engine_analyzer: RealizedEngineAnalyzer | None = None) -> None:
        self.engine_analyzer = engine_analyzer or RealizedEngineAnalyzer()

    def classify(self, state, *, strategy_tracker=None) -> tuple[BuildComponentAssessment, ...]:
        # Kept as a compatibility keyword for callers being migrated; categorical
        # strategy state has no authority in the canonical Bond classifier.
        del strategy_tracker

        developments, composition = evaluate_bond_composition(state)
        selected_ids = set(composition.bond_ids)
        conflict_losers = {left for left, _right in composition.conflicts}
        engines = {
            engine.engine_id: engine
            for engine in self.engine_analyzer.analyze(state)
        }

        assessments: list[BuildComponentAssessment] = []
        for index, joker in enumerate(getattr(state, "jokers", ()) or ()):
            name = _joker_name(joker)
            token = _token(joker)
            engine_id = _ENGINE_TOKEN_TO_ID.get(token)
            engine = engines.get(engine_id) if engine_id else None
            matches = _matching_developments(joker, developments)
            selected = tuple(dev for dev in matches if dev.bond_id in selected_ids)
            rejected = tuple(dev for dev in matches if dev.bond_id in conflict_losers)
            structural = max(selected, key=_development_priority) if selected else None
            rejected_structural = (
                max(rejected, key=_development_priority) if rejected else None
            )
            notes: list[str] = []

            if engine is not None:
                role = BuildComponentRole.ENGINE
                notes.append(
                    f"realized engine={engine.engine_id} state={engine.state.value} strength={engine.current_strength:.3f}"
                )
            elif structural is not None:
                mature = structural.realization in {
                    BondRealization.ACTIVE,
                    BondRealization.MATURE,
                }
                high_rank = structural.rank >= BondRank.R3
                if mature or high_rank:
                    role = BuildComponentRole.CORE
                    notes.append(
                        f"direct contributor to selected {structural.bond_id} Bond at {structural.rank.name}/{structural.realization.value}"
                    )
                else:
                    role = BuildComponentRole.SUPPORT
                    notes.append(
                        f"direct contributor to selected {structural.bond_id} Bond at {structural.rank.name}/{structural.realization.value}"
                    )
            elif rejected_structural is not None:
                role = BuildComponentRole.CONFLICT
                notes.append(
                    f"direct contribution belongs to rejected conflicting {rejected_structural.bond_id} Bond"
                )
            else:
                role = BuildComponentRole.FILLER
                notes.append(
                    "positive/general value may remain, but Joker is not structural to the realized Bond composition"
                )

            reference = structural or rejected_structural
            assessments.append(
                BuildComponentAssessment(
                    index=index,
                    name=name,
                    role=role,
                    bond_id=reference.bond_id if reference is not None else None,
                    bond_rank=reference.rank if reference is not None else None,
                    realized_engine_id=engine_id if engine is not None else None,
                    rationale=tuple(notes),
                )
            )

        return tuple(assessments)
