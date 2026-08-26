from __future__ import annotations

"""Public-state expectation for Judgement.

Judgement creates one random non-Legendary Joker. Balatro first rolls rarity
(70% Common, 25% Uncommon, 5% Rare), then chooses uniformly from the current
eligible pool for that rarity. The live pool adapter supplies that canonical public
catalogue after duplicate/unlock/ban/pool-gate filtering; no RNG seed or pool order
is exposed.

Newly created To Do List is the one modeled eligible Joker whose initial tactical
state is freshly randomized at creation. Balatro chooses uniformly from the public
set of visible poker hands, so this evaluator expands that finite sub-distribution
instead of constructing the model with ``target_hand=None``.
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

        for rarity, rarity_weight in RARITY_WEIGHTS.items():
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

            rarity_values: list[float] = []
            for record in records:
                expanded = self._initial_state_records(record, visible_hands)
                if expanded is None:
                    return self._incomplete(
                        all_outcomes,
                        f"generated initial state is unresolved for {record.get('label') or record.get('center')}",
                    )

                initial_values: list[float] = []
                for branch_record in expanded:
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
                    initial_values.append(edition_value)

                record_value = sum(initial_values) / len(initial_values)
                rarity_values.append(record_value)
                all_outcomes.append(
                    JudgementJokerOutcome(
                        rarity=rarity,
                        center=str(record.get("center") or ""),
                        label=str(record.get("label") or record.get("center") or ""),
                        expected_gain=record_value,
                    )
                )

            rarity_means[rarity] = sum(rarity_values) / len(rarity_values)

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
                *(
                    f"{rarity} eligible outcomes={sum(o.rarity == rarity for o in all_outcomes)} "
                    f"mean={rarity_means[rarity]:.3f}"
                    for rarity in RARITY_WEIGHTS
                ),
                f"expected Judgement Joker gain={total:.3f}",
                "To Do List initial target is averaged over public visible poker hands",
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
                "Judgement expectation fails closed; eligible outcomes are never dropped",
            ),
        )
