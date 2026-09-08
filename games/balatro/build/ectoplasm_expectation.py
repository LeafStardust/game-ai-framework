from __future__ import annotations

"""Public-state expectation for Ectoplasm.

Ectoplasm applies Negative to one uniformly random editionless owned Joker, reduces
permanent hand size by ``G.GAME.ecto_minus``, then increments that counter.  Target
identity does not change the slot effect: every eligible editionless Joker becomes
slot-neutral and therefore raises Joker capacity by exactly one.

The benefit is valued as the marginal public future-Joker acquisition opportunity at
``joker_slots + 1`` versus current capacity, reusing D11's eligible-pool D2/D14
expectation.  This deliberately omits speculative multi-shop lifetime value.  The
cost is the shared literal permanent hand-size opportunity model.
"""

from dataclasses import dataclass

from games.balatro.build.hand_size_opportunity import HandSizeOpportunityEvaluator
from games.balatro.joker_edition import joker_edition_name
from games.balatro.reroll_joker_expectation_policy import RerollJokerExpectationEvaluator


@dataclass(frozen=True)
class EctoplasmExpectation:
    available: bool
    complete: bool
    expected_capacity_gain: float
    hand_size_cost: float
    expected_total_gain: float
    eligible_joker_count: int
    hand_size_penalty: int
    rationale: tuple[str, ...] = ()


class EctoplasmExpectationEvaluator:
    EXPECTED_FUTURE_JOKER_PRICE = 5

    def __init__(
        self,
        *,
        hand_size: HandSizeOpportunityEvaluator | None = None,
        future_joker: RerollJokerExpectationEvaluator | None = None,
    ) -> None:
        self.hand_size = hand_size or HandSizeOpportunityEvaluator()
        # Do not construct a BalatroShopPolicy here. This evaluator is itself
        # installed underneath pack/shop policy constructors, and eagerly creating
        # another shop policy recursively rebuilds the entire D14/pack expectation
        # graph. Build the default future-Joker authority only when Ectoplasm is
        # actually evaluated, after the outer policy graph has finished wiring.
        self.future_joker = future_joker

    def _future_joker_evaluator(self) -> RerollJokerExpectationEvaluator:
        if self.future_joker is None:
            from games.balatro.shop_policy import BalatroShopPolicy

            self.future_joker = RerollJokerExpectationEvaluator(
                shop_policy=BalatroShopPolicy(),
            )
        return self.future_joker

    @staticmethod
    def _eligible_jokers(state) -> tuple[object, ...]:
        return tuple(
            joker
            for joker in tuple(getattr(state, "jokers", ()) or ())
            if joker_edition_name(joker) is None
        )

    def evaluate(self, state) -> EctoplasmExpectation:
        eligible = self._eligible_jokers(state)
        penalty = max(1, int(getattr(state, "ectoplasm_hand_size_penalty", 1) or 1))
        if not eligible:
            return EctoplasmExpectation(
                available=False,
                complete=True,
                expected_capacity_gain=0.0,
                hand_size_cost=0.0,
                expected_total_gain=0.0,
                eligible_joker_count=0,
                hand_size_penalty=penalty,
                rationale=("Ectoplasm unavailable: no editionless owned Joker is eligible",),
            )

        hand_cost = self.hand_size.evaluate(state, penalty=penalty)
        if not hand_cost.available or not hand_cost.complete:
            return EctoplasmExpectation(
                available=True,
                complete=False,
                expected_capacity_gain=0.0,
                hand_size_cost=0.0,
                expected_total_gain=0.0,
                eligible_joker_count=len(eligible),
                hand_size_penalty=penalty,
                rationale=(
                    "Ectoplasm deferred: permanent hand-size opportunity cost is incomplete",
                    *hand_cost.rationale,
                ),
            )

        future_joker = self._future_joker_evaluator()
        money = max(0, int(getattr(state, "money", 0) or 0))
        current = future_joker.evaluate(
            state,
            money=money,
            expected_price=self.EXPECTED_FUTURE_JOKER_PRICE,
        )
        expanded = state.copy()
        expanded.joker_slots = int(getattr(state, "joker_slots", 0) or 0) + 1
        with_slot = future_joker.evaluate(
            expanded,
            money=money,
            expected_price=self.EXPECTED_FUTURE_JOKER_PRICE,
        )
        if not current.complete or not with_slot.complete:
            notes = current.rationale if not current.complete else with_slot.rationale
            return EctoplasmExpectation(
                available=True,
                complete=False,
                expected_capacity_gain=0.0,
                hand_size_cost=float(hand_cost.build_value_loss),
                expected_total_gain=0.0,
                eligible_joker_count=len(eligible),
                hand_size_penalty=penalty,
                rationale=(
                    "Ectoplasm deferred: public future-Joker capacity expectation is incomplete",
                    *notes,
                ),
            )

        capacity_gain = max(0.0, float(with_slot.expected_gain) - float(current.expected_gain))
        cost = max(0.0, float(hand_cost.build_value_loss))
        total = capacity_gain - cost
        return EctoplasmExpectation(
            available=True,
            complete=True,
            expected_capacity_gain=capacity_gain,
            hand_size_cost=cost,
            expected_total_gain=total,
            eligible_joker_count=len(eligible),
            hand_size_penalty=penalty,
            rationale=(
                f"editionless eligible Jokers={len(eligible)}",
                "random eligible target identity is irrelevant to the +1 Joker-capacity effect",
                f"current public future-Joker normalized gain={current.expected_gain:.3f}",
                f"with one additional Joker slot gain={with_slot.expected_gain:.3f}",
                f"marginal Negative-slot option value={capacity_gain:.3f}",
                f"current Ectoplasm hand-size reduction={penalty}",
                *hand_cost.rationale,
                f"Ectoplasm net normalized gain={total:.3f}",
                "no hidden target, Joker identity, edition roll, RNG state, or future shop identity is observed",
            ),
        )
