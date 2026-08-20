from __future__ import annotations

from dataclasses import replace

from games.balatro.strategy import GOLD, NEUTRAL, SILVER
from games.balatro import strategy_conditional_relationships as conditional_module
from games.balatro.strategy_value import StrategyAwareJokerBuildValueEvaluator


_ACES_SUPPORT_TOKENS = frozenset({"dnajoker", "fibonaccijoker", "oddtoddjoker"})


def _token(item: object) -> str:
    return "".join(character for character in type(item).__name__.lower() if character.isalnum())


def _has_scholar(state) -> bool:
    return any(_token(joker) == "scholarjoker" for joker in getattr(state, "jokers", ()) or ())


def _has_dna(state) -> bool:
    return any(_token(joker) == "dnajoker" for joker in getattr(state, "jokers", ()) or ())


def install_aces_scholar_policy() -> None:
    if getattr(conditional_module, "_aces_scholar_policy_installed", False):
        return

    original_conditional = conditional_module.conditional_joker_relationship

    def conditional_joker_relationship(state, strategy_id: str, item: object) -> str:
        token = _token(item)
        if strategy_id == "aces" and token == "scholarjoker" and _has_dna(state):
            return GOLD
        if strategy_id == "aces" and token in _ACES_SUPPORT_TOKENS:
            return SILVER if _has_scholar(state) else NEUTRAL
        return original_conditional(state, strategy_id, item)

    conditional_module.conditional_joker_relationship = conditional_joker_relationship

    original_evaluate = StrategyAwareJokerBuildValueEvaluator.evaluate

    def evaluate(self, state, joker):
        result = original_evaluate(self, state, joker)
        if _token(joker) not in _ACES_SUPPORT_TOKENS or not _has_scholar(state):
            return result

        resolution = self.strategy_tracker.observe(state)
        primary_id = resolution.dominant_strategy_id
        primary_getter = getattr(self.strategy_tracker, "primary_strategy_id", None)
        if callable(primary_getter):
            primary_id = primary_getter(resolution)
        if primary_id != "aces":
            return result

        # Scholar is a Silver Aces core by itself. DNA is the pair that promotes
        # Scholar to Gold, so Scholar-backed support still receives a useful open-slot
        # floor while the agent is assembling that stronger Aces package.
        joker_slots = int(getattr(state, "joker_slots", 5) or 5)
        open_slot = len(getattr(state, "jokers", ()) or ()) < joker_slots
        if not open_slot:
            return result

        floor = 4.0
        if float(result.total_gain) >= floor:
            return result
        delta = floor - float(result.total_gain)
        return replace(
            result,
            total_gain=floor,
            strategic_adjustment=float(result.strategic_adjustment) + delta,
            rationale=(
                *result.rationale,
                "Scholar-backed Aces Silver support with open Joker slot receives minimum aligned acquisition value",
                f"Aces support acquisition floor={floor:.3f}",
            ),
        )

    StrategyAwareJokerBuildValueEvaluator.evaluate = evaluate
    conditional_module._aces_scholar_policy_installed = True
