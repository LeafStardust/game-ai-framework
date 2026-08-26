from __future__ import annotations

"""Use public eligible-Joker D2 expectation for unopened Buffoon packs.

The historical D8 model assigned Buffoon offers a fixed hit probability/value and
hard-vetoed the family when Joker slots were full. That capacity veto became stale
once D9 gained an explicit sell -> reobserve -> select replacement transaction.

This production authority values one random Buffoon Joker from the same public
eligible rarity/edition catalogue used by D11, at zero candidate purchase price
because pack contents are already sunk after opening. Candidate value is evaluated
at the cash that remains *after buying the pack*, so Bull/Bootstraps and other
cash-sensitive build effects see the state that will actually exist when the Joker
is selected. The pack transaction cost itself is still charged exactly once from
the original SHOP state.

The result is a conservative lower bound for packs with multiple visible offers:
choosing the best of two/four Jokers cannot be worse than the expectation of one
offer. We deliberately do not multiply by an independence assumption or inspect
hidden pack contents.
"""

from games.balatro.shop_booster_policy import (
    BUY,
    HOLD,
    BuildAwareShopBoosterPolicy,
    ShopBoosterRecommendation,
)
from games.balatro.shop_policy import BalatroShopPolicy
from games.balatro.reroll_joker_expectation_policy import RerollJokerExpectationEvaluator


def install_buffoon_booster_expectation_policy() -> None:
    if getattr(BuildAwareShopBoosterPolicy, "_public_buffoon_expectation_installed", False):
        return

    original_init = BuildAwareShopBoosterPolicy.__init__
    original_recommend = BuildAwareShopBoosterPolicy.recommend

    def init(self, *args, **kwargs):
        shop_policy = kwargs.get("shop_policy")
        original_init(self, *args, **kwargs)
        self._buffoon_shop_policy = shop_policy or BalatroShopPolicy()
        self._buffoon_joker_expectation = RerollJokerExpectationEvaluator(
            shop_policy=self._buffoon_shop_policy,
        )

    def recommend(self, state, action):
        family = self._family(action.target)
        if family != "BUFFOON":
            return original_recommend(self, state, action)
        if state.phase != "SHOP":
            raise ValueError("D8 booster acquisition requires SHOP phase")

        variant = self._variant(action.target)
        price = self._price(action.target)
        money_before = int(state.money)
        if price > money_before:
            return ShopBoosterRecommendation(
                decision=HOLD,
                action=action,
                family=family,
                variant=variant,
                total=self.parent_hold_baseline,
                rationale=(
                    f"Buffoon pack costs ${price} but only ${money_before} is available",
                ),
            )

        money_after_pack = money_before - price
        expectation = self._buffoon_joker_expectation.evaluate(
            state,
            money=money_after_pack,
            expected_price=0,
        )
        if not expectation.complete:
            return ShopBoosterRecommendation(
                decision=HOLD,
                action=action,
                family=family,
                variant=variant,
                total=self.parent_hold_baseline,
                rationale=(
                    "Buffoon pack public Joker expectation incomplete; HOLD fails closed",
                    *expectation.rationale,
                ),
            )

        option_utility = max(0.0, float(expectation.expected_gain))
        resource_cost = self.resource_valuator.money_spend_cost(
            money=money_before,
            spend=price,
            price_weight=self.thresholds.price_weight,
            interest_weight=self.thresholds.interest_weight,
            reserve_target=self.thresholds.reserve_target,
            reserve_weight=self.thresholds.reserve_weight,
            vouchers=getattr(state, "vouchers", ()),
            jokers=getattr(state, "jokers", ()),
        )
        advantage = option_utility - float(resource_cost.total)
        decision = (
            BUY
            if option_utility > 0.0
            and advantage > float(self.thresholds.minimum_buy_advantage)
            else HOLD
        )
        offer_count, selection_count = self.PACK_LAYOUTS[family][variant]
        total = self.parent_hold_baseline + advantage
        return ShopBoosterRecommendation(
            decision=decision,
            action=action,
            family=family,
            variant=variant,
            total=total,
            advantage_over_save=advantage,
            option_utility=option_utility,
            build_need_score=0.0,
            per_offer_hit_probability=0.0,
            at_least_one_hit_probability=0.0,
            offer_count=offer_count,
            selection_count=selection_count,
            runway_factor=self._runway_factor(max(1, int(getattr(state, "ante", 1) or 1))),
            price_penalty=resource_cost.direct,
            interest_penalty=resource_cost.interest,
            reserve_penalty=resource_cost.reserve,
            rationale=(
                f"booster family=BUFFOON variant={variant}",
                "Buffoon option value uses one-offer public eligible-Joker D2/D14 expectation",
                f"visible layout offers={offer_count} selections={selection_count}",
                "one-offer expectation is a conservative lower bound; no independence/best-of-N multiplier is invented",
                f"candidate scoring cash=${money_before}->${money_after_pack} after pack purchase",
                f"public-pool one-offer option utility={option_utility:.3f}",
                f"pack purchase resource cost={resource_cost.total:.3f}",
                f"D8 advantage over SAVE=0 is {advantage:.3f}; required>{self.thresholds.minimum_buy_advantage:.3f}",
                "full Joker roster remains valid because D9 can execute sell -> reobserve -> select replacement",
                *expectation.rationale,
                "unopened Buffoon contents are not inspected",
            ),
        )

    BuildAwareShopBoosterPolicy.__init__ = init
    BuildAwareShopBoosterPolicy.recommend = recommend
    BuildAwareShopBoosterPolicy._public_buffoon_expectation_installed = True
