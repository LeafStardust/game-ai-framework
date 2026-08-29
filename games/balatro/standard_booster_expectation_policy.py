from __future__ import annotations

"""Bounded public generator expectation for unopened Standard boosters.

D8 integrates the finite public Standard-card generator using only literal static D9
card modifiers. It deliberately omits contextual B6 profiling and whole-build deck-
growth projection: those belong to the real visible D9 decision, not an unopened
SHOP expectation loop. The omitted contextual mass is therefore a conservative zero.
"""

from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.shop_booster_policy import (
    BUY,
    HOLD,
    BuildAwareShopBoosterPolicy,
    ShopBoosterRecommendation,
)


_RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
_SUITS = ("Hearts", "Diamonds", "Clubs", "Spades")
_ENHANCEMENTS = (
    "m_bonus",
    "m_mult",
    "m_wild",
    "m_glass",
    "m_steel",
    "m_stone",
    "m_gold",
    "m_lucky",
)
_SEALS = ("Red", "Blue", "Gold", "Purple")


def _edition_distribution(rate: float) -> tuple[tuple[str | None, float], ...]:
    rate = max(0.0, float(rate))
    poly_tail = min(1.0, 0.012 * rate)
    holo_tail = min(1.0, 0.040 * rate)
    foil_tail = min(1.0, 0.080 * rate)
    return (
        (None, max(0.0, 1.0 - foil_tail)),
        ("Foil", max(0.0, foil_tail - holo_tail)),
        ("Holographic", max(0.0, holo_tail - poly_tail)),
        ("Polychrome", max(0.0, poly_tail)),
    )


def _enhancement_distribution() -> tuple[tuple[str | None, float], ...]:
    return ((None, 0.60),) + tuple((name, 0.05) for name in _ENHANCEMENTS)


def _seal_distribution() -> tuple[tuple[str | None, float], ...]:
    return ((None, 0.80),) + tuple((name, 0.05) for name in _SEALS)


class StandardBoosterExpectationEvaluator:
    @staticmethod
    def _static_visible_card_value(
        *,
        rank: str,
        enhancement: str | None,
        edition: str | None,
        seal: str | None,
    ) -> float:
        score = float(BalatroPackPolicy.RANK_VALUE.get(str(rank), 0.0))
        if enhancement:
            score += float(BalatroPackPolicy.PLAYING_ENHANCEMENT_VALUE.get(str(enhancement), 0.0))
        edition_text = str(edition or "").upper()
        if edition_text:
            score += float(BalatroPackPolicy.EDITION_BONUS.get(edition_text, 0.0))
        seal_text = str(seal or "").upper()
        if seal_text:
            score += float(BalatroPackPolicy.PLAYING_SEAL_VALUE.get(seal_text, 0.0))
        if not enhancement and not edition_text and not seal_text:
            score -= float(BalatroPackPolicy.VANILLA_CARD_DILUTION_PENALTY)
        return score

    def evaluate(self, state) -> tuple[float, float, tuple[str, ...]]:
        edition_rate = max(
            0.0,
            float(getattr(state, "joker_generation_edition_rate", 1.0) or 1.0),
        )
        edition_distribution = _edition_distribution(edition_rate)
        total_probability = 0.0
        expected_option_value = 0.0
        positive_probability = 0.0
        front_probability = 1.0 / float(len(_RANKS) * len(_SUITS))

        for rank in _RANKS:
            for _suit in _SUITS:
                for enhancement, enhancement_probability in _enhancement_distribution():
                    for edition, edition_probability in edition_distribution:
                        for seal, seal_probability in _seal_distribution():
                            probability = (
                                front_probability
                                * enhancement_probability
                                * edition_probability
                                * seal_probability
                            )
                            if probability <= 0.0:
                                continue
                            score = self._static_visible_card_value(
                                rank=rank,
                                enhancement=enhancement,
                                edition=edition,
                                seal=seal,
                            )
                            option_value = max(0.0, float(score))
                            total_probability += probability
                            expected_option_value += probability * option_value
                            if option_value > 0.0:
                                positive_probability += probability

        if abs(total_probability - 1.0) > 1e-9:
            return 0.0, 0.0, (
                f"Standard generator probability mass incomplete={total_probability:.12f}",
            )
        return expected_option_value, positive_probability, (
            "Standard one-offer EV uses exact public rank/suit/enhancement/seal/edition distribution",
            "unopened D8 uses static visible-card mechanics only; B6 profile and whole-build deck-growth projection are deferred to real D9",
            f"public edition_rate={edition_rate:.6f}",
            f"one-offer positive-choice probability={positive_probability:.6f}",
            f"one-offer sunk-cost option EV={expected_option_value:.6f}",
            "best-of-3/5 improvement and contextual build upside are omitted conservatively",
        )


def install_standard_booster_expectation_policy() -> None:
    if getattr(BuildAwareShopBoosterPolicy, "_standard_generator_expectation_installed", False):
        return

    original_init = BuildAwareShopBoosterPolicy.__init__
    original_recommend = BuildAwareShopBoosterPolicy.recommend

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self._standard_generator_expectation = StandardBoosterExpectationEvaluator()

    def recommend(self, state, action):
        family = self._family(action.target)
        if family != "STANDARD":
            return original_recommend(self, state, action)
        if state.phase != "SHOP":
            raise ValueError("D8 booster acquisition requires SHOP phase")

        variant = self._variant(action.target)
        price = self._price(action.target)
        if price > int(state.money):
            return ShopBoosterRecommendation(
                decision=HOLD,
                action=action,
                family=family,
                variant=variant,
                total=self.parent_hold_baseline,
                rationale=(f"Standard pack costs ${price} but only ${state.money} is available",),
            )

        option_utility, per_offer_positive, expectation_notes = self._standard_generator_expectation.evaluate(state)
        offer_count, selection_count = self.PACK_LAYOUTS[family][variant]
        resource_cost = self.resource_valuator.money_spend_cost(
            money=int(state.money),
            spend=price,
            price_weight=self.thresholds.price_weight,
            interest_weight=self.thresholds.interest_weight,
            reserve_target=self.thresholds.reserve_target,
            reserve_weight=self.thresholds.reserve_weight,
            vouchers=getattr(state, "vouchers", ()),
            jokers=getattr(state, "jokers", ()),
        )
        advantage = float(option_utility) - float(resource_cost.total)
        decision = BUY if option_utility > 0.0 and advantage > float(self.thresholds.minimum_buy_advantage) else HOLD
        return ShopBoosterRecommendation(
            decision=decision,
            action=action,
            family=family,
            variant=variant,
            total=float(self.parent_hold_baseline) + advantage,
            advantage_over_save=advantage,
            option_utility=float(option_utility),
            build_need_score=0.0,
            per_offer_hit_probability=float(per_offer_positive),
            at_least_one_hit_probability=float(per_offer_positive),
            offer_count=offer_count,
            selection_count=selection_count,
            runway_factor=self._runway_factor(max(1, int(getattr(state, "ante", 1) or 1))),
            price_penalty=resource_cost.direct,
            interest_penalty=resource_cost.interest,
            reserve_penalty=resource_cost.reserve,
            rationale=(
                f"booster family=STANDARD variant={variant}",
                *expectation_notes,
                f"visible layout offers={offer_count} selections={selection_count}",
                f"pack purchase resource cost={resource_cost.total:.3f}",
                f"D8 conservative Standard advantage over SAVE=0 is {advantage:.3f}",
                "unopened Standard contents are not inspected",
            ),
        )

    BuildAwareShopBoosterPolicy.__init__ = init
    BuildAwareShopBoosterPolicy.recommend = recommend
    BuildAwareShopBoosterPolicy._standard_generator_expectation_installed = True
