from __future__ import annotations

"""Replace D11's fixed future-Joker utility with public-pool D2 expectation.

A reroll does not reveal the future Joker, its edition, or its exact price. The live
observer does, however, expose the current eligible Joker catalogue by rarity plus
Balatro's public edition-rate multiplier. D11 can therefore integrate the *value*
of a future Joker over that catalogue without sampling RNG or reading pool order.

The unseen price remains the existing explicit D11 expected-price prior. Each
catalogue branch is assigned that price, passed through the ordinary Red/White D2
acquisition/replacement policy, then normalized through D14's shared Joker utility
scale. If any eligible outcome cannot be modeled, the Joker future-offer branch
fails closed to END_SHOP rather than renormalizing over only understood cards.
"""

import copy
from dataclasses import dataclass
from types import SimpleNamespace

from games.balatro.build import JokerBuildTransitionPlanner
from games.balatro.build.judgement_expectation import RARITY_WEIGHTS, JudgementExpectationEvaluator
from games.balatro.build.wraith_expectation import _edition_probabilities
from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy
from games.balatro.shop_reroll_policy import BuildAwareShopRerollPolicy
from games.balatro.shop_utility_scale import ShopUtilityScale


@dataclass(frozen=True)
class RerollJokerExpectation:
    complete: bool
    expected_gain: float
    outcome_count: int
    rationale: tuple[str, ...] = ()


class RerollJokerExpectationEvaluator:
    def __init__(self, *, shop_policy) -> None:
        self.shop_policy = shop_policy
        self.utility_scale = ShopUtilityScale(shop_policy)
        self.joker_factory = LiveJokerFactory()
        self.joker_policy = PlaybookJokerAcquisitionPolicy(
            JokerBuildTransitionPlanner(
                minimum_add_gain=0.0,
                minimum_replacement_delta=0.0,
            )
        )

    def evaluate(self, state, *, money: int, expected_price: int) -> RerollJokerExpectation:
        if str(getattr(state, "stake_name", "WHITE") or "WHITE").upper() != "WHITE":
            return self._incomplete("future-Joker expectation is currently scoped to White Stake")
        if not bool(getattr(state, "joker_generation_pool_observed", False)):
            return self._incomplete("authoritative public Joker generation pool was not observed")

        projected = state.copy()
        projected.money = max(0, int(money))
        visible_hands = tuple(getattr(projected, "visible_poker_hands", ()) or ())
        pools = dict(getattr(projected, "joker_generation_pools", {}) or {})
        editions = _edition_probabilities(
            float(getattr(projected, "joker_generation_edition_rate", 1.0) or 1.0)
        )

        rarity_means: dict[str, float] = {}
        outcome_count = 0
        for rarity in RARITY_WEIGHTS:
            records = list(pools.get(rarity, ()) or ())
            if not records:
                records = [
                    {
                        "center": "j_joker",
                        "label": "Joker",
                        "ability_name": "Joker",
                        "ability_set": "JOKER",
                        "rarity": "COMMON",
                    }
                ]

            values: list[float] = []
            for record in records:
                expanded = JudgementExpectationEvaluator._initial_state_records(
                    record,
                    visible_hands,
                )
                if expanded is None:
                    return self._incomplete(
                        f"future Joker initial state is unresolved for {record.get('label') or record.get('center')}",
                        outcome_count,
                    )

                initial_state_values: list[float] = []
                for branch_record in expanded:
                    base = self.joker_factory.create(dict(branch_record))
                    if base is None:
                        return self._incomplete(
                            f"eligible {rarity} future Joker is not modeled: {record.get('label') or record.get('center')}",
                            outcome_count,
                        )

                    edition_value = 0.0
                    for edition, probability in editions:
                        candidate = copy.deepcopy(base)
                        candidate.edition = edition
                        # Exact future shop price is unknown before the reroll. Keep
                        # D11's explicit expected-price prior, but let D2/D14 own all
                        # build, replacement, edition, slot, and economy semantics.
                        candidate.price = int(expected_price)
                        candidate.cost = int(expected_price)
                        try:
                            decision = self.joker_policy.decide(projected, candidate)
                        except (AttributeError, KeyError, RuntimeError, TypeError, ValueError, ZeroDivisionError) as exc:
                            return self._incomplete(
                                f"future Joker D2 valuation failed for {record.get('label') or record.get('center')}: {type(exc).__name__}: {exc}",
                                outcome_count,
                            )

                        selected = getattr(decision, "selected", None)
                        if selected is None:
                            gain = 0.0
                        else:
                            source = (
                                "JOKER_REPLACE_SELL"
                                if str(getattr(decision, "action", "")) == "REPLACE"
                                else "JOKER_BUY"
                            )
                            executable = SimpleNamespace(
                                decision=decision,
                                candidate=candidate,
                                source=source,
                            )
                            gain = max(
                                0.0,
                                float(self.utility_scale.joker_gain(projected, executable).gain),
                            )
                        edition_value += float(probability) * gain

                    initial_state_values.append(edition_value)

                values.append(sum(initial_state_values) / len(initial_state_values))
                outcome_count += 1

            rarity_means[rarity] = sum(values) / len(values)

        expected = sum(
            float(RARITY_WEIGHTS[rarity]) * rarity_means[rarity]
            for rarity in RARITY_WEIGHTS
        )
        return RerollJokerExpectation(
            complete=True,
            expected_gain=expected,
            outcome_count=outcome_count,
            rationale=(
                "future Joker uses public eligible rarity pools and D2/D14 normalized acquisition value",
                "rarity mixture Common=0.70 Uncommon=0.25 Rare=0.05",
                f"eligible modeled outcomes={outcome_count}",
                f"unseen Joker expected-price prior=${int(expected_price)}",
                f"expected actionable Joker normalized gain={expected:.3f}",
                "future exact Joker, edition, price, RNG state, pseudoseed, and pool order are not observed",
            ),
        )

    @staticmethod
    def _incomplete(reason: str, outcome_count: int = 0) -> RerollJokerExpectation:
        return RerollJokerExpectation(
            complete=False,
            expected_gain=0.0,
            outcome_count=outcome_count,
            rationale=(
                reason,
                "future-Joker reroll expectation fails closed; eligible outcomes are never dropped",
            ),
        )


def install_reroll_joker_expectation_policy() -> None:
    if getattr(BuildAwareShopRerollPolicy, "_public_joker_expectation_installed", False):
        return

    original_init = BuildAwareShopRerollPolicy.__init__
    original_future_offer_score = BuildAwareShopRerollPolicy._future_offer_score

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.reroll_joker_expectation = RerollJokerExpectationEvaluator(
            shop_policy=self.shop_policy,
        )

    def future_offer_score(self, state, offer, *, money: int, thresholds):
        if str(getattr(offer, "family", "")).upper() != "JOKER":
            return original_future_offer_score(
                self,
                state,
                offer,
                money=money,
                thresholds=thresholds,
            )

        hold = float(self.shop_policy.hold_bias)
        price = int(getattr(offer, "expected_price", 0) or 0)
        if price > int(money):
            return hold

        expectation = self.reroll_joker_expectation.evaluate(
            state,
            money=int(money),
            expected_price=price,
        )
        if not expectation.complete:
            return hold
        return hold + max(0.0, float(expectation.expected_gain))

    BuildAwareShopRerollPolicy.__init__ = init
    BuildAwareShopRerollPolicy._future_offer_score = future_offer_score
    BuildAwareShopRerollPolicy._public_joker_expectation_installed = True
