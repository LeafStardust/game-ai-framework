from __future__ import annotations

from dataclasses import dataclass

from games.balatro.actions import (
    BUY_BOOSTER,
    BUY_CONSUMABLE,
    BUY_JOKER,
    BUY_VOUCHER,
    END_SHOP,
    BalatroAction,
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
    booster: ShopBoosterRecommendation | None = None
    reroll: ShopRerollRecommendation | None = None
    rationale: tuple[str, ...] = ()


class BuildAwareShopArbiter:
    """Route the SHOP phase across independently scored child decisions.

    Deterministic purchases, unopened-booster option value, reroll, and END_SHOP
    retain separate policies/thresholds. The arbiter only compares their common
    score outputs and never inspects hidden future shop or pack contents.
    """

    DETERMINISTIC_ACTIONS = frozenset(
        {BUY_JOKER, BUY_CONSUMABLE, BUY_VOUCHER, END_SHOP}
    )

    def __init__(
        self,
        *,
        shop_policy: BalatroShopPolicy | None = None,
        booster_policy: BuildAwareShopBoosterPolicy | None = None,
        reroll_policy: BuildAwareShopRerollPolicy | None = None,
    ) -> None:
        self.shop_policy = shop_policy or BalatroShopPolicy()
        self.booster_policy = booster_policy or BuildAwareShopBoosterPolicy(
            shop_policy=self.shop_policy,
        )
        self.reroll_policy = reroll_policy or BuildAwareShopRerollPolicy(
            shop_policy=self.shop_policy,
        )

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
        if booster_best is not None:
            visible_best = max(visible_best, booster_best.total)

        reroll = self.reroll_policy.recommend(
            state,
            visible_actions,
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
