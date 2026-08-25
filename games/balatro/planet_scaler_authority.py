from __future__ import annotations

"""Shared mechanical authority for Jokers that scale whenever a Planet is used.

D4 loose-Planet acquisition and D7 held-Planet timing consume
``has_planet_use_scaler`` directly in their native decision owners. The installer
remains only for D8 Celestial acquisition because D8 is additionally wrapped by the
legacy Planet-spend/headroom layer during package registration.
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


def install_planet_scaler_authority() -> None:
    """Install only the remaining D8 Celestial acquisition authority.

    D4 and D7 are intentionally not monkey-patched here. Their core policies know
    the mechanic directly, preventing duplicated decisions and wrapper-order bugs.
    """
    from games.balatro.shop_booster_policy import BUY as BOOSTER_BUY
    from games.balatro.shop_booster_policy import BuildAwareShopBoosterPolicy

    if getattr(BuildAwareShopBoosterPolicy, "_planet_scaler_authority_installed", False):
        return

    original_build_need = BuildAwareShopBoosterPolicy._build_need
    original_recommend = BuildAwareShopBoosterPolicy.recommend

    def build_need(self, state, profile, *, family: str):
        if family == "CELESTIAL" and has_planet_use_scaler(state):
            return 1.0, (
                "Planet-use scaler active: every offered Planet gives guaranteed permanent scaler progress",
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

        # Only undo the ordinary hand-development-headroom HOLD. D8 economics and
        # reserve protection remain authoritative.
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
