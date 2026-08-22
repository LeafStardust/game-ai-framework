from __future__ import annotations

"""Standard Pack support for the Blue Joker/Hologram deck-growth composition."""

from dataclasses import replace

from games.balatro.shop_booster_policy import BuildAwareShopBoosterPolicy


_DECK_GROWTH_SCORERS = frozenset({"bluejoker", "hologramjoker"})
_DECK_GROWTH_SUPPORT_VALUE = 1.0


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _token(item: object) -> str:
    type_token = _normalize(type(item).__name__)
    if type_token and type_token not in {"simplenamespace", "object"}:
        return type_token if type_token.endswith("joker") else type_token + "joker"
    for value in (
        getattr(item, "name", ""),
        getattr(item, "label", ""),
        getattr(item, "ability_name", ""),
    ):
        token = _normalize(value)
        if token:
            return token if token.endswith("joker") else token + "joker"
    return type_token


def _deck_growth_active(state) -> bool:
    return any(_token(joker) in _DECK_GROWTH_SCORERS for joker in getattr(state, "jokers", ()) or ())


def install_deck_growth_pack_policy() -> None:
    if getattr(BuildAwareShopBoosterPolicy, "_deck_growth_pack_policy_installed", False):
        return

    original_recommend = BuildAwareShopBoosterPolicy.recommend

    def recommend(self, state, action):
        result = original_recommend(self, state, action)
        if result.family != "STANDARD" or not _deck_growth_active(state):
            return result

        advantage = float(result.advantage_over_save) + _DECK_GROWTH_SUPPORT_VALUE
        total = float(result.total) + _DECK_GROWTH_SUPPORT_VALUE
        option_utility = float(result.option_utility) + _DECK_GROWTH_SUPPORT_VALUE
        decision = result.decision
        if advantage > self.thresholds.minimum_buy_advantage:
            decision = "BUY"

        return replace(
            result,
            decision=decision,
            total=total,
            advantage_over_save=advantage,
            option_utility=option_utility,
            rationale=(
                *result.rationale,
                "Blue Joker/Hologram deck-growth composition: Standard Pack support advances the growth engine whenever a playing card is selected",
                f"deck-growth pack support=+{_DECK_GROWTH_SUPPORT_VALUE:.3f}",
            ),
        )

    BuildAwareShopBoosterPolicy.recommend = recommend
    BuildAwareShopBoosterPolicy._deck_growth_pack_policy_installed = True
