from __future__ import annotations

"""Public-state expectation for Judgement.

Judgement creates one random non-Legendary Joker. Balatro first rolls rarity
(70% Common, 25% Uncommon, 5% Rare), then chooses uniformly from the current
eligible pool for that rarity. The live pool adapter supplies that canonical public
catalogue after duplicate/unlock/ban/pool-gate filtering; no RNG seed or pool order
is exposed.

The eligible catalogue can be large and JokerBuildValueEvaluator is intentionally
expensive. Evaluating every eligible Joker across every edition branch made a single
Judgement option capable of blocking the live SHOP authority for tens of seconds.
This evaluator therefore uses a deterministic spread through each public rarity
pool. Evaluated outcomes retain the *full* eligible-pool denominator, so omitted
probability mass contributes literal zero instead of being renormalized. The result
is a conservative bounded lower bound rather than a sampled estimate.

Newly created To Do List is the one modeled eligible Joker whose initial tactical
state is freshly randomized at creation. Its public visible-hand sub-distribution is
bounded in the same way: evaluated branches retain the full hand-count denominator,
so omitted branches again contribute zero.
"""

import copy
from dataclasses import dataclass

from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.build.wraith_expectation import _edition_probabilities
from games.balatro.joker_edition import joker_edition_universal_value
from games.balatro.live.joker_factory import LiveJokerFactory


RARITY_WEIGHTS = {
    "COMMON": 0.70,
    "UNCOMMON": 0.25,
    "RARE": 0.05,
}

# SHOP/D8 must stay responsive even when the public eligible Joker catalogue is
# large. Six evenly spread records per rarity keeps the expensive whole-build
# evaluator bounded while preserving a conservative full-pool denominator.
_MAX_EVALUATED_RECORDS_PER_RARITY = 6
_MAX_EVALUATED_INITIAL_BRANCHES = 4


def _bounded_indices(count: int, limit: int) -> tuple[int, ...]:
    if count <= 0 or limit <= 0:
        return ()
    if count <= limit:
        return tuple(range(count))
    if limit == 1:
        return (0,)

    selected = {
        round(position * (count - 1) / float(limit - 1))
        for position in range(limit)
    }
    if len(selected) < limit:
        selected.update(index for index in range(count) if index not in selected)
    return tuple(sorted(selected)[:limit])


@dataclass(frozen=True)
class JudgementJokerOutcome:
    rarity: str
    center: str
    label: str
    expected_gain: float


@dataclass(frozen=True)
class JudgementExpectation:
    available: bool
    complete: bool
    outcome_count: int
    expected_total_gain: float
    outcomes: tuple[JudgementJokerOutcome, ...] = ()
    rationale: tuple[str, ...] = ()


class JudgementExpectationEvaluator:
    def __init__(
        self,
        *,
        joker_factory: LiveJokerFactory | None = None,
        joker_value: JokerBuildValueEvaluator | None = None,
    ) -> None:
        self.joker_factory = joker_factory or LiveJokerFactory()
        self.joker_value = joker_value or JokerBuildValueEvaluator()

    def evaluate(self, state) -> JudgementExpectation:
        joker_slots = max(0, int(getattr(state, "joker_slots", 0) or 0))
        if len(tuple(getattr(state, "jokers", ()) or ())) >= joker_slots:
            return JudgementExpectation(
                available=False,
                complete=True,
                outcome_count=0,
                expected_total_gain=0.0,
                rationale=("Judgement requires a free Joker slot",),
            )

        if str(getattr(state, "stake_name", "WHITE") or "WHITE").upper() != "WHITE":
            return JudgementExpectation(
                available=True,
                complete=False,
                outcome_count=0,
                expected_total_gain=0.0,
                rationale=(
                    "Judgement expectation is currently scoped to White Stake; "
                    "higher-stake generated Joker stickers are not modeled here",
                ),
            )

        if not bool(getattr(state, "joker_generation_pool_observed", False)):
            return JudgementExpectation(
                available=True,
                complete=False,
                outcome_count=0,
                expected_total_gain=0.0,
                rationale=("authoritative public Joker generation pool was not observed",),
            )

        pools = dict(getattr(state, "joker_generation_pools", {}) or {})
        visible_hands = tuple(getattr(state, "visible_poker_hands", ()) or ())
        edition_rate = float(getattr(state, "joker_generation_edition_rate", 1.0) or 1.0)
        editions = _edition_probabilities(edition_rate)

        all_outcomes: list[JudgementJokerOutcome] = []
        rarity_means: dict[str, float] = {}
        bounded_notes: list[str] = []

        for rarity in RARITY_WEIGHTS:
            records = list(pools.get(rarity, ()) or ())
            if not records:
                # Balatro's pool helper falls back to the base Joker if an eligible
                # requested rarity pool is empty.
                records = [
                    {
                        "center": "j_joker",
                        "label": "Joker",
                        "ability_name": "Joker",
                        "ability_set": "JOKER",
                        "rarity": "COMMON",
                    }
                ]

            total_record_count = len(records)
            record_indices = _bounded_indices(
                total_record_count,
                _MAX_EVALUATED_RECORDS_PER_RARITY,
            )
            rarity_value_sum = 0.0

            for record_index in record_indices:
                record = records[record_index]
                expanded = self._initial_state_records(record, visible_hands)
                if expanded is None:
                    return self._incomplete(
                        all_outcomes,
                        f"generated initial state is unresolved for {record.get('label') or record.get('center')}",
                    )

                total_branch_count = len(expanded)
                branch_indices = _bounded_indices(
                    total_branch_count,
                    _MAX_EVALUATED_INITIAL_BRANCHES,
                )
                branch_value_sum = 0.0

                for branch_index in branch_indices:
                    branch_record = expanded[branch_index]
                    base = self.joker_factory.create(branch_record)
                    if base is None:
                        return self._incomplete(
                            all_outcomes,
                            f"eligible {rarity} Joker is not modeled: "
                            f"{record.get('label') or record.get('center')}",
                        )
                    try:
                        edition_value = 0.0
                        for edition, probability in editions:
                            candidate = copy.deepcopy(base)
                            candidate.edition = edition
                            value = self.joker_value.evaluate(state, candidate).total_gain
                            value += joker_edition_universal_value(candidate)
                            edition_value += probability * float(value)
                    except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
                        return self._incomplete(
                            all_outcomes,
                            f"Joker valuation failed for {record.get('label') or record.get('center')}: "
                            f"{type(exc).__name__}: {exc}",
                        )
                    branch_value_sum += edition_value

                # Full branch denominator is deliberate: unevaluated branches are
                # assigned zero so this remains a lower bound.
                record_value = branch_value_sum / float(total_branch_count)
                rarity_value_sum += record_value
                all_outcomes.append(
                    JudgementJokerOutcome(
                        rarity=rarity,
                        center=str(record.get("center") or ""),
                        label=str(record.get("label") or record.get("center") or ""),
                        expected_gain=record_value,
                    )
                )

            # Full rarity-pool denominator is deliberate: unevaluated eligible
            # Jokers contribute zero rather than inflating the sampled subset.
            rarity_means[rarity] = rarity_value_sum / float(total_record_count)
            bounded_notes.append(
                f"{rarity} visible outcomes evaluated={len(record_indices)}/{total_record_count}; "
                "omitted probability mass remains zero"
            )

        total = sum(
            RARITY_WEIGHTS[rarity] * rarity_means[rarity]
            for rarity in RARITY_WEIGHTS
        )
        return JudgementExpectation(
            available=True,
            complete=True,
            outcome_count=len(all_outcomes),
            expected_total_gain=total,
            outcomes=tuple(all_outcomes),
            rationale=(
                "Balatro rarity weights: Common=0.70 Uncommon=0.25 Rare=0.05",
                f"public edition_rate={edition_rate:.3f}",
                *bounded_notes,
                *(
                    f"{rarity} bounded lower-bound mean={rarity_means[rarity]:.3f}"
                    for rarity in RARITY_WEIGHTS
                ),
                f"expected Judgement Joker gain lower bound={total:.3f}",
                "To Do List initial target uses a bounded deterministic spread over public visible poker hands",
                "all omitted catalogue/initial-state probability mass contributes literal zero",
                "no RNG sample, pseudoseed, pool order, or selected outcome read",
            ),
        )

    @staticmethod
    def _initial_state_records(record: dict, visible_hands: tuple[str, ...]):
        if str(record.get("center") or "") != "j_todo_list":
            return (dict(record),)
        if not visible_hands:
            return None

        branches: list[dict] = []
        for hand in visible_hands:
            branch = dict(record)
            public_state = dict(branch.get("public_state") or {})
            public_state["target_hand"] = hand
            branch["public_state"] = public_state
            branches.append(branch)
        return tuple(branches)

    @staticmethod
    def _incomplete(outcomes: list[JudgementJokerOutcome], reason: str) -> JudgementExpectation:
        return JudgementExpectation(
            available=True,
            complete=False,
            outcome_count=len(outcomes),
            expected_total_gain=0.0,
            outcomes=tuple(outcomes),
            rationale=(
                reason,
                "Judgement expectation fails closed; eligible outcomes are never silently discarded",
            ),
        )
