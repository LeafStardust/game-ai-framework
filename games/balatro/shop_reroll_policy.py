from __future__ import annotations

from dataclasses import dataclass

from games.balatro.actions import (
    BUY_CONSUMABLE,
    BUY_JOKER,
    BUY_VOUCHER,
    END_SHOP,
    REFRESH_SHOP,
    BalatroAction,
)
from games.balatro.build import BalatroBuildProfiler
from games.balatro.shop_policy import BalatroShopPolicy, ShopActionScore
from games.balatro.state import BalatroState


@dataclass(frozen=True)
class ShopRerollThresholds:
    """Dedicated B5 thresholds for reroll-vs-visible-shop decisions.

    ``exploration_prior`` is deliberately a policy preference, not a prediction of
    unseen shop contents. Build needs may raise that option value, but hidden future
    items/RNG are never inspected or modeled here.
    """

    exploration_prior: float = 2.5
    unmet_requirement_bonus: float = 0.75
    max_unmet_requirement_bonus: float = 3.0
    minimum_margin: float = 0.25


@dataclass(frozen=True)
class ShopRerollRecommendation:
    decision: str
    reroll_cost: int | None
    executable_action: BalatroAction | None
    current_best_score: float
    exploration_value: float
    reroll_score: float
    unmet_requirements: tuple[str, ...] = ()
    rationale: tuple[str, ...] = ()


class BuildAwareShopRerollPolicy:
    """Choose whether to spend on another shop roll using public state only.

    The layer compares a configurable exploration prior against the best *visible*
    deterministic shop action after applying the same money/interest/reserve
    economics used by :class:`BalatroShopPolicy`. It never predicts which specific
    Joker, consumable, voucher, booster, edition, or rarity will appear next.
    """

    def __init__(
        self,
        *,
        shop_policy: BalatroShopPolicy | None = None,
        build_profiler: BalatroBuildProfiler | None = None,
        thresholds: ShopRerollThresholds | None = None,
    ) -> None:
        self.shop_policy = shop_policy or BalatroShopPolicy()
        self.build_profiler = build_profiler or BalatroBuildProfiler()
        self.thresholds = thresholds or ShopRerollThresholds()

    def recommend(
        self,
        state: BalatroState,
        visible_actions: list[BalatroAction],
        *,
        reroll_cost: int | None,
    ) -> ShopRerollRecommendation:
        if state.phase != "SHOP":
            raise ValueError("reroll policy requires SHOP phase")

        current_scores = self._visible_scores(state, visible_actions)
        current_best = (
            current_scores[0].total
            if current_scores
            else float(self.shop_policy.hold_bias)
        )
        unmet = self._unmet_requirements(state)
        need_bonus = min(
            self.thresholds.max_unmet_requirement_bonus,
            len(unmet) * self.thresholds.unmet_requirement_bonus,
        )
        exploration = self.thresholds.exploration_prior + need_bonus

        if reroll_cost is None:
            return ShopRerollRecommendation(
                decision="HOLD",
                reroll_cost=None,
                executable_action=None,
                current_best_score=current_best,
                exploration_value=exploration,
                reroll_score=float("-inf"),
                unmet_requirements=unmet,
                rationale=(
                    "current reroll cost is not observed; reroll fails closed",
                    "exploration prior does not predict unseen shop contents",
                ),
            )

        cost = int(reroll_cost)
        if cost < 0:
            raise ValueError("reroll cost cannot be negative")

        if cost > state.money:
            return ShopRerollRecommendation(
                decision="HOLD",
                reroll_cost=cost,
                executable_action=None,
                current_best_score=current_best,
                exploration_value=exploration,
                reroll_score=float("-inf"),
                unmet_requirements=unmet,
                rationale=(
                    f"reroll costs ${cost} but only ${state.money} is available",
                    "exploration prior does not predict unseen shop contents",
                ),
            )

        remaining = state.money - cost
        price_penalty = cost * self.shop_policy.price_weight
        interest_penalty = (
            self.shop_policy._interest(state.money)
            - self.shop_policy._interest(remaining)
        ) * self.shop_policy.interest_weight
        reserve_penalty = self.shop_policy._incremental_reserve_shortfall(
            state.money,
            remaining,
        ) * self.shop_policy.reserve_weight

        reroll_score = (
            exploration
            - price_penalty
            - interest_penalty
            - reserve_penalty
        )
        required = current_best + self.thresholds.minimum_margin

        rationale = (
            f"visible-shop best score={current_best:.3f}",
            f"exploration prior={self.thresholds.exploration_prior:.3f}",
            f"unmet build requirements={len(unmet)} bonus={need_bonus:.3f}",
            f"reroll cost=${cost} price penalty={price_penalty:.3f}",
            f"interest penalty={interest_penalty:.3f}",
            f"reserve penalty={reserve_penalty:.3f}",
            f"reroll score={reroll_score:.3f}; required>{required:.3f}",
            "exploration prior does not predict unseen shop contents",
        )

        if reroll_score <= required:
            return ShopRerollRecommendation(
                decision="HOLD",
                reroll_cost=cost,
                executable_action=None,
                current_best_score=current_best,
                exploration_value=exploration,
                reroll_score=reroll_score,
                unmet_requirements=unmet,
                rationale=rationale,
            )

        return ShopRerollRecommendation(
            decision="REROLL",
            reroll_cost=cost,
            executable_action=BalatroAction(REFRESH_SHOP),
            current_best_score=current_best,
            exploration_value=exploration,
            reroll_score=reroll_score,
            unmet_requirements=unmet,
            rationale=rationale,
        )

    def _visible_scores(
        self,
        state: BalatroState,
        visible_actions: list[BalatroAction],
    ) -> list[ShopActionScore]:
        """Score only deterministic child-layer actions already supported by D12."""
        supported_names = {
            BUY_JOKER,
            BUY_CONSUMABLE,
            BUY_VOUCHER,
            END_SHOP,
        }
        supported = [
            action
            for action in visible_actions
            if action.name in supported_names
        ]

        # Random-state actions (e.g. booster opening) are intentionally absent:
        # this layer will not fabricate a deterministic comparable value for them.
        if not any(action.name == END_SHOP for action in supported):
            supported.append(BalatroAction(END_SHOP))

        return self.shop_policy.rank_actions(state, supported)

    def _unmet_requirements(self, state: BalatroState) -> tuple[str, ...]:
        profile = self.build_profiler.profile(state)
        requirements = {
            requirement
            for effect in profile.effects
            for requirement in effect.requires
        }
        return tuple(
            sorted(
                requirement
                for requirement in requirements
                if not profile.supports(requirement)
            )
        )
