from __future__ import annotations

"""Run-log calibration policies approved after the 10-attempt Red/White batch.

This module deliberately patches narrow decision surfaces instead of weakening the
underlying universal strategy model. The goals are:

* retain live/scaled Jokers according to their current power;
* allow a strong aligned early Joker to beat a small cash-reserve penalty;
* keep dependent strategy leaves from being seeded by support alone;
* make weak builds prefer Joker development over generic packs; and
* spend more aggressively late when surplus cash is not itself the scoring engine.
"""

from dataclasses import replace

from games.balatro.joker_policy import HOLD, JokerAcquisitionPolicy
from games.balatro.strategy import AVAILABLE, GOLD, SILVER
from games.balatro.strategy_booster_policy import (
    StrategyAwareShopBoosterPolicy,
    StrategyAwareShopRerollPolicy,
)
from games.balatro.strategy_conditional_relationships import (
    StateAwareBalatroStrategyTracker,
)
from games.balatro.strategy_value import StrategyAwareJokerBuildValueEvaluator


def _token(item: object) -> str:
    value = getattr(item, "name", None) or type(item).__name__
    token = "".join(c for c in str(value).lower() if c.isalnum())
    if token.endswith("joker"):
        return token
    class_token = "".join(c for c in type(item).__name__.lower() if c.isalnum())
    if class_token.endswith("joker"):
        return class_token
    return token


def _owned_tokens(state) -> frozenset[str]:
    """Return canonical Joker tokens while supporting name-only live/test objects."""
    tokens: set[str] = set()
    for joker in getattr(state, "jokers", ()) or ():
        token = _token(joker)
        tokens.add(token)
        if token and not token.endswith("joker"):
            tokens.add(f"{token}joker")
    return frozenset(tokens)


def _is_owned_instance(state, joker: object) -> bool:
    return any(joker is owned for owned in getattr(state, "jokers", ()) or ())


def _live_scaler_floor(state, joker: object) -> tuple[float, str] | None:
    """Return a conservative whole-build retention floor from current live power."""
    token = _token(joker)
    money = max(0, int(getattr(state, "money", 0) or 0))

    if token == "bulljoker":
        chips = money * 2
        return 8.0 + min(18.0, chips / 40.0), f"Bull live cash chips=+{chips}"
    if token == "bootstrapsjoker":
        mult = (money // 5) * 2
        return 8.0 + min(18.0, mult / 6.0), f"Bootstraps live cash mult=+{mult}"

    if token in {"greenjoker", "ridethebusjoker", "flashcardjoker"}:
        mult = max(0.0, float(getattr(joker, "mult", 0.0) or 0.0))
        if mult <= 0.0:
            return None
        label = {
            "greenjoker": "Green Joker",
            "ridethebusjoker": "Ride the Bus",
            "flashcardjoker": "Flash Card",
        }[token]
        return 5.0 + min(18.0, mult / 2.5), f"{label} accumulated mult=+{mult:g}"

    if token in {"runnerjoker", "squarejoker"}:
        chips = max(0.0, float(getattr(joker, "chips", 0.0) or 0.0))
        if chips <= 0.0:
            return None
        label = "Runner" if token == "runnerjoker" else "Square Joker"
        return 5.0 + min(18.0, chips / 30.0), f"{label} accumulated chips=+{chips:g}"

    return None


# A specialization may inherit parent support, but support alone must not manufacture
# the child. Each entry lists at least one defining/core token that must already be
# owned before direct child evidence is allowed to become actionable.
_DEPENDENT_LEAF_CORES: dict[str, frozenset[str]] = {
    "high_card_baron_mime": frozenset({"baronjoker", "mimejoker"}),
    "face_photochad": frozenset({"photographjoker"}),
    "face_triboulet_sock": frozenset({"tribouletjoker"}),
    "face_pareidolia": frozenset({"pareidoliajoker"}),
    "face_business_card": frozenset({"businesscardjoker"}),
    "faceless_ride_bus": frozenset({"ridethebusjoker"}),
    "faceless_discard_economy": frozenset({"facelessjoker"}),
    "hearts_bloodstone_oops": frozenset({"bloodstonejoker"}),
    "hearts_bloodstone_retrigger": frozenset({"bloodstonejoker"}),
    "clubs_onyx": frozenset({"onyxagatejoker"}),
    "clubs_seeing_double": frozenset({"seeingdoublejoker"}),
    "flower_pot_splash": frozenset({"flowerpotjoker"}),
    "flower_pot_smeared": frozenset({"flowerpotjoker"}),
    "hologram_dna": frozenset({"hologramjoker"}),
    "hologram_certificate": frozenset({"hologramjoker"}),
    "hologram_marble": frozenset({"hologramjoker"}),
    "cash_bull_bootstraps": frozenset({"bulljoker", "bootstrapsjoker"}),
}


def install_log_batch_calibration_policy() -> None:
    if getattr(StrategyAwareJokerBuildValueEvaluator, "_log_batch_calibration_installed", False):
        return

    # 1) Stateful/live scaler retention.
    original_value_evaluate = StrategyAwareJokerBuildValueEvaluator.evaluate

    def evaluate(self, state, joker):
        result = original_value_evaluate(self, state, joker)
        if not _is_owned_instance(state, joker):
            return result
        live = _live_scaler_floor(state, joker)
        if live is None:
            return result
        floor, note = live
        if float(result.total_gain) >= floor:
            return result
        delta = floor - float(result.total_gain)
        return replace(
            result,
            total_gain=floor,
            strategic_adjustment=float(result.strategic_adjustment) + delta,
            rationale=(
                *result.rationale,
                note,
                f"live scaler retention floor={floor:.3f}; replacement must beat current accumulated power",
            ),
        )

    StrategyAwareJokerBuildValueEvaluator.evaluate = evaluate

    # 2) Early aligned purchases can break the tiny reserve on a weak board.
    original_joker_decide = JokerAcquisitionPolicy.decide

    def joker_decide(self, state, candidate):
        decision = original_joker_decide(self, state, candidate)
        if decision.action != HOLD:
            return decision
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        jokers = list(getattr(state, "jokers", ()) or ())
        slots = int(getattr(state, "joker_slots", 5) or 5)
        if ante > 2 or len(jokers) >= slots or len(jokers) > 1:
            return decision

        transition = self.transition_planner.plan(state, candidate)
        candidate_value = transition.candidate_value
        aligned = bool(
            getattr(candidate_value, "active_alignment", False)
            and getattr(candidate_value, "strategy_tier", None) in {GOLD, SILVER}
        )
        price = self._price(candidate)
        if not aligned or price > int(getattr(state, "money", 0) or 0):
            return decision

        original_thresholds = self.thresholds
        try:
            self.thresholds = replace(
                original_thresholds,
                interest_weight=0.0,
                reserve_weight=0.0,
                minimum_purchase_advantage=min(
                    float(original_thresholds.minimum_purchase_advantage), 0.10
                ),
            )
            override = original_joker_decide(self, state, candidate)
        finally:
            self.thresholds = original_thresholds

        if override.action == HOLD:
            return decision
        return replace(
            override,
            rationale=(
                *override.rationale,
                "early weak-board override: aligned Silver/Gold Joker with a free slot outranks interest/reserve preservation",
            ),
        )

    JokerAcquisitionPolicy.decide = joker_decide

    # 3) Dependency-gated specialization admission.
    original_assess = StateAwareBalatroStrategyTracker.assess

    def assess(self, state):
        assessments = tuple(original_assess(self, state))
        owned = _owned_tokens(state)
        gated = []
        for assessment in assessments:
            cores = _DEPENDENT_LEAF_CORES.get(assessment.strategy_id)
            if cores and not (owned & cores):
                gated.append(
                    replace(
                        assessment,
                        score=0.0,
                        base_score=0.0,
                        status=AVAILABLE,
                        rationale=(
                            *assessment.rationale,
                            "dependent specialization blocked: support cannot seed this leaf without its defining core",
                        ),
                    )
                )
            else:
                gated.append(assessment)
        return tuple(sorted(gated, key=lambda a: (-float(a.score), a.strategy_id)))

    StateAwareBalatroStrategyTracker.assess = assess

    # 4) Weak rosters prioritize Joker development over generic packs.
    original_booster_recommend = StrategyAwareShopBoosterPolicy.recommend

    def booster_recommend(self, state, action):
        recommendation = original_booster_recommend(self, state, action)
        if recommendation.family in {"BUFFOON", "SPECTRAL"}:
            return recommendation
        jokers = list(getattr(state, "jokers", ()) or ())
        if len(jokers) > 2:
            return recommendation
        resolution = self.strategy_tracker.observe(state)
        dominant = resolution.assessment(resolution.dominant_strategy_id)
        score = float(dominant.score) if dominant is not None else 0.0
        if score >= 6.0:
            return recommendation
        factor = 0.55
        discounted_utility = float(recommendation.option_utility) * factor
        resource_cost = (
            float(recommendation.price_penalty)
            + float(recommendation.interest_penalty)
            + float(recommendation.reserve_penalty)
        )
        advantage = discounted_utility - resource_cost
        decision_name = recommendation.decision
        if advantage <= float(self.thresholds.minimum_buy_advantage):
            decision_name = HOLD
        return replace(
            recommendation,
            decision=decision_name,
            option_utility=discounted_utility,
            advantage_over_save=advantage,
            total=self.parent_hold_baseline + advantage,
            rationale=(
                *recommendation.rationale,
                f"weak roster ({len(jokers)} Jokers, dominant score={score:.3f}); generic pack value factor={factor:.2f}",
                "visible Jokers, rerolls, and Buffoon packs take development priority until the board has real scoring capacity",
            ),
        )

    StrategyAwareShopBoosterPolicy.recommend = booster_recommend

    # 5) Late-game boss-readiness pressure: surplus cash should search for power,
    # except when cash itself is the scoring/economy route. Existing Gold economy
    # route stop-loss reserves remain authoritative.
    original_thresholds_for_state = StrategyAwareShopRerollPolicy.thresholds_for_state

    def thresholds_for_state(self, state):
        thresholds = original_thresholds_for_state(self, state)
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        money = max(0, int(getattr(state, "money", 0) or 0))
        if ante < 7 or money < 40:
            return thresholds
        resolution = self.strategy_tracker.observe(state)
        if self._is_gold_economy_route(resolution.dominant_strategy_id):
            return thresholds
        owned = _owned_tokens(state)
        if owned & {"bulljoker", "bootstrapsjoker"}:
            return thresholds
        return replace(
            thresholds,
            maximum_paid_reroll_cost=max(int(thresholds.maximum_paid_reroll_cost), 12),
            minimum_money_after_paid_reroll=min(
                int(thresholds.minimum_money_after_paid_reroll), 5
            ),
            late_ante_minimum_money_after_paid_reroll=min(
                int(thresholds.late_ante_minimum_money_after_paid_reroll), 10
            ),
            minimum_margin=0.0,
        )

    StrategyAwareShopRerollPolicy.thresholds_for_state = thresholds_for_state
    StrategyAwareJokerBuildValueEvaluator._log_batch_calibration_installed = True
