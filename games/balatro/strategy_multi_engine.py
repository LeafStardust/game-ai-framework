from __future__ import annotations

"""Primary-win-condition plus compatible-engine strategy orchestration.

The universal strategy catalogue contains both actual win conditions and useful
engines. Treating every positive node as a mutually-exclusive build causes support
engines to hijack the run, especially after the old Ante-6 convergence boundary.
This layer keeps one primary scoring direction while allowing compatible secondary
and support engines to remain prescriptive.
"""

from dataclasses import replace

from games.balatro.strategy import (
    AVAILABLE,
    BRONZE,
    GOLD,
    SILVER,
    BalatroStrategyTracker,
)

PRIMARY = "PRIMARY"
SECONDARY = "SECONDARY"
SUPPORT = "SUPPORT"

SECONDARY_STRATEGIES = frozenset({
    "drivers_license",
    "blue_seal", "gold_seal", "red_seal", "purple_seal",
    "hiker_training",
    "planet_engine", "planet_constellation", "planet_satellite",
    "planet_constellation_satellite",
    "tarot_engine", "tarot_cartomancer", "tarot_hallucination", "tarot_eight_ball",
    "cash_hoard", "cash_growth", "cash_cloud_nine", "cash_bull_bootstraps",
    "discard_utilization", "discard_castle", "discard_mail_rebate",
    "no_discard", "no_discard_reserve", "no_discard_ramen",
    "loyalty_cycle",
})

SUPPORT_STRATEGIES = frozenset({
    "face_held_economy", "face_business_card", "faceless_discard_economy",
    "deck_thinning", "thinning_trading", "thinning_erosion", "thinning_trading_erosion",
    "abstract_joker", "swashbuckler", "raised_fist", "flower_pot",
    "last_hand_burst", "last_hand_acrobat",
})


def strategy_role(strategy_id: str | None) -> str:
    if strategy_id in SUPPORT_STRATEGIES:
        return SUPPORT
    if strategy_id in SECONDARY_STRATEGIES:
        return SECONDARY
    return PRIMARY


def _positive_tokens(definition) -> frozenset[str]:
    return frozenset(
        set(getattr(definition, "gold_jokers", ()))
        | set(getattr(definition, "silver_jokers", ()))
        | set(getattr(definition, "bronze_jokers", ()))
    )


def _compatible(tracker: BalatroStrategyTracker, primary_id: str, other_id: str) -> bool:
    """Reject explicit catalogue conflicts and competing poker-hand prescriptions."""
    if primary_id == other_id:
        return True
    primary_defs = tuple(tracker.definitions_for_path(primary_id))
    other_defs = tuple(tracker.definitions_for_path(other_id))
    if not primary_defs or not other_defs:
        return True

    primary_positive = frozenset().union(*(_positive_tokens(d) for d in primary_defs))
    other_positive = frozenset().union(*(_positive_tokens(d) for d in other_defs))
    primary_bans = frozenset().union(*(getattr(d, "banned_jokers", frozenset()) for d in primary_defs))
    other_bans = frozenset().union(*(getattr(d, "banned_jokers", frozenset()) for d in other_defs))
    if primary_bans & other_positive or other_bans & primary_positive:
        return False

    primary_hands = set(tracker.primary_hands_for(primary_id))
    other_hands = set(tracker.primary_hands_for(other_id))
    if primary_hands and other_hands and primary_hands.isdisjoint(other_hands):
        return False
    return True


def primary_strategy_id(tracker: BalatroStrategyTracker, resolution) -> str | None:
    positive = [a for a in resolution.assessments if float(a.score) > 0.0]
    true_primary = next((a for a in positive if strategy_role(a.strategy_id) == PRIMARY), None)
    if true_primary is not None:
        return true_primary.strategy_id
    secondary = next((a for a in positive if strategy_role(a.strategy_id) == SECONDARY), None)
    if secondary is not None:
        return secondary.strategy_id
    return positive[0].strategy_id if positive else None


def active_engine_ids(tracker: BalatroStrategyTracker, resolution) -> tuple[str, ...]:
    primary_id = primary_strategy_id(tracker, resolution)
    if primary_id is None:
        return ()
    engines: list[str] = []
    for assessment in resolution.assessments:
        strategy_id = assessment.strategy_id
        if strategy_id == primary_id or float(assessment.score) <= 0.0:
            continue
        if strategy_role(strategy_id) == PRIMARY:
            continue
        if assessment.status == AVAILABLE and float(assessment.score) < 1.0:
            continue
        if not _compatible(tracker, primary_id, strategy_id):
            continue
        engines.append(strategy_id)
        if len(engines) >= 3:
            break
    return tuple(engines)


def prescriptive_strategy_ids(tracker: BalatroStrategyTracker, resolution) -> tuple[str, ...]:
    primary_id = primary_strategy_id(tracker, resolution)
    if primary_id is None:
        return ()
    return (primary_id, *active_engine_ids(tracker, resolution))


def install_multi_engine_strategy_policy() -> None:
    """Keep compatible engines prescriptive without letting them hijack the primary."""
    if getattr(BalatroStrategyTracker, "_multi_engine_policy_installed", False):
        return

    BalatroStrategyTracker.strategy_role = lambda self, strategy_id: strategy_role(strategy_id)
    BalatroStrategyTracker.primary_strategy_id = lambda self, resolution: primary_strategy_id(self, resolution)
    BalatroStrategyTracker.active_engine_ids = lambda self, resolution: active_engine_ids(self, resolution)
    BalatroStrategyTracker.prescriptive_strategy_ids = lambda self, resolution: prescriptive_strategy_ids(self, resolution)

    original_scope_factor = BalatroStrategyTracker._scope_factor
    original_evaluate_item = BalatroStrategyTracker.evaluate_item

    def _scope_factor(self, state, strategy_id, rank, resolution):
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        if ante < 6:
            return original_scope_factor(self, state, strategy_id, rank, resolution)
        prescriptive = self.prescriptive_strategy_ids(resolution)
        if strategy_id not in prescriptive:
            return 0.0
        if strategy_id == self.primary_strategy_id(resolution):
            return 1.0
        return 0.65 if self.strategy_role(strategy_id) == SECONDARY else 0.40

    def evaluate_item(self, state, item, *, kind):
        result = original_evaluate_item(self, state, item, kind=kind)
        resolution = self.observe(state)
        engine_ids = set(self.active_engine_ids(resolution))
        if not engine_ids:
            return result
        relationships = self._relationships_for(item, kind=str(kind).upper())
        aligned = [
            (strategy_id, relationship)
            for strategy_id, relationship in relationships.items()
            if strategy_id in engine_ids and relationship in {GOLD, SILVER, BRONZE}
        ]
        if not aligned:
            return result

        by_id = {a.strategy_id: a for a in resolution.assessments}
        best_id, best_tier = max(
            aligned,
            key=lambda pair: self.relationship_score(state, pair[1]),
        )
        assessment = by_id.get(best_id)
        if assessment is None:
            return result
        role_factor = 0.65 if self.strategy_role(best_id) == SECONDARY else 0.40
        relation_weight = self.relationship_score(state, best_tier)
        alignment = max(0.0, float(assessment.score)) * relation_weight * role_factor
        config = self._config(state)
        bonus = alignment * self._number(config, "candidate_alignment_scale", 0.08) * self.strategy_pressure(state)
        definition = self.definitions.get(best_id)
        projected = float(assessment.score) + relation_weight * float(assessment.effectiveness)
        return replace(
            result,
            strategy_id=best_id if bonus > float(result.value) else result.strategy_id,
            strategy_name=(definition.name if definition is not None and bonus > float(result.value) else result.strategy_name),
            tier=best_tier if bonus > float(result.value) else result.tier,
            value=max(float(result.value), bonus),
            projected_score=max(float(result.projected_score), projected),
            active_alignment=True,
            rationale=(
                *result.rationale,
                f"compatible {self.strategy_role(best_id).lower()} engine remains prescriptive: {best_id} {best_tier}",
                f"multi-engine alignment floor={bonus:+.3f}; primary={self.primary_strategy_id(resolution)}",
            ),
        )

    def hand_fit(self, state, hand_type):
        resolution = self.observe(state)
        primary_id = self.primary_strategy_id(resolution)
        if primary_id is None:
            return 0.0, ("no positive universal strategy evidence",)

        hand_type = str(hand_type).upper()
        pressure = self.strategy_pressure(state)
        prescriptive = self.prescriptive_strategy_ids(resolution)
        mapped = False
        for index, strategy_id in enumerate(prescriptive):
            hands = tuple(self.primary_hands_for(strategy_id))
            if not hands:
                continue
            mapped = True
            if hand_type in hands:
                strength = 1.0 if index == 0 else 0.45
                definition = self.definitions.get(strategy_id)
                name = definition.name if definition is not None else strategy_id
                return strength * pressure * self.effectiveness(state, strategy_id), (
                    f"{hand_type} reinforces {'primary' if index == 0 else 'compatible engine'} strategy {name}",
                )
        if not mapped:
            return 0.0, ("active primary/engine strategies do not prescribe a poker-hand type",)
        return -0.25 * pressure, (f"{hand_type} does not reinforce the active primary scoring route",)

    BalatroStrategyTracker._scope_factor = _scope_factor
    BalatroStrategyTracker.evaluate_item = evaluate_item
    BalatroStrategyTracker.hand_fit = hand_fit
    BalatroStrategyTracker._multi_engine_policy_installed = True
