from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from games.balatro.bonds.diagnostics import bond_strategy_diagnostics
from games.balatro.build.profile import BalatroBuildProfiler, BuildProfile


_INTERACTION_RELATIONS = ("requires", "amplifies", "scales_with")


def _count_payload(items) -> dict[str, int]:
    return {str(key): int(value) for key, value in items}


def _strength_payload(items) -> dict[str, float]:
    return {str(key): float(value) for key, value in items}


def _effect_payload(descriptor) -> dict[str, Any]:
    return {
        "source": str(descriptor.source),
        "kind": str(descriptor.kind),
        "produces": sorted(str(value) for value in descriptor.produces),
        "requires": sorted(str(value) for value in descriptor.requires),
        "amplifies": sorted(str(value) for value in descriptor.amplifies),
        "scales_with": sorted(str(value) for value in descriptor.scales_with),
        "transforms": sorted(str(value) for value in descriptor.transforms),
    }


def build_profile_log_payload(profile: BuildProfile) -> dict[str, Any]:
    """Return a JSON-safe mechanical build description for durable run logs."""
    return {
        "money": int(profile.money),
        "ante": int(profile.ante),
        "joker_slots": int(profile.joker_slots),
        "free_joker_slots": int(profile.free_joker_slots),
        "consumable_slots": int(profile.consumable_slots),
        "free_consumable_slots": int(profile.free_consumable_slots),
        "deck_size": int(profile.deck_size),
        "rank_counts": _count_payload(profile.rank_counts),
        "suit_counts": _count_payload(profile.suit_counts),
        "enhancement_counts": _count_payload(profile.enhancement_counts),
        "seal_counts": _count_payload(profile.seal_counts),
        "edition_counts": _count_payload(profile.edition_counts),
        "hand_levels": _count_payload(profile.hand_levels),
        "jokers": [str(value) for value in profile.joker_names],
        "consumables": [str(value) for value in profile.consumable_names],
        "feature_strengths": _strength_payload(profile.feature_strengths),
        "effects": [_effect_payload(item) for item in profile.effects],
    }


def detected_build_synergies(profile: BuildProfile) -> list[dict[str, Any]]:
    """Expose behavior-backed interactions supported by current public state."""
    strengths = dict(profile.feature_strengths)
    detected: list[dict[str, Any]] = []
    for descriptor in profile.effects:
        for relation in _INTERACTION_RELATIONS:
            for feature in sorted(getattr(descriptor, relation)):
                strength = float(strengths.get(feature, 0.0))
                if strength <= 0.0:
                    continue
                detected.append(
                    {
                        "source": str(descriptor.source),
                        "relation": relation,
                        "feature": str(feature),
                        "feature_strength": strength,
                    }
                )
    return sorted(
        detected,
        key=lambda item: (item["source"], item["relation"], item["feature"]),
    )


def _strategy_identity(payload: dict[str, Any] | None) -> tuple[Any, Any]:
    if payload is None:
        return None, None
    candidates = tuple(
        (
            candidate.get("strategy_id"),
            candidate.get("commitment"),
            bool(candidate.get("pinned")),
        )
        for candidate in payload.get("strategy_candidates", ())
        if isinstance(candidate, dict)
    )
    return payload.get("pinned_strategy"), candidates


@dataclass(frozen=True)
class PreparedBondBuildLog:
    """One not-yet-durable Bond/build event prepared for a guarded decision."""

    payload: dict[str, Any]
    signature: str
    profile_payload: dict[str, Any]
    bond_strategy_payload: dict[str, Any]
    tracker: "BondBuildLogTracker" = field(repr=False, compare=False)

    def commit(self) -> None:
        self.tracker.commit(self)


class BondBuildLogTracker:
    """Prepare canonical Bond telemetry and deduplicate only durable events."""

    def __init__(
        self,
        *,
        profiler: BalatroBuildProfiler | None = None,
        strategy_diagnostics: Callable[[Any], dict[str, Any]] = bond_strategy_diagnostics,
    ) -> None:
        self.profiler = profiler or BalatroBuildProfiler()
        self.strategy_diagnostics = strategy_diagnostics
        self._last_signature: str | None = None
        self._last_profile: dict[str, Any] | None = None
        self._last_bond_strategy: dict[str, Any] | None = None

    @staticmethod
    def _signature(
        profile_payload: dict[str, Any],
        bond_strategy_payload: dict[str, Any],
        synergies: list[dict[str, Any]],
    ) -> str:
        structural_profile = dict(profile_payload)
        structural_profile.pop("money", None)
        return json.dumps(
            {
                "profile": structural_profile,
                "bond_strategy": bond_strategy_payload,
                "detected_synergies": synergies,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _transition(
        previous: dict[str, Any] | None,
        current: dict[str, Any],
    ) -> str:
        if previous is None:
            return "INITIAL"
        if _strategy_identity(previous) != _strategy_identity(current):
            return "STRATEGY_CHANGED"
        return "BUILD_UPDATED"

    @staticmethod
    def _changed_fields(
        previous: dict[str, Any] | None,
        current: dict[str, Any],
    ) -> list[str]:
        if previous is None:
            return sorted(key for key in current if key != "money")
        return sorted(
            key
            for key, value in current.items()
            if key != "money" and previous.get(key) != value
        )

    def prepare(self, state) -> PreparedBondBuildLog | None:
        profile = self.profiler.profile(state)
        profile_payload = build_profile_log_payload(profile)
        bond_strategy_payload = self.strategy_diagnostics(state)
        synergies = detected_build_synergies(profile)
        signature = self._signature(profile_payload, bond_strategy_payload, synergies)
        if signature == self._last_signature:
            return None

        payload = {
            "transition": self._transition(
                self._last_bond_strategy,
                bond_strategy_payload,
            ),
            "changed_fields": self._changed_fields(
                self._last_profile,
                profile_payload,
            ),
            "profile": profile_payload,
            "bond_strategy": bond_strategy_payload,
            "detected_synergies": synergies,
        }
        return PreparedBondBuildLog(
            payload=payload,
            signature=signature,
            profile_payload=profile_payload,
            bond_strategy_payload=bond_strategy_payload,
            tracker=self,
        )

    def commit(self, prepared: PreparedBondBuildLog) -> None:
        if prepared.tracker is not self:
            raise ValueError("prepared Bond/build event belongs to another tracker")
        self._last_signature = prepared.signature
        self._last_profile = prepared.profile_payload
        self._last_bond_strategy = prepared.bond_strategy_payload

    def observe(self, state) -> dict[str, Any] | None:
        """Immediate convenience path for deterministic callers."""
        prepared = self.prepare(state)
        if prepared is None:
            return None
        self.commit(prepared)
        return prepared.payload
