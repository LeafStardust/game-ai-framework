from __future__ import annotations

"""Canonical mechanical authority for Jokers that scale whenever a Planet is used.

A Planet-use scaler changes the meaning of every Planet: even an off-hand Planet is
both a permanent hand upgrade and guaranteed permanent scaler progress. Ordinary
hand-relevance/headroom conservatism therefore must not suppress that mechanic.
Resource safety remains authoritative; this layer never spends below the configured
cash reserve or overrides the early-spend sanity guard.
"""

from dataclasses import replace


_PLANET_USE_SCALERS = frozenset({"ConstellationJoker"})


def has_planet_use_scaler(state) -> bool:
    """Return whether public owned-Joker state contains an active Planet-use scaler."""
    return any(
        type(joker).__name__ in _PLANET_USE_SCALERS
        and not bool(getattr(joker, "debuffed", False))
        for joker in tuple(getattr(state, "jokers", ()) or ())
    )


def _category(candidate) -> str:
    return str(getattr(candidate, "category", "") or "").upper()


def install_planet_scaler_authority() -> None:
    # Local imports avoid making the lightweight capability helper participate in
    # the live/shop import graph until Balatro policy registration is complete.
    from games.balatro.actions import BUY_AND_USE_CONSUMABLE, BalatroAction
    from games.balatro.live.consumable_timing import LiveConsumableTimingPolicy
    from games.balatro.live.consumable_timing_core import USE
    from games.balatro.shop_booster_policy import BUY as BOOSTER_BUY
    from games.balatro.shop_booster_policy import BuildAwareShopBoosterPolicy
    from games.balatro.shop_consumable_policy import BUY_AND_USE
    from games.balatro.shop_consumable_policy import ConsumableAcquisitionDecision
    from games.balatro.shop_consumable_policy import ConsumableAcquisitionOption
    from games.balatro.shop_consumable_policy import ConsumableAcquisitionPolicy

    if not getattr(BuildAwareShopBoosterPolicy, "_planet_scaler_authority_installed", False):
        original_build_need = BuildAwareShopBoosterPolicy._build_need
        original_recommend = BuildAwareShopBoosterPolicy.recommend

        def build_need(self, state, profile, *, family: str):
            if family == "CELESTIAL" and has_planet_use_scaler(state):
                return 1.0, (
                    "Planet-use scaler active: every offered Planet also gives guaranteed permanent scaler progress",
                )
            return original_build_need(self, state, profile, family=family)

        def booster_recommend(self, state, action):
            result = original_recommend(self, state, action)
            if result.family != "CELESTIAL" or not has_planet_use_scaler(state):
                return result
            if result.should_buy:
                return replace(
                    result,
                    rationale=(
                        *result.rationale,
                        "Planet-scaler authority: Celestial purchase directly advances the active scaling engine",
                    ),
                )

            # Only undo the ordinary Planet-headroom veto. A HOLD produced by D8
            # economics or the earlier survival-cash guard remains authoritative.
            headroom_veto = any(
                "no marginal hand-development headroom" in str(note)
                for note in tuple(result.rationale or ())
            )
            if not headroom_veto:
                return result
            price = int(self._price(action.target))
            money_after = int(state.money) - price
            reserve = int(self.thresholds.reserve_target)
            if money_after < reserve:
                return result
            return replace(
                result,
                decision=BOOSTER_BUY,
                rationale=(
                    *result.rationale,
                    "Planet-scaler authority overrides ordinary hand-development headroom: every Planet advances the scaler",
                    f"post-purchase reserve remains safe: ${money_after} >= ${reserve}",
                ),
            )

        BuildAwareShopBoosterPolicy._build_need = build_need
        BuildAwareShopBoosterPolicy.recommend = booster_recommend
        BuildAwareShopBoosterPolicy._planet_scaler_authority_installed = True

    if not getattr(ConsumableAcquisitionPolicy, "_planet_scaler_authority_installed", False):
        original_decide = ConsumableAcquisitionPolicy.decide

        def consumable_decide(self, state, candidate):
            result = original_decide(self, state, candidate)
            if _category(candidate) != "PLANET" or not has_planet_use_scaler(state):
                return result

            price = int(self._price(candidate))
            economics = self._economics(state, candidate, occupy_slot=False)
            reserve = int(self.thresholds.reserve_target)
            if economics.money_after < reserve:
                return result

            # Using a Planet under Constellation is targetless and deterministic:
            # hand level increases and the scaler gains +0.1 XMult permanently.
            # Treat the direct transaction as an authority decision rather than
            # asking ordinary off-path hand relevance to value the same mechanic.
            option = ConsumableAcquisitionOption(
                mode=BUY_AND_USE,
                build_gain=max(
                    0.0,
                    max(
                        (float(getattr(item, "build_gain", 0.0)) for item in result.options),
                        default=0.0,
                    ),
                ),
                immediate_gain=0.1,
                total_advantage=max(
                    float(self.thresholds.minimum_buy_and_use_advantage) + 0.001,
                    0.351,
                ),
                economics=economics,
                eligible=True,
                executable_action=BalatroAction(BUY_AND_USE_CONSUMABLE, target=candidate),
                rationale=(
                    "Planet-use scaler authority: Planet use guarantees permanent +0.1 XMult scaler growth",
                    f"price=${price}; money after=${economics.money_after}; reserve=${reserve}",
                ),
            )
            return ConsumableAcquisitionDecision(
                action=BUY_AND_USE,
                candidate=result.candidate,
                selected=option,
                options=(option, *tuple(result.options)),
                thresholds=result.thresholds,
                rationale=(
                    "selected D4 mode=BUY_AND_USE by active Planet-scaler authority",
                    *option.rationale,
                    *tuple(result.rationale or ()),
                ),
            )

        ConsumableAcquisitionPolicy.decide = consumable_decide
        ConsumableAcquisitionPolicy._planet_scaler_authority_installed = True

    if not getattr(LiveConsumableTimingPolicy, "_planet_scaler_authority_installed", False):
        original_timing_recommend = LiveConsumableTimingPolicy.recommend

        def timing_recommend(self, state, consumable):
            result = original_timing_recommend(self, state, consumable)
            if _category(consumable) != "PLANET" or not has_planet_use_scaler(state):
                return result
            return replace(
                result,
                decision=USE,
                rationale=(
                    "USE: active Planet-use scaler makes immediate Planet consumption permanent engine growth",
                    "holding the Planet provides no compensating scaler value",
                    *tuple(result.rationale or ()),
                ),
            )

        LiveConsumableTimingPolicy.recommend = timing_recommend
        LiveConsumableTimingPolicy._planet_scaler_authority_installed = True
