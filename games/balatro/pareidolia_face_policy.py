from __future__ import annotations

from dataclasses import replace

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
    """Protect Pareidolia face payoffs without duplicating inherited tree evidence.

    Face Cards parent evidence is already inherited once when the Pareidolia child
    becomes the active leaf. Reclassifying the same payoff Jokers on the child would
    count them twice (for example Pareidolia + Scary Face becoming 14 instead of 11).
    This policy therefore affects Joker retention/acquisition value only; it does not
    add another conditional strategy relationship.
    """
    if getattr(StrategyAwareJokerBuildValueEvaluator, "_pareidolia_face_policy_installed", False):
        return

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
    StrategyAwareJokerBuildValueEvaluator._pareidolia_face_policy_installed = True
