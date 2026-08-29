from __future__ import annotations

"""Bound public future-Joker value without entering D2.

This module has two deliberately separate responsibilities:

* D11 rerolls do *not* run catalogue acquisition planning for hypothetical unseen
  Jokers.  The installer delegates those offers to D11's existing explicit static
  public shop prior, which is cheap and already models affordability, slot pressure,
  replacement pressure, and shop economics.
* Buffoon-pack and Antimatter literal evaluators also reuse
  :class:`RerollJokerExpectationEvaluator`.  Those callers need a real marginal
  public-pool Joker value.  The evaluator therefore uses a tightly bounded
  ``JokerBuildTransitionPlanner`` calculation, never the fully wrapped D2 acquisition
  policy that previously made a SHOP checkpoint take minutes.

The bounded evaluator keeps the full public rarity-pool and initial-state
probability denominators.  Large pools evaluate only a deterministic spread of
records; only the most-probable public edition branch is evaluated.  Omitted mass is
literal zero rather than being renormalized, so the result is a conservative lower
bound.  No RNG state, pseudoseed, pool order, or hidden future identity is read.
"""

import copy
from dataclasses import dataclass

from games.balatro.build import JokerBuildTransitionPlanner
from games.balatro.build.judgement_expectation import (
    RARITY_WEIGHTS,
    JudgementExpectationEvaluator,
    _bounded_indices,
)
from games.balatro.build.wraith_expectation import _edition_probabilities
from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.shop_reroll_policy import BuildAwareShopRerollPolicy
from games.balatro.shop_utility_scale import ShopUtilityScale


# Retained public/runtime-contract constants. The late SHOP runtime installer tightens
# ``_MAX_RECORDS_PER_RARITY`` to 1. ``_MAX_D2_EVALUATIONS`` is compatibility metadata
# only: this evaluator has a hard architectural rule that it never invokes D2.
_MAX_EXACT_PUBLIC_RECORDS = 24
_MAX_RECORDS_PER_RARITY = 3
_MAX_D2_EVALUATIONS = 12
_MAX_INITIAL_BRANCHES_PER_RECORD = 2
_MAX_EDITIONS_PER_RECORD = 1


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


def _bounded_editions(
    editions: tuple[tuple[object, float], ...],
    *,
    limit: int = _MAX_EDITIONS_PER_RECORD,
) -> tuple[tuple[object, float], ...]:
    """Return the most-probable public edition branches without renormalizing."""
    if limit <= 0 or not editions:
        return ()
    ranked = sorted(
        enumerate(editions),
        key=lambda item: (-float(item[1][1]), item[0]),
    )[:limit]
    selected = {index for index, _ in ranked}
    return tuple(branch for index, branch in enumerate(editions) if index in selected)


class RerollJokerExpectationEvaluator:
    """Conservative bounded marginal value for the observed eligible Joker pool.

    Despite the historical class name, D11 rerolls no longer consume this value.
    Buffoon and Antimatter do because they need literal public-pool capacity/replacement
    value.  The evaluator stops at the build-transition layer and never enters D2.
    """

    def __init__(self, *, shop_policy) -> None:
        self.shop_policy = shop_policy
        self.utility_scale = ShopUtilityScale(shop_policy)
        self.joker_factory = LiveJokerFactory()
        self.joker_planner = JokerBuildTransitionPlanner(
            minimum_add_gain=0.0,
            minimum_replacement_delta=0.0,
        )

    def evaluate(self, state, *, money: int, expected_price: int) -> RerollJokerExpectation:
        # Buffoon/Antimatter use zero acquisition price here; D11 rerolls use their
        # own static prior and shop economics. Keep the parameters for the established
        # shared call surface without letting this build-only layer duplicate D2.
        del money, expected_price

        if str(getattr(state, "stake_name", "WHITE") or "WHITE").upper() != "WHITE":
            return self._incomplete("future-Joker expectation is currently scoped to White Stake")
        if not bool(getattr(state, "joker_generation_pool_observed", False)):
            return self._incomplete("authoritative public Joker generation pool was not observed")

        visible_hands = tuple(getattr(state, "visible_poker_hands", ()) or ())
        pools = dict(getattr(state, "joker_generation_pools", {}) or {})
        edition_rate = float(getattr(state, "joker_generation_edition_rate", 1.0) or 1.0)
        editions = tuple(
            (edition, float(probability))
            for edition, probability in _edition_probabilities(edition_rate)
            if float(probability) > 0.0
        )
        evaluated_editions = _bounded_editions(editions)
        if not evaluated_editions:
            return self._incomplete("public Joker edition distribution is empty")

        records_by_rarity: dict[str, list[dict[str, object]]] = {}
        expanded_by_rarity: dict[str, list[tuple[dict[str, object], ...]]] = {}
        total_records = 0

        # Preflight every public record cheaply. A bounded valuation must not hide an
        # unresolved eligible outcome merely because that record was not selected for
        # expensive build-transition evaluation.
        for rarity in RARITY_WEIGHTS:
            records = list(pools.get(rarity, ()) or ()) or [_fallback_record()]
            records_by_rarity[rarity] = records
            total_records += len(records)
            expanded_records: list[tuple[dict[str, object], ...]] = []
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
                expanded_records.append(branches)
            expanded_by_rarity[rarity] = expanded_records

        exact_records = total_records <= _MAX_EXACT_PUBLIC_RECORDS
        rarity_means: dict[str, float] = {}
        evaluated_records = 0
        evaluated_transitions = 0

        for rarity in RARITY_WEIGHTS:
            records = records_by_rarity[rarity]
            expanded_records = expanded_by_rarity[rarity]
            record_indices = (
                tuple(range(len(records)))
                if exact_records
                else _bounded_indices(len(records), _MAX_RECORDS_PER_RARITY)
            )
            rarity_value_sum = 0.0

            for record_index in record_indices:
                branches = expanded_records[record_index]
                branch_indices = _bounded_indices(
                    len(branches),
                    _MAX_INITIAL_BRANCHES_PER_RECORD,
                )
                branch_value_sum = 0.0

                for branch_index in branch_indices:
                    base = self.joker_factory.create(dict(branches[branch_index]))
                    if base is None:  # defensive; full preflight above already proved it
                        return self._incomplete(
                            f"eligible {rarity} future Joker became unmodeled",
                            total_records,
                        )

                    edition_value = 0.0
                    for edition, probability in evaluated_editions:
                        candidate = copy.deepcopy(base)
                        candidate.edition = edition
                        try:
                            transition = self.joker_planner.plan(state, candidate)
                        except (AttributeError, KeyError, RuntimeError, TypeError, ValueError, ZeroDivisionError) as exc:
                            return self._incomplete(
                                "future Joker build-transition valuation failed for "
                                f"{records[record_index].get('label') or records[record_index].get('center')}: "
                                f"{type(exc).__name__}: {exc}",
                                total_records,
                            )
                        evaluated_transitions += 1

                        action = str(getattr(transition, "action", "HOLD") or "HOLD").upper()
                        if action == "ADD":
                            gain = float(transition.candidate_value.total_gain)
                        elif action == "REPLACE" and transition.replacement is not None:
                            gain = float(transition.replacement.build_delta)
                        else:
                            gain = 0.0
                        edition_value += float(probability) * max(0.0, gain)

                    branch_value_sum += edition_value

                # Preserve the full initial-state denominator. Unevaluated branches
                # retain real probability mass at value zero.
                rarity_value_sum += branch_value_sum / float(len(branches))
                evaluated_records += 1

            # Preserve the full rarity-pool denominator. Unevaluated records retain
            # real probability mass at value zero.
            rarity_means[rarity] = rarity_value_sum / float(len(records))

        expected = sum(
            float(RARITY_WEIGHTS[rarity]) * rarity_means.get(rarity, 0.0)
            for rarity in RARITY_WEIGHTS
        )
        return RerollJokerExpectation(
            complete=True,
            expected_gain=max(0.0, float(expected)),
            outcome_count=total_records,
            rationale=(
                "future Joker uses the authoritative public eligible rarity pools",
                f"eligible public outcomes={total_records}",
                f"build-transition records evaluated={evaluated_records}",
                f"build-transition calls={evaluated_transitions}",
                f"edition branches evaluated={len(evaluated_editions)}/{len(editions)} without renormalization",
                "bounded build-transition expectation supports literal Buffoon replacement and Antimatter capacity value",
                "hypothetical unseen reroll acquisition gain is deferred until the item is visible; D11 rerolls use their static public prior",
                "reroll expectation never invokes D2 for hypothetical future Jokers",
                "unevaluated public probability mass contributes zero",
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
        # Paid speculative rerolls retain the established public-observability gate.
        # Without the authoritative Joker catalogue, every unseen offer family is
        # valued exactly at HOLD. A paid reroll therefore loses after resource cost,
        # while a genuinely free reroll can still take the intentional zero-cost tie.
        if not bool(getattr(state, "joker_generation_pool_observed", False)):
            return float(self.shop_policy.hold_bias)

        # Unseen reroll outcomes are not D2 acquisition decisions. Once the public
        # catalogue is observed, delegate every family to D11's bounded explicit
        # public/static prior rather than recursively evaluating hypothetical D2 buys.
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
