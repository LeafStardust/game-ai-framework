from __future__ import annotations

from dataclasses import replace

from games.balatro import strategy_conditional_relationships as relationships
from games.balatro.strategy import GOLD
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
    """Make Pareidolia an activator for genuine face-card scoring routes.

    Pareidolia makes every card a face card, so it is defining Gold evidence for the
    generic Face Cards route. For specialized face routes it becomes Gold only after
    the actual scoring payoff exists (Photograph or Triboulet); Pareidolia alone must
    not manufacture those specialized strategies.

    The existing build-value retention floor remains separate from strategy scoring
    so inherited face-payoff Jokers are not counted twice.
    """
    if getattr(StrategyAwareJokerBuildValueEvaluator, "_pareidolia_face_policy_installed", False):
        return

    original_conditional = relationships.conditional_joker_relationship

    def conditional_joker_relationship(state, strategy_id: str, item: object) -> str:
        base = original_conditional(state, strategy_id, item)
        if _token(item) != _PAREIDOLIA:
            return base

        owned = _owned_tokens(state)
        if strategy_id == "face_cards":
            return GOLD
        if strategy_id == "face_photochad" and "photographjoker" in owned:
            return GOLD
        if strategy_id == "face_triboulet_sock" and "tribouletjoker" in owned:
            return GOLD
        return base

    relationships.conditional_joker_relationship = conditional_joker_relationship

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
    StrategyAwareJokerBuildValueEvaluator._pareidolia_face_policy_installed = True
