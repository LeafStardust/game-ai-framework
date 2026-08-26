from __future__ import annotations

"""Bounded D1-style whole-blind survival projection for SHOP Build Health.

SHOP has no visible current hand, so the live D1 planner cannot be called directly.
This adapter samples only the unordered public owned-deck composition to construct a
small deterministic set of possible opening hands, then runs the same
``LiveBlindClearPlanner`` used by D1 from each sampled opening. No serialized draw
order, RNG state, seed, or future shop information is consulted.

The adapter is deliberately production-only: custom/injected Build Health scorers
retain the generic capacity estimator used by deterministic unit tests and offline
callers. If the bounded planner cannot complete, the generic estimator remains the
fail-safe rather than blocking SHOP decisions.

Only the real current SHOP may launch this bounded D1 projection. Internal
candidate/replacement states created while D2/D14 is comparing hypothetical Joker
transitions carry ``_rw_internal_build_health_projection`` and retain the generic
Build Health estimate. This prevents D1 expectimax from multiplying underneath
D2/D14 while preserving one real-state survival assessment.
"""

from copy import deepcopy
from types import SimpleNamespace

from games.balatro.build_health_runtime import RuntimeBuildHealthEvaluator
from games.balatro.live.blind_clear_planner import (
    LiveBlindClearPlanner,
    PlannerSearchBudgetExceeded,
)
from games.balatro.live.draw_model import PublicDeckComposition
from games.balatro.live.draw_outcomes import PublicDrawOutcomeModel
from games.balatro.scoring import BalatroScorer


_OPENING_SAMPLE_COUNT = 4
_CHILD_DRAW_SAMPLE_COUNT = 2
_PLANNER_MAX_NODES = 96


def _positive_int(value, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return int(default)
    return parsed if parsed > 0 else int(default)


def _round_hands(state) -> int:
    for key in ("hands_per_round", "hands", "base_hands"):
        value = getattr(state, key, None)
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            return parsed
    # Red/White baseline and legacy BalatroState default.
    return 4


def _round_discards(state) -> int:
    for key in ("discards_per_round", "discards", "base_discards"):
        value = getattr(state, key, None)
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed >= 0:
            return parsed
    # Red/White baseline and legacy BalatroState default.
    return 3


def _opening_size(state, population: int) -> int:
    return min(
        max(0, int(population)),
        _positive_int(getattr(state, "hand_size", None), 8),
    )


def _public_owned_cards(state) -> list:
    owned = getattr(state, "owned_deck", None)
    if owned is not None:
        return list(owned)
    return list(getattr(state, "deck", ()) or ())


def _opening_state(state, *, target: int, hands: int, opening, composition, model):
    projected = deepcopy(state)
    projected.phase = "SELECTING_HAND"
    projected.score = 0
    projected.blind_score = int(target)
    projected.blind = SimpleNamespace(requirement=int(target))
    projected.boss_name = None
    projected.boss_blind_state_observed = False
    projected.boss_blind_hands = set()
    projected.boss_blind_only_hand = None
    projected.hands_remaining = int(hands)
    projected.discards_remaining = _round_discards(state)
    projected.discards_used = 0
    projected.round_hand_play_counts = {
        hand: 0
        for hand in (getattr(projected, "round_hand_play_counts", {}) or {})
    }
    projected.hand = [model.card_from_signature(signature) for signature in opening.cards]
    projected.deck = model.remaining_cards(composition, opening)
    return projected


def bounded_shop_clear_probability(
    state,
    *,
    target: float,
    hands: int | None = None,
) -> float | None:
    """Estimate next-blind P(clear) using bounded public-state D1 expectimax.

    ``None`` means the bounded projection was unavailable; callers should retain
    their pre-existing conservative/fallback survival estimate.
    """

    if str(getattr(state, "phase", "")).upper() != "SHOP":
        return None

    try:
        target_int = int(round(float(target)))
    except (TypeError, ValueError):
        return None
    if target_int <= 0:
        return None

    cards = _public_owned_cards(state)
    if not cards:
        return None

    composition = PublicDeckComposition.from_cards(cards)
    opening_size = _opening_size(state, composition.total_cards)
    if opening_size <= 0:
        return None

    opening_model = PublicDrawOutcomeModel(
        exact_combination_limit=1,
        sample_count=_OPENING_SAMPLE_COUNT,
        seed=0,
    )
    try:
        openings = opening_model.distribution(composition, opening_size)
    except (TypeError, ValueError):
        return None

    round_hands = _positive_int(hands, _round_hands(state))
    total_probability = 0.0
    covered_probability = 0.0

    for opening in openings.outcomes:
        branch = _opening_state(
            state,
            target=target_int,
            hands=round_hands,
            opening=opening,
            composition=composition,
            model=opening_model,
        )
        child_draws = PublicDrawOutcomeModel(
            exact_combination_limit=1,
            sample_count=_CHILD_DRAW_SAMPLE_COUNT,
            seed=0,
        )
        planner = LiveBlindClearPlanner(
            draw_outcomes=child_draws,
            play_width=2,
            discard_width=1,
            child_play_width=1,
            child_discard_width=0,
            horizon=round_hands,
            max_nodes=_PLANNER_MAX_NODES,
        )
        try:
            plan = planner.plan(branch)
        except (
            AttributeError,
            KeyError,
            RuntimeError,
            TypeError,
            ValueError,
            ZeroDivisionError,
            PlannerSearchBudgetExceeded,
        ):
            # Partial opening coverage would bias the aggregate. Fail closed to the
            # generic Build Health estimator unless every sampled opening completed.
            return None

        weight = max(0.0, float(opening.probability))
        covered_probability += weight
        total_probability += weight * max(
            0.0,
            min(1.0, float(plan.value.clear_probability)),
        )

    if covered_probability <= 0.0:
        return None
    return max(0.0, min(1.0, total_probability / covered_probability))


def install_shop_clear_probability_health_policy() -> None:
    """Replace only production SHOP survival with bounded D1 clear probability."""

    if getattr(RuntimeBuildHealthEvaluator, "_shop_clear_probability_installed", False):
        return

    original = RuntimeBuildHealthEvaluator._survival_and_immediate

    def _survival_and_immediate(self, state):
        survival, immediate = original(self, state)
        if str(getattr(state, "phase", "")).upper() != "SHOP":
            return survival, immediate
        if bool(getattr(state, "_rw_internal_build_health_projection", False)):
            # D2/D14 candidate and replacement projections are already hypothetical.
            # Never nest bounded D1 expectimax beneath that hypothetical branch.
            return survival, immediate
        if type(getattr(self, "scorer", None)) is not BalatroScorer:
            # Explicit custom scorers are offline/test contracts, not production D1.
            return survival, immediate

        target = 0.0
        for value in (
            getattr(state, "blind_score", 0),
            getattr(state, "blind_requirement", 0),
            getattr(getattr(state, "blind", None), "requirement", 0),
        ):
            try:
                parsed = float(value or 0)
            except (TypeError, ValueError):
                continue
            if parsed > 0:
                target = parsed
                break
        if target <= 0.0:
            return survival, immediate

        projected = bounded_shop_clear_probability(
            state,
            target=target,
            hands=_round_hands(state),
        )
        if projected is None:
            return survival, immediate
        return projected, immediate

    RuntimeBuildHealthEvaluator._survival_and_immediate = _survival_and_immediate
    RuntimeBuildHealthEvaluator._shop_clear_probability_installed = True
