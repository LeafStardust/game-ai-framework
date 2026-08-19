from __future__ import annotations

from dataclasses import replace

from games.balatro import strategy_conditional_relationships as conditional_module
from games.balatro.strategy import NEUTRAL, SILVER
from games.balatro.strategy_value import StrategyAwareJokerBuildValueEvaluator


_PAREIDOLIA = "pareidoliajoker"
_PAREIDOLIA_FACE_SUPPORT = frozenset(
    {
        "smileyfacejoker",
        "scaryfacejoker",
        "businesscardjoker",
        "midasmaskjoker",
        "photographjoker",
        "sockandbuskinjoker",
        "reservedparkingjoker",
    }
)


def _token(item: object) -> str:
    return "".join(character for character in type(item).__name__.lower() if character.isalnum())


def _owned_tokens(state) -> frozenset[str]:
    return frozenset(_token(joker) for joker in getattr(state, "jokers", ()) or ())


def _has_pareidolia(state) -> bool:
    return _PAREIDOLIA in _owned_tokens(state)


def install_pareidolia_face_policy() -> None:
    if getattr(conditional_module, "_pareidolia_face_policy_installed", False):
        return

    original_conditional = conditional_module.conditional_joker_relationship

    def conditional_joker_relationship(state, strategy_id: str, item: object) -> str:
        token = _token(item)
        if (
            strategy_id == "face_pareidolia"
            and token in _PAREIDOLIA_FACE_SUPPORT
        ):
            return SILVER if _has_pareidolia(state) else NEUTRAL
        return original_conditional(state, strategy_id, item)

    conditional_module.conditional_joker_relationship = conditional_joker_relationship

    original_evaluate = StrategyAwareJokerBuildValueEvaluator.evaluate

    def evaluate(self, state, joker):
        result = original_evaluate(self, state, joker)
        token = _token(joker)
        if token not in _PAREIDOLIA_FACE_SUPPORT or not _has_pareidolia(state):
            return result

        resolution = self.strategy_tracker.observe(state)
        pareidolia_assessment = resolution.assessment("face_pareidolia")
        if pareidolia_assessment is None or float(pareidolia_assessment.score) <= 0.0:
            return result

        # Pareidolia makes every played card a face card. Once that leaf has real
        # positive evidence, its face-payoff Jokers remain genuine engine pieces
        # even if a broader parent/sibling temporarily wins the primary-id tie.
        # This is a retention floor, not an immortality rule: a materially stronger
        # replacement can still beat the support Joker.
        floor = 6.0
        if float(result.total_gain) >= floor:
            return result
        delta = floor - float(result.total_gain)
        return replace(
            result,
            total_gain=floor,
            strategic_adjustment=float(result.strategic_adjustment) + delta,
            rationale=(
                *result.rationale,
                "Pareidolia leaf active; keep face-payoff Joker as aligned engine support",
                f"Pareidolia support retention floor={floor:.3f}",
            ),
        )

    StrategyAwareJokerBuildValueEvaluator.evaluate = evaluate
    conditional_module._pareidolia_face_policy_installed = True
