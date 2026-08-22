from __future__ import annotations

from dataclasses import replace

from games.balatro.actions import PLAY_CARDS
from games.balatro.live.hand_action_policy import PACE_PLAY, LiveHandActionPolicy


_SIXTH_SENSE = "sixthsensejoker"
_SIXTH_SENSE_RATIONALE = (
    "Sixth Sense opportunity: first-hand single 6 still meets required pace, so harvest the Spectral without sacrificing survival pace"
)


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _token(item: object) -> str:
    type_token = _normalize(type(item).__name__)
    if type_token and type_token not in {"simplenamespace", "object"}:
        return type_token if type_token.endswith("joker") else type_token + "joker"
    for value in (
        getattr(item, "name", ""),
        getattr(item, "label", ""),
        getattr(item, "ability_name", ""),
    ):
        token = _normalize(value)
        if token:
            return token if token.endswith("joker") else token + "joker"
    return type_token


def _owned_tokens(state) -> frozenset[str]:
    return frozenset(_token(joker) for joker in getattr(state, "jokers", ()) or ())


def _first_hand_of_round(state) -> bool:
    counts = getattr(state, "round_hand_play_counts", None)
    if not isinstance(counts, dict):
        return False
    try:
        return not any(int(value or 0) > 0 for value in counts.values())
    except (TypeError, ValueError):
        return False


def _consumable_slot_available(state) -> bool:
    slots = max(0, int(getattr(state, "consumable_slots", 0) or 0))
    if slots <= 0:
        return False
    return len(getattr(state, "consumables", ()) or ()) < slots


def _is_single_six_play(action) -> bool:
    if str(getattr(action, "name", "")) != PLAY_CARDS:
        return False
    cards = tuple(getattr(action, "cards", ()) or ())
    return len(cards) == 1 and str(getattr(cards[0], "rank", "")) == "6"


def _best_non_six_pace_plan(policy, state, result):
    candidates = []
    for plan in result.plans:
        if getattr(plan.action, "name", None) != PLAY_CARDS or _is_single_six_play(plan.action):
            continue
        projected = float(policy.evaluator.project_play(state, plan.action).expected_hand_score)
        ratio = policy._pace_ratio(projected, result.pace_target)
        if ratio + policy.EPSILON < policy.thresholds.pace_ratio_floor:
            continue
        candidates.append((ratio, projected, plan))
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (item[0], item[1], policy._within_type_key(item[2])),
    )


def install_sixth_sense_policy() -> None:
    if getattr(LiveHandActionPolicy, "_sixth_sense_policy_installed", False):
        return

    original_decide = LiveHandActionPolicy.decide

    def decide(self, state, plans, **kwargs):
        result = original_decide(self, state, plans, **kwargs)
        if result.mode != PACE_PLAY:
            return result
        if _SIXTH_SENSE not in _owned_tokens(state) or not _first_hand_of_round(state):
            return result

        slot_available = _consumable_slot_available(state)

        # If D1 independently chose the single 6 while the Spectral slot is full,
        # avoid destroying the 6 whenever another pace-satisfying play exists.
        if not slot_available and _is_single_six_play(result.action):
            fallback = _best_non_six_pace_plan(self, state, result)
            if fallback is None:
                return result
            ratio, projected, selected = fallback
            return replace(
                result,
                action=selected.action,
                selected_plan=selected,
                selected_immediate_score=projected,
                selected_pace_ratio=ratio,
                confidence=min(float(result.confidence), self._pace_confidence(ratio)),
                rationale=(
                    "Sixth Sense preservation: consumable slots are full, so do not destroy a 6 when another play still meets required pace",
                    *result.rationale,
                ),
            )

        if not slot_available:
            return result

        # D1 may already have selected the correct single-6 line. Mark that choice
        # explicitly so telemetry/tests can distinguish intentional Sixth Sense use.
        if _is_single_six_play(result.action):
            if any("Sixth Sense opportunity" in note for note in result.rationale):
                return result
            return replace(
                result,
                rationale=(_SIXTH_SENSE_RATIONALE, *result.rationale),
            )

        candidates = []
        for plan in result.plans:
            if not _is_single_six_play(plan.action):
                continue
            projected = float(self.evaluator.project_play(state, plan.action).expected_hand_score)
            ratio = self._pace_ratio(projected, result.pace_target)
            if ratio + self.EPSILON < self.thresholds.pace_ratio_floor:
                continue
            candidates.append((ratio, projected, plan))

        if not candidates:
            return result

        ratio, projected, selected = max(
            candidates,
            key=lambda item: (item[0], item[1], self._within_type_key(item[2])),
        )
        return replace(
            result,
            action=selected.action,
            selected_plan=selected,
            selected_immediate_score=projected,
            selected_pace_ratio=ratio,
            confidence=min(float(result.confidence), self._pace_confidence(ratio)),
            rationale=(_SIXTH_SENSE_RATIONALE, *result.rationale),
        )

    LiveHandActionPolicy.decide = decide
    LiveHandActionPolicy._sixth_sense_policy_installed = True
