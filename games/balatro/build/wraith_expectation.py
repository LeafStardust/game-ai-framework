from __future__ import annotations

"""Public-state expectation for Wraith.

Wraith creates one Rare Joker and sets money to $0. The eligible Rare catalogue is
read from Balatro's current public pool metadata by the live-state adapter; this
module never samples the game's RNG or reads pool order.

Each modeled Rare Joker is evaluated against the post-Wraith ($0) build through the
existing whole-build Joker evaluator. Balatro's ordinary edition roll is integrated
analytically from the public ``edition_rate`` multiplier. The cash loss is charged on
the same RunResourceValuator coefficients used by the D14 shared shop scale.

If any eligible Rare outcome cannot be represented exactly enough by the framework,
the expectation fails closed instead of renormalizing over the subset we understand.
"""

import copy
from dataclasses import dataclass

from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.joker_edition import joker_edition_universal_value
from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.resource_value import RunResourceValuator


@dataclass(frozen=True)
class WraithJokerOutcome:
    center: str
    label: str
    expected_gain: float


@dataclass(frozen=True)
class WraithExpectation:
    available: bool
    complete: bool
    rare_outcomes: int
    expected_joker_gain: float
    cash_cost: float
    expected_total_gain: float
    outcomes: tuple[WraithJokerOutcome, ...] = ()
    rationale: tuple[str, ...] = ()


def _edition_probabilities(rate: float) -> tuple[tuple[str | None, float], ...]:
    """Return Balatro's non-guaranteed Joker edition distribution.

    ``poll_edition`` checks cumulative upper-tail thresholds in this order:
    Negative (0.003), Polychrome (0.006*rate), Holographic (0.02*rate),
    Foil (0.04*rate), then Base. Convert those thresholds into disjoint branch
    probabilities without assuming the thresholds remain ordered at unusual rates.
    """
    rate = max(0.0, float(rate))
    cumulative = 0.0
    branches: list[tuple[str | None, float]] = []
    for edition, tail in (
        ("NEGATIVE", 0.003),
        ("POLYCHROME", min(1.0, 0.006 * rate)),
        ("HOLOGRAPHIC", min(1.0, 0.020 * rate)),
        ("FOIL", min(1.0, 0.040 * rate)),
    ):
        next_cumulative = max(cumulative, min(1.0, float(tail)))
        probability = max(0.0, next_cumulative - cumulative)
        if probability > 0.0:
            branches.append((edition, probability))
        cumulative = next_cumulative
    if cumulative < 1.0:
        branches.append((None, 1.0 - cumulative))
    return tuple(branches)


class WraithExpectationEvaluator:
    def __init__(
        self,
        *,
        joker_factory: LiveJokerFactory | None = None,
        joker_value: JokerBuildValueEvaluator | None = None,
        resource_valuator: RunResourceValuator | None = None,
    ) -> None:
        self.joker_factory = joker_factory or LiveJokerFactory()
        self.joker_value = joker_value or JokerBuildValueEvaluator()
        self.resource_valuator = resource_valuator or RunResourceValuator()

    def evaluate(self, state) -> WraithExpectation:
        joker_slots = max(0, int(getattr(state, "joker_slots", 0) or 0))
        if len(tuple(getattr(state, "jokers", ()) or ())) >= joker_slots:
            return WraithExpectation(
                available=False,
                complete=True,
                rare_outcomes=0,
                expected_joker_gain=0.0,
                cash_cost=0.0,
                expected_total_gain=0.0,
                rationale=("Wraith requires a free Joker slot",),
            )

        if str(getattr(state, "stake_name", "WHITE") or "WHITE").upper() != "WHITE":
            return WraithExpectation(
                available=True,
                complete=False,
                rare_outcomes=0,
                expected_joker_gain=0.0,
                cash_cost=0.0,
                expected_total_gain=0.0,
                rationale=(
                    "Wraith expectation is currently scoped to White Stake; "
                    "higher-stake generated Joker stickers are not folded into this model",
                ),
            )

        if not bool(getattr(state, "joker_generation_pool_observed", False)):
            return WraithExpectation(
                available=True,
                complete=False,
                rare_outcomes=0,
                expected_joker_gain=0.0,
                cash_cost=0.0,
                expected_total_gain=0.0,
                rationale=("authoritative public Joker generation pool was not observed",),
            )

        pools = dict(getattr(state, "joker_generation_pools", {}) or {})
        records = list(pools.get("RARE", ()) or ())
        # Balatro's pool helper falls back to the base Joker if a requested pool is
        # empty. Preserve that behavior rather than treating an empty Rare pool as
        # impossible generation.
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

        post_cash_state = state.copy()
        post_cash_state.money = 0
        edition_rate = float(
            getattr(state, "joker_generation_edition_rate", 1.0) or 1.0
        )
        editions = _edition_probabilities(edition_rate)

        outcomes: list[WraithJokerOutcome] = []
        for record in records:
            base = self.joker_factory.create(dict(record))
            if base is None:
                return self._incomplete(
                    outcomes,
                    f"eligible Rare Joker is not modeled: {record.get('label') or record.get('center')}",
                )

            branch_value = 0.0
            try:
                for edition, probability in editions:
                    candidate = copy.deepcopy(base)
                    candidate.edition = edition
                    value = self.joker_value.evaluate(post_cash_state, candidate).total_gain
                    # Match the existing Joker acquisition convention: literal
                    # edition scoring is already visible to the whole-build scorer,
                    # while this universal term carries strategy-independent edition
                    # value such as Negative slot capacity.
                    value += joker_edition_universal_value(candidate)
                    branch_value += probability * float(value)
            except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
                return self._incomplete(
                    outcomes,
                    f"Rare Joker valuation failed for {record.get('label') or record.get('center')}: "
                    f"{type(exc).__name__}: {exc}",
                )

            outcomes.append(
                WraithJokerOutcome(
                    center=str(record.get("center") or ""),
                    label=str(record.get("label") or record.get("center") or ""),
                    expected_gain=branch_value,
                )
            )

        expected_joker = sum(outcome.expected_gain for outcome in outcomes) / len(outcomes)
        money = max(0, int(getattr(state, "money", 0) or 0))
        cash = self.resource_valuator.money_spend_cost(
            money=money,
            spend=money,
            price_weight=0.35,
            interest_weight=1.25,
            reserve_target=5,
            reserve_weight=0.45,
            vouchers=getattr(state, "vouchers", ()),
            jokers=getattr(state, "jokers", ()),
        )
        total = expected_joker - float(cash.total)
        return WraithExpectation(
            available=True,
            complete=True,
            rare_outcomes=len(outcomes),
            expected_joker_gain=expected_joker,
            cash_cost=float(cash.total),
            expected_total_gain=total,
            outcomes=tuple(outcomes),
            rationale=(
                "uniform expectation over the current public eligible Rare Joker pool",
                f"eligible Rare outcomes={len(outcomes)}",
                f"public edition_rate={edition_rate:.3f}",
                f"expected Rare Joker build/edition gain={expected_joker:.3f}",
                f"Wraith money transition=${money}->$0 shared resource cost={cash.total:.3f}",
                *cash.notes,
                f"expected Wraith net gain={total:.3f}",
                "no RNG sample, pseudoseed, pool order, or selected outcome read",
            ),
        )

    @staticmethod
    def _incomplete(
        outcomes: list[WraithJokerOutcome],
        reason: str,
    ) -> WraithExpectation:
        return WraithExpectation(
            available=True,
            complete=False,
            rare_outcomes=len(outcomes),
            expected_joker_gain=0.0,
            cash_cost=0.0,
            expected_total_gain=0.0,
            outcomes=tuple(outcomes),
            rationale=(reason, "Wraith expectation fails closed; eligible outcomes are never dropped"),
        )
