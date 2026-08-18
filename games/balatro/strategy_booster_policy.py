from __future__ import annotations

from dataclasses import replace

from games.balatro.playbook import BalatroPlaybookNotFound, default_balatro_playbooks
from games.balatro.playbook_shop_policy import PlaybookBuildAwareShopArbiter
from games.balatro.shop_booster_policy import (
    HOLD,
    BoosterAcquisitionThresholds,
    BuildAwareShopBoosterPolicy,
    ShopBoosterRecommendation,
)
from games.balatro.shop_reroll_policy import (
    BuildAwareShopRerollPolicy,
    ShopRerollThresholds,
)
from games.balatro.strategy import BalatroStrategyTracker


class StrategyAwareShopBoosterPolicy(BuildAwareShopBoosterPolicy):
    """D8 booster policy driven by the universal playbook strategy state.

    Arcana and Spectral packs are safe to open because D9/D10 still inspect the
    visible post-open choices and may Skip. Celestial packs are different: Planets
    reinforce an existing poker-hand direction, so D8 requires meaningful current
    poker-hand evidence before spending on the unopened pack.
    """

    AUTONOMOUS_SAFE_FAMILIES = frozenset(
        {*BuildAwareShopBoosterPolicy.AUTONOMOUS_SAFE_FAMILIES, "ARCANA", "SPECTRAL"}
    )

    def __init__(
        self,
        *args,
        strategy_tracker: BalatroStrategyTracker,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.strategy_tracker = strategy_tracker

    def _primary_hands(self, strategy_id: str) -> tuple[str, ...]:
        getter = getattr(self.strategy_tracker, "primary_hands_for", None)
        if callable(getter):
            return tuple(getter(strategy_id))
        definition = self.strategy_tracker.definitions.get(strategy_id)
        return () if definition is None else tuple(definition.primary_hands)

    def recommend(self, state, action) -> ShopBoosterRecommendation:
        recommendation = super().recommend(state, action)

        if recommendation.family == "BUFFOON":
            full = len(getattr(state, "jokers", ()) or ()) >= int(
                getattr(state, "joker_slots", 5) or 5
            )
            if full:
                # D8 must not demand a speculative sale before hidden Buffoon
                # contents are visible. Revalue the unopened pack as having one
                # replacement opportunity; D9 may Skip after reveal, and only a
                # visible desirable Joker may justify selling an incumbent.
                shadow = state.copy()
                shadow.joker_slots = len(getattr(state, "jokers", ()) or ()) + 1
                recommendation = super().recommend(shadow, action)
                recommendation = replace(
                    recommendation,
                    rationale=(
                        *recommendation.rationale,
                        "full Joker roster does not force a pre-open sale for Buffoon packs",
                        "Buffoon pack is valued as a replacement opportunity; inspect visible Jokers first, then sell only if an actual replacement is selected",
                    ),
                )
            return recommendation

        if recommendation.family != "CELESTIAL":
            return recommendation

        config = self.strategy_tracker._config(state)
        evidence_floor = self.strategy_tracker._number(
            config,
            "celestial_poker_evidence_floor",
            1.5,
        )
        resolution = self.strategy_tracker.observe(state)
        poker_assessments = [
            assessment
            for assessment in resolution.assessments
            if self._primary_hands(assessment.strategy_id)
        ]
        best = max(poker_assessments, key=lambda item: item.score, default=None)
        best_score = float(best.score) if best is not None else 0.0
        best_name = best.name if best is not None else "none"

        if best_score < evidence_floor:
            return replace(
                recommendation,
                decision=HOLD,
                rationale=(
                    *recommendation.rationale,
                    f"Celestial blocked: best poker-hand strategy={best_name} score={best_score:.3f}",
                    f"Celestial poker-strategy evidence floor={evidence_floor:.3f}",
                    "Planets reinforce an evidenced poker-hand route; they do not seed one",
                ),
            )

        return replace(
            recommendation,
            rationale=(
                *recommendation.rationale,
                f"Celestial admitted by poker-hand strategy={best_name} score={best_score:.3f}",
                f"Celestial poker-strategy evidence floor={evidence_floor:.3f}",
            ),
        )


class StrategyAwareShopRerollPolicy(BuildAwareShopRerollPolicy):
    """Increase reroll pressure once a build direction exists or the run is late."""

    GOLD_ECONOMY_ROOTS = frozenset({"gold_cards", "gold_seal"})
    GOLD_EARLY_RESERVE = 25
    GOLD_LATE_RESERVE = 40
    GOLD_MAXIMUM_PAID_REROLL_COST = 6

    STRATEGY_SEARCH_SCORE_FLOOR = 1.0
    STRATEGY_SEARCH_MAXIMUM_PAID_REROLL_COST = 10
    STRATEGY_SEARCH_EARLY_RESERVE = 5
    STRATEGY_SEARCH_LATE_RESERVE = 10
    STRATEGY_SEARCH_LATE_ANTE = 6

    def __init__(
        self,
        *args,
        strategy_tracker: BalatroStrategyTracker,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.strategy_tracker = strategy_tracker

    def _is_gold_economy_route(self, strategy_id: str | None) -> bool:
        if strategy_id is None:
            return False
        path = (str(strategy_id),)
        topology = getattr(self.strategy_tracker, "topology", None)
        if topology is not None and strategy_id in topology.nodes:
            path = topology.path(strategy_id)
        return bool(self.GOLD_ECONOMY_ROOTS.intersection(path))

    def _search_pressure(self, state) -> tuple[bool, float, str | None]:
        resolution = self.strategy_tracker.observe(state)
        assessment = resolution.assessment(resolution.dominant_strategy_id)
        score = float(assessment.score) if assessment is not None else 0.0
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        enabled = score >= self.STRATEGY_SEARCH_SCORE_FLOOR or ante >= self.STRATEGY_SEARCH_LATE_ANTE
        return enabled, score, resolution.dominant_strategy_id

    def thresholds_for_state(self, state) -> ShopRerollThresholds:
        thresholds = super().thresholds_for_state(state)
        resolution = self.strategy_tracker.observe(state)
        search, _, _ = self._search_pressure(state)

        if search:
            thresholds = replace(
                thresholds,
                minimum_margin=0.0,
                maximum_paid_reroll_cost=max(
                    int(thresholds.maximum_paid_reroll_cost),
                    self.STRATEGY_SEARCH_MAXIMUM_PAID_REROLL_COST,
                ),
                minimum_money_after_paid_reroll=min(
                    int(thresholds.minimum_money_after_paid_reroll),
                    self.STRATEGY_SEARCH_EARLY_RESERVE,
                ),
                late_ante_minimum_money_after_paid_reroll=min(
                    int(thresholds.late_ante_minimum_money_after_paid_reroll),
                    self.STRATEGY_SEARCH_LATE_RESERVE,
                ),
            )

        if not self._is_gold_economy_route(resolution.dominant_strategy_id):
            return thresholds
        return replace(
            thresholds,
            maximum_paid_reroll_cost=min(
                int(thresholds.maximum_paid_reroll_cost),
                self.GOLD_MAXIMUM_PAID_REROLL_COST,
            ),
            minimum_money_after_paid_reroll=max(
                int(thresholds.minimum_money_after_paid_reroll),
                self.GOLD_EARLY_RESERVE,
            ),
            late_ante_minimum_money_after_paid_reroll=max(
                int(thresholds.late_ante_minimum_money_after_paid_reroll),
                self.GOLD_LATE_RESERVE,
            ),
        )

    def recommend(self, state, visible_actions, *, reroll_cost, visible_score_floor=None):
        recommendation = super().recommend(
            state,
            visible_actions,
            reroll_cost=reroll_cost,
            visible_score_floor=visible_score_floor,
        )
        search, score, strategy_id = self._search_pressure(state)
        if not search:
            return recommendation
        return replace(
            recommendation,
            rationale=(
                *recommendation.rationale,
                f"strategy-search pressure active: dominant={strategy_id or 'none'} score={score:.3f} ante={int(getattr(state, 'ante', 1) or 1)}",
                "established/late run lowers passive waiting tolerance and favors paid search for Jokers/consumables when public EV supports it",
            ),
        )


class StrategyAwarePlaybookShopArbiter(PlaybookBuildAwareShopArbiter):
    """Resolve D8 from the active cartridge while sharing universal strategy state."""

    def __init__(
        self,
        *args,
        strategy_tracker: BalatroStrategyTracker,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.strategy_tracker = strategy_tracker

    def decide(self, state, visible_actions, *, reroll_cost):
        decision = super().decide(
            state,
            visible_actions,
            reroll_cost=reroll_cost,
        )

        # Shop packs are option-value purchases. An already visible, D2-admitted
        # Joker is concrete build value and must be resolved first. The autonomous
        # loop re-observes the settled shop after the Joker purchase, so the same
        # pack can still be considered immediately afterward with the updated build.
        if decision.source == "BOOSTER":
            joker_best = self._best_joker_decision(state)
            if joker_best is not None:
                joker_utility = self.utility_scale.joker_gain(state, joker_best)
                if joker_utility.gain > 0.0:
                    return replace(
                        decision,
                        action=joker_best.action,
                        source="JOKER",
                        total=float(joker_best.total),
                        normalized_gain=float(joker_utility.gain),
                        joker=joker_best.decision,
                        booster=None,
                        rationale=(
                            *decision.rationale,
                            "visible D2-admitted Joker takes precedence over unopened shop booster",
                            "re-observe shop after Joker transaction before reconsidering packs",
                        ),
                    )

        return decision

    def _booster_policy_for_state(self, state) -> BuildAwareShopBoosterPolicy:
        if self.booster_policy is not None:
            return self.booster_policy

        try:
            playbook = default_balatro_playbooks().for_state(state)
        except BalatroPlaybookNotFound:
            return StrategyAwareShopBoosterPolicy(
                shop_policy=self.shop_policy,
                strategy_tracker=self.strategy_tracker,
            )

        thresholds = BoosterAcquisitionThresholds.from_mapping(
            playbook.thresholds_for("D8")
        )
        return StrategyAwareShopBoosterPolicy(
            thresholds=thresholds,
            shop_policy=self.shop_policy,
            strategy_tracker=self.strategy_tracker,
        )
