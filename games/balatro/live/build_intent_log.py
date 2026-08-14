from __future__ import annotations

import json
from typing import Any

from games.balatro.build.profile import (
    BalatroBuildProfiler,
    BalatroPlaystyleIntentTracker,
    BuildProfile,
    PlaystyleIntent,
)


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
    """Return a JSON-safe public build description for durable run logs."""
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
        "playstyle_strengths": _strength_payload(profile.playstyle_strengths),
        "effects": [_effect_payload(item) for item in profile.effects],
    }


def playstyle_intent_log_payload(intent: PlaystyleIntent) -> dict[str, Any]:
    return {
        "mode": "LOCKED" if intent.locked else "PIVOTABLE",
        "locked": bool(intent.locked),
        "lock_ante": int(intent.lock_ante) if intent.lock_ante is not None else None,
        "strengths": _strength_payload(intent.strengths),
    }


def detected_build_synergies(profile: BuildProfile) -> list[dict[str, Any]]:
    """Expose behavior-backed interactions whose required feature is present.

    This does not invent pairwise Joker tables. It only reports relationships that
    already exist in B1 effect descriptors and are currently supported by the
    public B2 feature-strength vector.
    """
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
        key=lambda item: (
            item["source"],
            item["relation"],
            item["feature"],
        ),
    )


class BuildIntentLogTracker:
    """Emit structured build/intent telemetry only when the build meaning changes.

    Volatile cash is included in an emitted profile for context but deliberately
    excluded from the change signature. Ordinary score/economy movement therefore
    cannot flood the JSONL stream with duplicate build events.
    """

    def __init__(
        self,
        *,
        profiler: BalatroBuildProfiler | None = None,
        intent_tracker: BalatroPlaystyleIntentTracker | None = None,
    ) -> None:
        self.profiler = profiler or BalatroBuildProfiler()
        self.intent_tracker = intent_tracker or BalatroPlaystyleIntentTracker()
        self._last_signature: str | None = None
        self._last_profile: dict[str, Any] | None = None
        self._last_intent: dict[str, Any] | None = None

    @staticmethod
    def _signature(
        profile_payload: dict[str, Any],
        intent_payload: dict[str, Any],
        synergies: list[dict[str, Any]],
    ) -> str:
        structural_profile = dict(profile_payload)
        structural_profile.pop("money", None)
        return json.dumps(
            {
                "profile": structural_profile,
                "intent": intent_payload,
                "detected_synergies": synergies,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _transition(
        previous_intent: dict[str, Any] | None,
        current_intent: dict[str, Any],
    ) -> str:
        if previous_intent is None:
            return "INITIAL"
        if not previous_intent["locked"] and current_intent["locked"]:
            return "LOCKED"
        if previous_intent["strengths"] != current_intent["strengths"]:
            return "PIVOTED" if not current_intent["locked"] else "BUILD_UPDATED"
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

    def observe(self, state) -> dict[str, Any] | None:
        profile = self.profiler.profile(state)
        intent = self.intent_tracker.resolve(profile)
        profile_payload = build_profile_log_payload(profile)
        intent_payload = playstyle_intent_log_payload(intent)
        synergies = detected_build_synergies(profile)
        signature = self._signature(profile_payload, intent_payload, synergies)

        if signature == self._last_signature:
            return None

        payload = {
            "transition": self._transition(self._last_intent, intent_payload),
            "changed_fields": self._changed_fields(
                self._last_profile,
                profile_payload,
            ),
            "profile": profile_payload,
            "intent": intent_payload,
            "detected_synergies": synergies,
        }
        self._last_signature = signature
        self._last_profile = profile_payload
        self._last_intent = intent_payload
        return payload
