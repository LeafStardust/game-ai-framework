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
from games.balatro.shop_policy import BalatroShopPolicy, ShopActionScore
from games.balatro.shop_reroll_policy import (
    BuildAwareShopRerollPolicy,
    ShopRerollRecommendation,
)
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


class BuildAwareShopArbiter:
    """Route the SHOP phase across independently scored child decisions.

    D2 Joker acquisition/replacement, deterministic purchases, unopened-booster
    option value, reroll, and END_SHOP retain separate policies/thresholds. The
    arbiter only compares their common score outputs and never inspects hidden
    future shop or pack contents.

    Joker replacement is deliberately a two-checkpoint transaction. D2 may select
    ``SELL_JOKER`` for the incumbent, but the arbiter never chains the follow-up
    purchase. The autonomous loop must observe the settled post-sale SHOP state and
    run D2 again; only that fresh decision may emit ``BUY_JOKER``.
    """

    DETERMINISTIC_ACTIONS = frozenset(
        {BUY_CONSUMABLE, BUY_VOUCHER, END_SHOP}
    )

    def __init__(
        self,
        *,
        shop_policy: BalatroShopPolicy | None = None,
        booster_policy: BuildAwareShopBoosterPolicy | None = None,
        reroll_policy: BuildAwareShopRerollPolicy | None = None,
        joker_policy: JokerAcquisitionPolicy | None = None,
    ) -> None:
        self.shop_policy = shop_policy or BalatroShopPolicy()
        self.booster_policy = booster_policy or BuildAwareShopBoosterPolicy(
            shop_policy=self.shop_policy,
        )
        self.reroll_policy = reroll_policy or BuildAwareShopRerollPolicy(
            shop_policy=self.shop_policy,
        )
        self.joker_policy = joker_policy

    def decide(
        self,
        state: BalatroState,
        visible_actions: list[BalatroAction],
        *,
        reroll_cost: int | None,
    ) -> ShopArbiterDecision:
        if state.phase != "SHOP":
            raise ValueError("shop arbiter requires SHOP phase")

        deterministic_actions = [
            action
            for action in visible_actions
            if action.name in self.DETERMINISTIC_ACTIONS
        ]
        if not any(action.name == END_SHOP for action in deterministic_actions):
            deterministic_actions.append(BalatroAction(END_SHOP))

        deterministic_ranked = self.shop_policy.rank_actions(
            state,
            deterministic_actions,
        )
        if not deterministic_ranked:
            raise RuntimeError("shop arbiter has no deterministic HOLD baseline")
        deterministic_best = deterministic_ranked[0]

        joker_best = self._best_joker_decision(state)

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
            key=lambda recommendation: recommendation.total,
            default=None,
        )

        visible_best = deterministic_best.total
        if joker_best is not None:
            visible_best = max(visible_best, joker_best.total)
        if booster_best is not None:
            visible_best = max(visible_best, booster_best.total)

        # D2 is authoritative for Joker acquisition/replacement. Do not let the
        # older generic shop scorer independently admit a BUY_JOKER while reroll
        # reasoning is comparing current visible options.
        reroll_visible_actions = [
            action for action in visible_actions if action.name != BUY_JOKER
        ]
        reroll = self.reroll_policy.recommend(
            state,
            reroll_visible_actions,
            reroll_cost=reroll_cost,
            visible_score_floor=visible_best,
        )

        candidates: list[tuple[float, int, str, BalatroAction, object]] = [
            (
                deterministic_best.total,
                2,
                "DETERMINISTIC",
                deterministic_best.action,
                deterministic_best,
            )
        ]
        if joker_best is not None:
            candidates.append(
                (
                    joker_best.total,
                    3,
                    joker_best.source,
                    joker_best.action,
                    joker_best,
                )
            )
        if booster_best is not None:
            candidates.append(
                (
                    booster_best.total,
                    1,
                    "BOOSTER",
                    booster_best.action,
                    booster_best,
                )
            )
        if reroll.decision == "REROLL":
            if reroll.executable_action is None:
                raise RuntimeError("REROLL recommendation is missing executable action")
            candidates.append(
                (
                    reroll.reroll_score,
                    0,
                    "REROLL",
                    reroll.executable_action,
                    reroll,
                )
            )

        total, _, source, action, child = max(
            candidates,
            key=lambda candidate: (candidate[0], candidate[1]),
        )
        hold = float(self.shop_policy.hold_bias)
        rationale = [
            f"arbiter source={source}",
            f"selected score={total:.3f}",
            f"hold baseline={hold:.3f}",
            f"normalized gain={total - hold:.3f}",
            f"best deterministic score={deterministic_best.total:.3f}",
            f"admitted boosters={len(admitted_boosters)}/{len(booster_recommendations)}",
            "parent arbiter compares child outputs; it does not predict hidden contents",
        ]

        if source == "DETERMINISTIC":
            rationale.extend(deterministic_best.notes)
            return ShopArbiterDecision(
                action=action,
                source=("END_SHOP" if action.name == END_SHOP else "DETERMINISTIC"),
                total=total,
                hold_baseline=hold,
                normalized_gain=total - hold,
                deterministic=deterministic_best,
                reroll=reroll,
                rationale=tuple(rationale),
            )

        if source in {"JOKER_BUY", "JOKER_REPLACE_SELL"}:
            assert isinstance(child, _ExecutableJokerDecision)
            selected = child.decision.selected
            if selected is None:
                raise RuntimeError("actionable D2 Joker decision is missing its selected option")
            rationale.extend(child.decision.rationale)
            rationale.extend(selected.rationale)
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
                normalized_gain=total - hold,
                joker=child.decision,
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
                normalized_gain=total - hold,
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
            normalized_gain=total - hold,
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
                recommendation.total,
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
