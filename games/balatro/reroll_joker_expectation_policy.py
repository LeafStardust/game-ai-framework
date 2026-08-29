from __future__ import annotations

"""Value unseen future Jokers from the authoritative public eligible catalogue.

A reroll reveals future shop items but does not make those hypothetical Jokers
visible acquisition decisions.  D2 is therefore deliberately *not* invoked while
valuing unseen reroll outcomes: doing so recursively ran the full wrapped acquisition
planner for hypothetical catalogue entries and could block an interactive SHOP
checkpoint for minutes.

The public eligible Joker catalogue is still preflighted for completeness.  Once the
catalogue is known to be representable, unseen Joker acquisition gain contributes a
conservative zero until an actual Joker becomes visible and normal D2/D14 authority
can evaluate its real identity, edition, price, and replacement context.  This is a
hard runtime boundary rather than a sampling/count heuristic.
"""

from dataclasses import dataclass

from games.balatro.build.judgement_expectation import RARITY_WEIGHTS, JudgementExpectationEvaluator
from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.shop_reroll_policy import BuildAwareShopRerollPolicy
from games.balatro.shop_utility_scale import ShopUtilityScale


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

        # Preflight the complete public catalogue without entering D2.  This retains
        # the existing fail-closed model-completeness contract while establishing a
        # hard authority boundary: hypothetical reroll outcomes cannot recursively
        # invoke visible-item acquisition planning.
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
                "future Joker uses the authoritative public eligible rarity pools",
                f"eligible public outcomes={total_records}",
                "hypothetical unseen Joker acquisition gain is deferred until the item is visible",
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
