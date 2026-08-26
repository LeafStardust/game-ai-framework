from __future__ import annotations

"""Value unseen future Jokers from the authoritative public eligible catalogue.

Small public pools are integrated exactly through the ordinary Red/White D2/D14
path.  A vanilla live pool is much larger: evaluating every eligible Joker, every
public initial-state branch, and every edition through the fully wrapped acquisition
policy can block an interactive SHOP checkpoint for minutes.

For large pools this module therefore computes a deterministic conservative lower
bound.  Every public record is still preflighted for model completeness.  A
rarity-stratified subset is then passed through full D2/D14; unevaluated records and
edition branches keep their real probability mass but contribute zero instead of
being dropped or renormalized.  The estimate can only understate future option
value.  It never reads RNG state, pseudoseeds, pool order, future identities, or
hidden prices.
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


# Deterministic fixtures and genuinely small public pools retain the exact model.
_MAX_EXACT_PUBLIC_RECORDS = 24
# Large live pools sample evenly across each rarity, never by Joker name/tier.
_MAX_RECORDS_PER_RARITY = 3
# Hard cap on expensive fully wrapped D2 calls.  Unspent probability mass is zero.
_MAX_D2_EVALUATIONS = 48


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


def _stratified_indices(size: int, limit: int) -> tuple[int, ...]:
    if size <= 0:
        return ()
    if size <= limit:
        return tuple(range(size))
    # Equal-width deterministic strata over the observer-provided public catalogue.
    # Ordering is used only to obtain coverage; no semantic value is inferred from it.
    return tuple(min(size - 1, (index * size) // limit) for index in range(limit))


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
        editions = tuple(
            (edition, float(probability))
            for edition, probability in _edition_probabilities(
                float(getattr(projected, "joker_generation_edition_rate", 1.0) or 1.0)
            )
            if float(probability) > 0.0
        )

        records_by_rarity: dict[str, list[dict[str, object]]] = {}
        expanded_by_rarity: dict[str, list[tuple[dict[str, object], ...]]] = {}
        total_records = 0

        # Preflight the entire public pool cheaply.  A bounded valuation must never
        # hide an unresolved/unmodeled eligible outcome merely because it was not
        # selected for expensive D2 scoring.
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
                    if self.joker_factory.create(dict(branch_record)) is None:
                        return self._incomplete(
                            f"eligible {rarity} future Joker is not modeled: {record.get('label') or record.get('center')}",
                            total_records,
                        )
                expanded_records.append(branches)
            expanded_by_rarity[rarity] = expanded_records

        exact = total_records <= _MAX_EXACT_PUBLIC_RECORDS
        rarity_means: dict[str, float] = {}
        evaluated_records = 0
        d2_evaluations = 0
        budget_exhausted = False

        for rarity in RARITY_WEIGHTS:
            records = records_by_rarity[rarity]
            expanded_records = expanded_by_rarity[rarity]
            selected_indices = (
                tuple(range(len(records)))
                if exact
                else _stratified_indices(len(records), _MAX_RECORDS_PER_RARITY)
            )
            selected_set = set(selected_indices)
            rarity_total = 0.0

            # The denominator remains the full public rarity pool.  Unselected
            # records contribute literal zero; they are never renormalized away.
            for record_index, (record, branches) in enumerate(zip(records, expanded_records)):
                if record_index not in selected_set:
                    continue

                record_total = 0.0
                for branch_record in branches:
                    branch_value = 0.0
                    base = self.joker_factory.create(dict(branch_record))
                    if base is None:  # defensive: preflight above already proved this
                        return self._incomplete(
                            f"eligible {rarity} future Joker became unmodeled: {record.get('label') or record.get('center')}",
                            total_records,
                        )
                    for edition, probability in editions:
                        if d2_evaluations >= _MAX_D2_EVALUATIONS and not exact:
                            budget_exhausted = True
                            break
                        candidate = copy.deepcopy(base)
                        candidate.edition = edition
                        candidate.price = int(expected_price)
                        candidate.cost = int(expected_price)
                        try:
                            decision = self.joker_policy.decide(projected, candidate)
                        except (AttributeError, KeyError, RuntimeError, TypeError, ValueError, ZeroDivisionError) as exc:
                            return self._incomplete(
                                f"future Joker D2 valuation failed for {record.get('label') or record.get('center')}: {type(exc).__name__}: {exc}",
                                total_records,
                            )
                        d2_evaluations += 1

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
                        branch_value += float(probability) * gain
                    record_total += branch_value
                    if budget_exhausted:
                        break

                rarity_total += record_total / float(len(branches))
                evaluated_records += 1
                if budget_exhausted:
                    break

            rarity_means[rarity] = rarity_total / float(len(records))
            if budget_exhausted:
                # Every remaining rarity/record has zero contribution by definition
                # of the conservative bounded lower bound.
                for remaining in RARITY_WEIGHTS:
                    rarity_means.setdefault(remaining, 0.0)
                break

        expected = sum(
            float(RARITY_WEIGHTS[rarity]) * rarity_means.get(rarity, 0.0)
            for rarity in RARITY_WEIGHTS
        )
        bounded = not exact or budget_exhausted
        return RerollJokerExpectation(
            complete=True,
            expected_gain=expected,
            outcome_count=total_records,
            rationale=(
                "future Joker uses the authoritative public eligible rarity pools and full D2/D14 for every evaluated branch",
                "rarity mixture Common=0.70 Uncommon=0.25 Rare=0.05",
                f"eligible public outcomes={total_records}",
                f"D2-evaluated records={evaluated_records}; D2 calls={d2_evaluations}",
                (
                    "large-pool bounded lower bound active: unevaluated public probability mass contributes zero and is not renormalized"
                    if bounded
                    else "small public pool integrated exactly"
                ),
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
