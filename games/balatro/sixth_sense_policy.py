from __future__ import annotations

from dataclasses import replace

from games.balatro.actions import PLAY_CARDS
from games.balatro.live.hand_action_policy import PACE_PLAY, LiveHandActionPolicy
from games.balatro.strategy import SILVER
from games.balatro import strategy_conditional_relationships as conditional_module


_SIXTH_SENSE = "sixthsensejoker"
_TAROT_CONSUMABLE_ENGINE_JOKERS = frozenset(
    {
        "fortunetellerjoker",
        "cartomancerjoker",
        "hallucinationjoker",
        "eightballjoker",
        "vagabondjoker",
        # Perkeo is not Tarot-specific, but it directly turns the Spectral generated
        # by Sixth Sense into repeatable consumable value and is therefore material
        # consumable infrastructure for this pairing.
        "perkeojoker",
    }
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


def install_sixth_sense_policy() -> None:
    if getattr(conditional_module, "_sixth_sense_policy_installed", False):
        return

    original_conditional = conditional_module.conditional_joker_relationship

    def conditional_joker_relationship(state, strategy_id: str, item: object) -> str:
        if strategy_id == "sixes" and _token(item) == _SIXTH_SENSE:
            if _owned_tokens(state) & _TAROT_CONSUMABLE_ENGINE_JOKERS:
                return SILVER
        return original_conditional(state, strategy_id, item)

    conditional_module.conditional_joker_relationship = conditional_joker_relationship

    original_decide = LiveHandActionPolicy.decide

    def decide(self, state, plans, **kwargs):
        result = original_decide(self, state, plans, **kwargs)

        # Sixth Sense is optional utility, never a survival override. Only divert a
        # PACE_PLAY decision to the first-hand single-6 trigger when that trigger
        # independently satisfies the same D1 pace floor and has room to create its
        # Spectral reward. CLEAR_PATH and PACE_RECOVERY remain untouched.
        if result.mode != PACE_PLAY:
            return result
        if _SIXTH_SENSE not in _owned_tokens(state):
            return result
        if not _first_hand_of_round(state) or not _consumable_slot_available(state):
            return result
        if _is_single_six_play(result.action):
            return result

        candidates = []
        for plan in result.plans:
            if not _is_single_six_play(plan.action):
                continue
            projected = float(
                self.evaluator.project_play(state, plan.action).expected_hand_score
            )
            ratio = self._pace_ratio(projected, result.pace_target)
            if ratio + self.EPSILON < self.thresholds.pace_ratio_floor:
                continue
            candidates.append((ratio, projected, plan))

        if not candidates:
            return result

        ratio, projected, selected = max(
            candidates,
            key=lambda item: (
                item[0],
                item[1],
                self._within_type_key(item[2]),
            ),
        )
        return replace(
            result,
            action=selected.action,
            selected_plan=selected,
            selected_immediate_score=projected,
            selected_pace_ratio=ratio,
            confidence=min(float(result.confidence), self._pace_confidence(ratio)),
            rationale=(
                "Sixth Sense opportunity: first-hand single 6 still meets required pace, so harvest the Spectral without sacrificing survival pace",
                *result.rationale,
            ),
        )

    LiveHandActionPolicy.decide = decide
    conditional_module._sixth_sense_policy_installed = True
