from __future__ import annotations

"""Bound unseen future-Joker reroll valuation without entering D2.

A reroll reveals future shop items but does not create a visible acquisition decision.
Running the fully wrapped D2 acquisition planner over hypothetical catalogue entries
caused interactive SHOP decisions to take minutes. Production reroll valuation now
keeps that authority boundary strict: unseen Joker offers use D11's existing explicit
public/static shop prior, including its affordability, resource, slot and replacement
penalties. Actual visible Jokers continue to use normal D2/D14 authority.

The catalogue evaluator remains available as a cheap fail-closed completeness check
for callers/tests that need to verify that the observed public generation pool is
representable. It never invokes D2 and does not supply synthetic unseen-Joker value.
"""

from dataclasses import dataclass

from games.balatro.build.judgement_expectation import RARITY_WEIGHTS, JudgementExpectationEvaluator
from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.shop_reroll_policy import BuildAwareShopRerollPolicy
from games.balatro.shop_utility_scale import ShopUtilityScale


# Retained compatibility/runtime-contract constants. The legacy runtime-bound
# installer assigns the first two values; none authorize hypothetical D2 calls.
_MAX_EXACT_PUBLIC_RECORDS = 24
_MAX_RECORDS_PER_RARITY = 1
_MAX_D2_EVALUATIONS = 12


@dataclass(frozen=True)
class RerollJokerExpectation:
    complete: bool
    expected_gain: float
    outcome_count: int
    rationale: tuple[str, ...] = ()


def _fallback_record() -> dict[str, object]:
    return {
        "center": "j_joker",
        "label": "Joker",
        "ability_name": "Joker",
        "ability_set": "JOKER",
        "rarity": "COMMON",
    }


class RerollJokerExpectationEvaluator:
    def __init__(self, *, shop_policy) -> None:
        self.shop_policy = shop_policy
        self.utility_scale = ShopUtilityScale(shop_policy)
        self.joker_factory = LiveJokerFactory()

    def evaluate(self, state, *, money: int, expected_price: int) -> RerollJokerExpectation:
        del money, expected_price
        if str(getattr(state, "stake_name", "WHITE") or "WHITE").upper() != "WHITE":
            return self._incomplete("future-Joker expectation is currently scoped to White Stake")
        if not bool(getattr(state, "joker_generation_pool_observed", False)):
            return self._incomplete("authoritative public Joker generation pool was not observed")

        visible_hands = tuple(getattr(state, "visible_poker_hands", ()) or ())
        pools = dict(getattr(state, "joker_generation_pools", {}) or {})
        total_records = 0

        for rarity in RARITY_WEIGHTS:
            records = list(pools.get(rarity, ()) or ()) or [_fallback_record()]
            total_records += len(records)
            for record in records:
                expanded = JudgementExpectationEvaluator._initial_state_records(
                    record,
                    visible_hands,
                )
                if expanded is None:
                    return self._incomplete(
                        f"future Joker initial state is unresolved for {record.get('label') or record.get('center')}",
                        total_records,
                    )
                branches = tuple(dict(branch_record) for branch_record in expanded)
                if not branches:
                    return self._incomplete(
                        f"future Joker initial-state expansion is empty for {record.get('label') or record.get('center')}",
                        total_records,
                    )
                for branch_record in branches:
                    if self.joker_factory.create(branch_record) is None:
                        return self._incomplete(
                            f"eligible {rarity} future Joker is not modeled: {record.get('label') or record.get('center')}",
                            total_records,
                        )

        return RerollJokerExpectation(
            complete=True,
            expected_gain=0.0,
            outcome_count=total_records,
            rationale=(
                "future Joker uses the authoritative public eligible rarity pools for completeness only",
                f"eligible public outcomes={total_records}",
                "hypothetical unseen Joker acquisition value remains under the explicit D11 static shop prior",
                "reroll expectation never invokes D2 for hypothetical future Jokers",
                "unseen Joker identity, edition, price, RNG state, pseudoseed, and pool order are not observed",
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
                "future-Joker expectation fails closed; eligible outcomes are never silently dropped",
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
        # Unseen reroll outcomes are not D2 acquisition decisions. Delegate every
        # family, including JOKER, to D11's bounded explicit public/static prior.
        return original_future_offer_score(
            self,
            state,
            offer,
            money=money,
            thresholds=thresholds,
        )

    BuildAwareShopRerollPolicy.__init__ = init
    BuildAwareShopRerollPolicy._future_offer_score = future_offer_score
    BuildAwareShopRerollPolicy._public_joker_expectation_installed = True
