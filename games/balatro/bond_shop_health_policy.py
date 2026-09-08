from __future__ import annotations

from dataclasses import dataclass, replace

from games.balatro.live.hand_action_policy import LiveHandActionDecisionEngine
from games.balatro.live.strategy_health import LiveStrategyHealth, StrategyHealthMode, evaluate_live_strategy_health
from games.balatro.shop_reroll_policy import BuildAwareShopRerollPolicy
from games.balatro.shop_utility_scale import ShopNormalizedUtility, ShopUtilityScale


@dataclass(frozen=True)
class StrategyHealthProvenance:
    deck_name: str
    stake_name: str
    ante: int
    round: int


_LAST_STRATEGY_HEALTH: LiveStrategyHealth | None = None
_LAST_STRATEGY_HEALTH_PROVENANCE: StrategyHealthProvenance | None = None


_JOKER_GAIN_FACTOR = {
    StrategyHealthMode.SURVIVE: 1.25,
    StrategyHealthMode.REPAIR: 1.15,
    StrategyHealthMode.HOLD: 1.00,
    StrategyHealthMode.REINFORCE: 1.00,
    StrategyHealthMode.EXPLOIT: 1.00,
}

_CONSUMABLE_GAIN_FACTOR = {
    StrategyHealthMode.SURVIVE: 1.15,
    StrategyHealthMode.REPAIR: 1.08,
    StrategyHealthMode.HOLD: 1.00,
    StrategyHealthMode.REINFORCE: 1.00,
    StrategyHealthMode.EXPLOIT: 1.00,
}

_REROLL_MARGIN_FACTOR = {
    StrategyHealthMode.SURVIVE: 1.35,
    StrategyHealthMode.REPAIR: 1.20,
    StrategyHealthMode.HOLD: 1.00,
    StrategyHealthMode.REINFORCE: 1.00,
    StrategyHealthMode.EXPLOIT: 1.00,
}


def _provenance(state) -> StrategyHealthProvenance:
    return StrategyHealthProvenance(
        deck_name=str(getattr(state, "deck_name", "") or ""),
        stake_name=str(getattr(state, "stake_name", "") or ""),
        ante=max(1, int(getattr(state, "ante", 1) or 1)),
        round=int(getattr(state, "round", getattr(state, "round_num", 0)) or 0),
    )


def _provenance_matches(state) -> bool:
    if _LAST_STRATEGY_HEALTH_PROVENANCE is None:
        return False
    return _provenance(state) == _LAST_STRATEGY_HEALTH_PROVENANCE


def last_strategy_health(state=None) -> LiveStrategyHealth | None:
    if state is not None and not _provenance_matches(state):
        return None
    return _LAST_STRATEGY_HEALTH


def clear_strategy_health() -> None:
    global _LAST_STRATEGY_HEALTH, _LAST_STRATEGY_HEALTH_PROVENANCE
    _LAST_STRATEGY_HEALTH = None
    _LAST_STRATEGY_HEALTH_PROVENANCE = None


def _record_strategy_health(state, decision) -> None:
    global _LAST_STRATEGY_HEALTH, _LAST_STRATEGY_HEALTH_PROVENANCE
    try:
        _LAST_STRATEGY_HEALTH = evaluate_live_strategy_health(
            state,
            selected_plan=decision.selected_plan,
        )
        _LAST_STRATEGY_HEALTH_PROVENANCE = _provenance(state)
    except (AttributeError, TypeError, ValueError):
        # Strategy health is advisory. Failure to derive it must never block D1.
        clear_strategy_health()


def _positive_gain_with_health(
    utility: ShopNormalizedUtility,
    *,
    factor: float,
    note: str,
) -> ShopNormalizedUtility:
    if utility.gain <= 0.0 or factor <= 1.0:
        return utility
    adjusted = utility.gain * factor
    return replace(
        utility,
        gain=adjusted,
        notes=(
            *utility.notes,
            f"canonical Bond-health authority: {note}; admitted positive gain factor={factor:.3f}",
        ),
    )


def install_bond_shop_health_policy() -> None:
    """Bridge canonical 46-Bond Strategy Health into SHOP without bypassing guards.

    The layer is deliberately downstream of D1 survival and downstream of all SHOP
    child admission/legality policies. It can amplify only already-positive admitted
    acquisition utility and already-admitted reroll margin. It cannot turn a rejected
    purchase/reroll into an executable action, cannot make negative utility positive,
    and cannot weaken affordability, reserve, slot, Eternal, or replacement guards.

    Cached health is valid only for the same public run/round identity that produced
    it. This prevents a module-global D1->SHOP bridge from leaking stale authority
    across restarts, different rounds, decks, stakes, or direct SHOP entry.
    """

    if not getattr(LiveHandActionDecisionEngine, "_bond_shop_health_capture_installed", False):
        original_decide = LiveHandActionDecisionEngine.decide

        def decide(self, state):
            decision = original_decide(self, state)
            _record_strategy_health(state, decision)
            self.last_strategy_health = _LAST_STRATEGY_HEALTH
            return decision

        LiveHandActionDecisionEngine.decide = decide
        LiveHandActionDecisionEngine._bond_shop_health_capture_installed = True

    if not getattr(ShopUtilityScale, "_bond_shop_health_utility_installed", False):
        original_joker_gain = ShopUtilityScale.joker_gain
        original_consumable_gain = ShopUtilityScale.consumable_gain

        def joker_gain(self, state, executable):
            utility = original_joker_gain(self, state, executable)
            health = last_strategy_health(state)
            if health is None:
                return utility
            factor = _JOKER_GAIN_FACTOR[health.mode]
            if getattr(executable, "source", "") == "JOKER_REPLACE_SELL":
                # Replacement churn receives only half of the weak-health boost.
                factor = 1.0 + (factor - 1.0) * 0.5
            return _positive_gain_with_health(
                utility,
                factor=factor,
                note=f"mode={health.mode.value}",
            )

        def consumable_gain(self, state, executable):
            utility = original_consumable_gain(self, state, executable)
            health = last_strategy_health(state)
            if health is None:
                return utility
            return _positive_gain_with_health(
                utility,
                factor=_CONSUMABLE_GAIN_FACTOR[health.mode],
                note=f"mode={health.mode.value}",
            )

        ShopUtilityScale.joker_gain = joker_gain
        ShopUtilityScale.consumable_gain = consumable_gain
        ShopUtilityScale._bond_shop_health_utility_installed = True

    if not getattr(BuildAwareShopRerollPolicy, "_bond_shop_health_reroll_installed", False):
        original_recommend = BuildAwareShopRerollPolicy.recommend

        def recommend(self, state, visible_actions, *, reroll_cost, visible_score_floor=None):
            recommendation = original_recommend(
                self,
                state,
                visible_actions,
                reroll_cost=reroll_cost,
                visible_score_floor=visible_score_floor,
            )
            health = last_strategy_health(state)
            if health is None or recommendation.decision != "REROLL":
                return recommendation

            factor = _REROLL_MARGIN_FACTOR[health.mode]
            if factor <= 1.0:
                return recommendation

            margin = max(
                0.0,
                float(recommendation.reroll_score)
                - float(recommendation.current_best_score),
            )
            if margin <= 0.0:
                return recommendation

            adjusted_score = float(recommendation.current_best_score) + margin * factor
            return replace(
                recommendation,
                reroll_score=adjusted_score,
                rationale=(
                    *recommendation.rationale,
                    f"canonical Bond-health mode={health.mode.value}; admitted reroll margin factor={factor:.3f}",
                    "health authority cannot admit a reroll rejected by D11",
                ),
            )

        BuildAwareShopRerollPolicy.recommend = recommend
        BuildAwareShopRerollPolicy._bond_shop_health_reroll_installed = True
