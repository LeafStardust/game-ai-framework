from __future__ import annotations

from dataclasses import dataclass

from games.balatro.actions import (
    BUY_BOOSTER,
    BUY_CONSUMABLE,
    BUY_JOKER,
    BUY_VOUCHER,
    END_SHOP,
    SELL_JOKER,
    BalatroAction,
)
from games.balatro.joker_policy import (
    BUY,
    REPLACE,
    JokerAcquisitionDecision,
    JokerAcquisitionPolicy,
    JokerAcquisitionThresholds,
)
from games.balatro.playbook import (
    BalatroPlaybookNotFound,
    default_balatro_playbooks,
)
from games.balatro.shop_booster_policy import (
    BuildAwareShopBoosterPolicy,
    ShopBoosterRecommendation,
)
from games.balatro.shop_consumable_policy import (
    BUY as CONSUMABLE_BUY,
    BUY_AND_USE as CONSUMABLE_BUY_AND_USE,
    ConsumableAcquisitionDecision,
    ConsumableAcquisitionPolicy,
    ConsumableAcquisitionThresholds,
)
from games.balatro.shop_policy import BalatroShopPolicy, ShopActionScore
from games.balatro.shop_reroll_policy import (
    BuildAwareShopRerollPolicy,
    ShopRerollRecommendation,
)
from games.balatro.shop_utility_scale import ShopUtilityScale
from games.balatro.state import BalatroState


@dataclass(frozen=True)
class ShopArbiterDecision:
    """Normalized parent decision over completed SHOP child layers."""

    action: BalatroAction
    source: str
    total: float
    hold_baseline: float
    normalized_gain: float
    deterministic: ShopActionScore | None = None
    joker: JokerAcquisitionDecision | None = None
    consumable: ConsumableAcquisitionDecision | None = None
    booster: ShopBoosterRecommendation | None = None
    reroll: ShopRerollRecommendation | None = None
    rationale: tuple[str, ...] = ()


@dataclass(frozen=True)
class _ExecutableJokerDecision:
    action: BalatroAction
    source: str
    total: float
    candidate: object
    decision: JokerAcquisitionDecision
    candidate_index: int


@dataclass(frozen=True)
class _ExecutableConsumableDecision:
    action: BalatroAction
    source: str
    total: float
    candidate: object
    decision: ConsumableAcquisitionDecision
    candidate_index: int


@dataclass(frozen=True)
class _ArbiterCandidate:
    action: BalatroAction
    source: str
    total: float
    normalized_gain: float
    priority: int
    child: object | None = None


class BuildAwareShopArbiter:
    """Route the SHOP phase across independently scored child decisions.

    D2 Joker acquisition/replacement, D4 consumable acquisition mode, deterministic
    voucher purchases, unopened-booster option value, reroll, and END_SHOP retain
    separate policies/thresholds. Child policies remain authoritative for admission,
    then D14 recomputes admitted options on one shared parent resource scale before
    cross-family comparison. END_SHOP is the explicit zero-gain parent baseline. The
    arbiter never inspects hidden future shop or pack contents.

    Joker replacement is deliberately a two-checkpoint transaction. D2 may select
    ``SELL_JOKER`` for the incumbent, but the arbiter never chains the follow-up
    purchase. The autonomous loop must observe the settled post-sale SHOP state and
    run D2 again; only that fresh decision may emit ``BUY_JOKER``.
    """

    DETERMINISTIC_ACTIONS = frozenset({BUY_VOUCHER, END_SHOP})

    def __init__(
        self,
        *,
        shop_policy: BalatroShopPolicy | None = None,
        booster_policy: BuildAwareShopBoosterPolicy | None = None,
        reroll_policy: BuildAwareShopRerollPolicy | None = None,
        joker_policy: JokerAcquisitionPolicy | None = None,
        consumable_policy: ConsumableAcquisitionPolicy | None = None,
    ) -> None:
        self.shop_policy = shop_policy or BalatroShopPolicy()
        self.utility_scale = ShopUtilityScale(self.shop_policy)
        self.booster_policy = booster_policy or BuildAwareShopBoosterPolicy(
            shop_policy=self.shop_policy,
        )
        self.reroll_policy = reroll_policy or BuildAwareShopRerollPolicy(
            shop_policy=self.shop_policy,
        )
        self.joker_policy = joker_policy
        self.consumable_policy = consumable_policy

    def decide(
        self,
        state: BalatroState,
        visible_actions: list[BalatroAction],
        *,
        reroll_cost: int | None,
    ) -> ShopArbiterDecision:
        if state.phase != "SHOP":
            raise ValueError("shop arbiter requires SHOP phase")

        hold = float(self.shop_policy.hold_bias)
        deterministic_actions = [
            action
            for action in visible_actions
            if action.name in self.DETERMINISTIC_ACTIONS
            and action.name != END_SHOP
        ]
        deterministic_ranked = self.shop_policy.rank_actions(
            state,
            deterministic_actions,
        )
        deterministic_best = (
            deterministic_ranked[0] if deterministic_ranked else None
        )

        joker_best = self._best_joker_decision(state)
        consumable_best = self._best_consumable_decision(state)

        booster_recommendations = tuple(
            self.booster_policy.recommend(state, action)
            for action in visible_actions
            if action.name == BUY_BOOSTER
        )
        admitted_boosters = tuple(
            recommendation
            for recommendation in booster_recommendations
            if recommendation.decision == "BUY"
        )
        booster_best = max(
            admitted_boosters,
            key=lambda recommendation: self.utility_scale.booster_gain(
                state,
                recommendation,
            ).gain,
            default=None,
        )

        deterministic_utility = (
            self.utility_scale.baseline_gain(deterministic_best.total, hold)
            if deterministic_best is not None
            else None
        )
        joker_utility = (
            self.utility_scale.joker_gain(state, joker_best)
            if joker_best is not None
            else None
        )
        consumable_utility = (
            self.utility_scale.consumable_gain(state, consumable_best)
            if consumable_best is not None
            else None
        )
        booster_utility = (
            self.utility_scale.booster_gain(state, booster_best)
            if booster_best is not None
            else None
        )

        visible_normalized_best = max(
            0.0,
            *(
                utility.gain
                for utility in (
                    deterministic_utility,
                    joker_utility,
                    consumable_utility,
                    booster_utility,
                )
                if utility is not None
            ),
        )

        # D2 and D4 are authoritative for their item families. Do not let the
        # older generic scorer independently admit those same actions while reroll
        # reasoning compares visible opportunity. Reroll operates on the generic
        # shop-score representation, so map the D14 shared normalized visible floor
        # back onto that representation using the parent's hold baseline.
        reroll_visible_actions = [
            action
            for action in visible_actions
            if action.name not in {BUY_JOKER, BUY_CONSUMABLE}
        ]
        reroll_visible_floor = hold + visible_normalized_best
        reroll = self.reroll_policy.recommend(
            state,
            reroll_visible_actions,
            reroll_cost=reroll_cost,
            visible_score_floor=reroll_visible_floor,
        )
        reroll_utility = (
            self.utility_scale.baseline_gain(reroll.reroll_score, hold)
            if reroll.decision == "REROLL"
            else None
        )

        # END_SHOP is a real candidate, not an after-the-fact fallback. It wins
        # exact zero-gain ties except against an admitted zero-cost reroll: a free
        # reroll weakly dominates ending because END_SHOP remains available after
        # observing the refreshed shop. Positive child ties retain explicit parent
        # priority: D2 > D4 > deterministic voucher > booster > reroll.
        candidates: list[_ArbiterCandidate] = [
            _ArbiterCandidate(
                action=BalatroAction(END_SHOP),
                source="END_SHOP",
                total=hold,
                normalized_gain=0.0,
                priority=5,
            )
        ]
        if deterministic_best is not None and deterministic_utility is not None:
            candidates.append(
                _ArbiterCandidate(
                    action=deterministic_best.action,
                    source="DETERMINISTIC",
                    total=float(deterministic_best.total),
                    normalized_gain=deterministic_utility.gain,
                    priority=2,
                    child=deterministic_best,
                )
            )
        if joker_best is not None and joker_utility is not None:
            candidates.append(
                _ArbiterCandidate(
                    action=joker_best.action,
                    source=joker_best.source,
                    total=float(joker_best.total),
                    normalized_gain=joker_utility.gain,
                    priority=4,
                    child=joker_best,
                )
            )
        if consumable_best is not None and consumable_utility is not None:
            candidates.append(
                _ArbiterCandidate(
                    action=consumable_best.action,
                    source=consumable_best.source,
                    total=float(consumable_best.total),
                    normalized_gain=consumable_utility.gain,
                    priority=3,
                    child=consumable_best,
                )
            )
        if booster_best is not None and booster_utility is not None:
            candidates.append(
                _ArbiterCandidate(
                    action=booster_best.action,
                    source="BOOSTER",
                    total=float(booster_best.total),
                    normalized_gain=booster_utility.gain,
                    priority=1,
                    child=booster_best,
                )
            )
        if reroll.decision == "REROLL":
            if reroll.executable_action is None:
                raise RuntimeError("REROLL recommendation is missing executable action")
            assert reroll_utility is not None
            candidates.append(
                _ArbiterCandidate(
                    action=reroll.executable_action,
                    source="REROLL",
                    total=float(reroll.reroll_score),
                    normalized_gain=reroll_utility.gain,
                    priority=6 if reroll_cost == 0 else 0,
                    child=reroll,
                )
            )

        selected = max(
            candidates,
            key=lambda candidate: (
                candidate.normalized_gain,
                candidate.priority,
            ),
        )
        source = selected.source
        action = selected.action
        total = selected.total
        normalized_gain = selected.normalized_gain
        child = selected.child
        deterministic_text = (
            f"{deterministic_best.total:.3f}"
            if deterministic_best is not None
            else "none"
        )
        consumable_text = (
            f"{consumable_best.total:.3f}"
            if consumable_best is not None
            else "none"
        )
        rationale = [
            f"arbiter source={source}",
            f"selected child score={total:.3f}",
            f"parent END_SHOP baseline={hold:.3f}",
            f"D14 normalized gain={normalized_gain:.3f}",
            f"best deterministic score={deterministic_text}",
            f"best D4 consumable advantage={consumable_text}",
            f"visible normalized floor={visible_normalized_best:.3f}",
            f"admitted boosters={len(admitted_boosters)}/{len(booster_recommendations)}",
            "D14 parent comparison uses one shared money/interest/reserve/slot resource scale after child admission",
            "child admission thresholds remain child-owned",
            "parent arbiter does not predict hidden contents",
        ]

        if source == "END_SHOP":
            return ShopArbiterDecision(
                action=action,
                source="END_SHOP",
                total=total,
                hold_baseline=hold,
                normalized_gain=0.0,
                reroll=reroll,
                rationale=tuple(rationale),
            )

        if source == "DETERMINISTIC":
            assert isinstance(child, ShopActionScore)
            rationale.extend(child.notes)
            return ShopArbiterDecision(
                action=action,
                source="DETERMINISTIC",
                total=total,
                hold_baseline=hold,
                normalized_gain=normalized_gain,
                deterministic=child,
                reroll=reroll,
                rationale=tuple(rationale),
            )

        if source in {"JOKER_BUY", "JOKER_REPLACE_SELL"}:
            assert isinstance(child, _ExecutableJokerDecision)
            selected_option = child.decision.selected
            if selected_option is None:
                raise RuntimeError("actionable D2 Joker decision is missing its selected option")
            rationale.extend(child.decision.rationale)
            rationale.extend(selected_option.rationale)
            if source == "JOKER_REPLACE_SELL":
                rationale.extend(
                    (
                        "replacement execution step=SELL",
                        "follow-up BUY is not chained",
                        "next action requires fresh authoritative observation and D2 replan",
                    )
                )
            return ShopArbiterDecision(
                action=action,
                source=source,
                total=total,
                hold_baseline=hold,
                normalized_gain=normalized_gain,
                joker=child.decision,
                reroll=reroll,
                rationale=tuple(rationale),
            )

        if source in {"CONSUMABLE_BUY", "CONSUMABLE_BUY_AND_USE"}:
            assert isinstance(child, _ExecutableConsumableDecision)
            selected_option = child.decision.selected
            if selected_option is None:
                raise RuntimeError("actionable D4 consumable decision is missing its selected option")
            rationale.extend(child.decision.rationale)
            rationale.extend(selected_option.rationale)
            return ShopArbiterDecision(
                action=action,
                source=source,
                total=total,
                hold_baseline=hold,
                normalized_gain=normalized_gain,
                consumable=child.decision,
                reroll=reroll,
                rationale=tuple(rationale),
            )

        if source == "BOOSTER":
            assert isinstance(child, ShopBoosterRecommendation)
            rationale.extend(child.rationale)
            return ShopArbiterDecision(
                action=action,
                source="BOOSTER",
                total=total,
                hold_baseline=hold,
                normalized_gain=normalized_gain,
                booster=child,
                reroll=reroll,
                rationale=tuple(rationale),
            )

        assert isinstance(child, ShopRerollRecommendation)
        rationale.extend(child.rationale)
        return ShopArbiterDecision(
            action=action,
            source="REROLL",
            total=total,
            hold_baseline=hold,
            normalized_gain=normalized_gain,
            reroll=child,
            rationale=tuple(rationale),
        )

    def _best_joker_decision(
        self,
        state: BalatroState,
    ) -> _ExecutableJokerDecision | None:
        policy = self._joker_policy_for_state(state)
        actionable: list[_ExecutableJokerDecision] = []

        for candidate_index, candidate in enumerate(state.shop_jokers):
            decision = policy.decide(state, candidate)
            selected = decision.selected
            if selected is None:
                continue

            if decision.action == BUY:
                action = BalatroAction(BUY_JOKER, target=candidate)
                source = "JOKER_BUY"
            elif decision.action == REPLACE:
                replace_index = selected.replace_index
                if replace_index is None:
                    raise RuntimeError("D2 replacement is missing an incumbent slot")
                if replace_index < 0 or replace_index >= len(state.jokers):
                    raise RuntimeError(
                        f"D2 replacement slot {replace_index} is outside the current Joker roster"
                    )
                action = BalatroAction(SELL_JOKER, target=replace_index)
                source = "JOKER_REPLACE_SELL"
            else:
                continue

            actionable.append(
                _ExecutableJokerDecision(
                    action=action,
                    source=source,
                    total=float(selected.total_advantage),
                    candidate=candidate,
                    decision=decision,
                    candidate_index=candidate_index,
                )
            )

        if not actionable:
            return None

        return max(
            actionable,
            key=lambda recommendation: (
                self.utility_scale.joker_gain(state, recommendation).gain,
                -recommendation.candidate_index,
            ),
        )

    def _best_consumable_decision(
        self,
        state: BalatroState,
    ) -> _ExecutableConsumableDecision | None:
        policy = self._consumable_policy_for_state(state)
        actionable: list[_ExecutableConsumableDecision] = []

        for candidate_index, candidate in enumerate(state.shop_consumables):
            decision = policy.decide(state, candidate)
            selected = decision.selected
            if selected is None or selected.executable_action is None:
                continue

            if decision.action == CONSUMABLE_BUY:
                source = "CONSUMABLE_BUY"
            elif decision.action == CONSUMABLE_BUY_AND_USE:
                source = "CONSUMABLE_BUY_AND_USE"
            else:
                continue

            actionable.append(
                _ExecutableConsumableDecision(
                    action=selected.executable_action,
                    source=source,
                    total=float(selected.total_advantage),
                    candidate=candidate,
                    decision=decision,
                    candidate_index=candidate_index,
                )
            )

        if not actionable:
            return None

        return max(
            actionable,
            key=lambda recommendation: (
                self.utility_scale.consumable_gain(state, recommendation).gain,
                -recommendation.candidate_index,
            ),
        )

    def _joker_policy_for_state(self, state: BalatroState) -> JokerAcquisitionPolicy:
        if self.joker_policy is not None:
            return self.joker_policy

        try:
            playbook = default_balatro_playbooks().for_state(state)
        except BalatroPlaybookNotFound:
            # Unit/synthetic states frequently omit deck/stake identity. The
            # default D2 thresholds are the conservative shared fallback and match
            # the currently supported Red/White cartridge unless overridden there.
            return JokerAcquisitionPolicy()

        thresholds = JokerAcquisitionThresholds.from_mapping(
            playbook.strategy.get("decision_thresholds", {}).get(
                "joker_acquisition",
                {},
            )
        )
        return JokerAcquisitionPolicy(thresholds)

    def _consumable_policy_for_state(
        self,
        state: BalatroState,
    ) -> ConsumableAcquisitionPolicy:
        if self.consumable_policy is not None:
            return self.consumable_policy

        try:
            playbook = default_balatro_playbooks().for_state(state)
        except BalatroPlaybookNotFound:
            return ConsumableAcquisitionPolicy()

        thresholds = ConsumableAcquisitionThresholds.from_mapping(
            playbook.strategy.get("decision_thresholds", {}).get(
                "consumable_acquisition",
                {},
            )
        )
        return ConsumableAcquisitionPolicy(thresholds)
