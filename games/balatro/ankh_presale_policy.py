from __future__ import annotations

"""Multi-checkpoint Ankh preparation for committed builds.

Ankh already has an analytic whole-board expectation model. This policy adds the
missing action sequence: when an open Spectral pack contains Ankh, the agent may
sell expendable non-Eternal off-path Jokers first if doing so improves the exact
public-state Ankh expectation. Protected Gold/Silver components of a committed
strategy are never sacrificed by this preparation step.
"""

from copy import deepcopy
from dataclasses import dataclass
from itertools import combinations

from games.balatro.actions import SELL_JOKER, BalatroAction
from games.balatro.build.ankh_expectation import AnkhExpectationEvaluator
from games.balatro.pack_policy import PackActionScore
from games.balatro.playbook_pack_policy import PlaybookBalatroPackPolicy
from games.balatro.strategy import COMMITTED, GOLD, MATURE, SILVER


@dataclass(frozen=True)
class AnkhPresalePlan:
    sell_indices: tuple[int, ...]
    current_expected_gain: float
    prepared_expected_gain: float

    @property
    def improvement(self) -> float:
        return float(self.prepared_expected_gain) - float(self.current_expected_gain)


def _primary_id(tracker, resolution):
    primary = resolution.dominant_strategy_id
    getter = getattr(tracker, "primary_strategy_id", None)
    if callable(getter):
        primary = getter(resolution)
    return primary


def _tracker_from_policy(policy):
    evaluator = getattr(getattr(policy, "item_estimator", None), "joker_build_value", None)
    return getattr(evaluator, "strategy_tracker", None)


def _protected_indices(policy, state) -> frozenset[int]:
    tracker = _tracker_from_policy(policy)
    if tracker is None:
        return frozenset()
    resolution = tracker.observe(state)
    if resolution.active_status not in {COMMITTED, MATURE}:
        return frozenset()
    primary = _primary_id(tracker, resolution)
    if primary is None:
        return frozenset()

    protected = set()
    for index, joker in enumerate(getattr(state, "jokers", ()) or ()):
        relation = tracker.evaluate_item(state, joker, kind="JOKER")
        if (
            relation.active_alignment
            and relation.strategy_id == primary
            and relation.tier in {GOLD, SILVER}
        ):
            protected.add(index)
    return frozenset(protected)


def _evaluate_after_sales(evaluator: AnkhExpectationEvaluator, state, indices: tuple[int, ...]):
    branch = deepcopy(state)
    removed = set(indices)
    branch.jokers = [
        joker
        for index, joker in enumerate(getattr(branch, "jokers", ()) or ())
        if index not in removed
    ]
    return evaluator.evaluate(branch)


def best_ankh_presale_plan(policy, state) -> AnkhPresalePlan | None:
    jokers = tuple(getattr(state, "jokers", ()) or ())
    if len(jokers) <= 1:
        return None

    evaluator = getattr(policy, "ankh_evaluator", None) or AnkhExpectationEvaluator()
    current = evaluator.evaluate(state)
    if not current.available or not current.complete:
        return None

    protected = _protected_indices(policy, state)
    expendable = tuple(
        index
        for index, joker in enumerate(jokers)
        if index not in protected and not bool(getattr(joker, "eternal", False))
    )
    if not expendable:
        return None

    best: AnkhPresalePlan | None = None
    # At most five ordinary Joker slots are expected on this competence line, so
    # exhaustive public subsets are bounded. Never sell every Joker: Ankh requires
    # at least one target after preparation.
    for count in range(1, len(expendable) + 1):
        for indices in combinations(expendable, count):
            if len(jokers) - len(indices) < 1:
                continue
            expectation = _evaluate_after_sales(evaluator, state, tuple(indices))
            if not expectation.available or not expectation.complete:
                continue
            plan = AnkhPresalePlan(
                sell_indices=tuple(indices),
                current_expected_gain=float(current.expected_build_gain),
                prepared_expected_gain=float(expectation.expected_build_gain),
            )
            if plan.improvement <= 1e-9:
                continue
            if best is None or (
                plan.prepared_expected_gain,
                -len(plan.sell_indices),
                plan.improvement,
            ) > (
                best.prepared_expected_gain,
                -len(best.sell_indices),
                best.improvement,
            ):
                best = plan
    return best


def install_ankh_presale_policy() -> None:
    if getattr(PlaybookBalatroPackPolicy, "_ankh_presale_policy_installed", False):
        return

    original_score_action = PlaybookBalatroPackPolicy.score_action

    def score_action(self, state, action):
        choice = getattr(action, "target", None)
        if (
            str(getattr(state, "phase", "") or "") == "SPECTRAL_PACK"
            and str(getattr(choice, "kind", "") or "").upper() == "SPECTRAL"
            and str(getattr(choice, "label", "") or "") == "Ankh"
        ):
            plan = best_ankh_presale_plan(self, state)
            if plan is not None and plan.sell_indices:
                # Sell one planned expendable Joker, then re-observe the still-open
                # pack. The next checkpoint recomputes the optimal remaining subset
                # rather than assuming the previous hypothetical state became real.
                index = int(plan.sell_indices[0])
                return PackActionScore(
                    BalatroAction(SELL_JOKER, target=index),
                    float(plan.prepared_expected_gain),
                    (
                        "Ankh multi-action plan: pre-sell expendable off-path Joker before consuming the Spectral",
                        f"sell incumbent slot {index}; re-observe the same Spectral pack afterwards",
                        f"current analytic Ankh build gain={plan.current_expected_gain:+.3f}",
                        f"prepared analytic Ankh build gain={plan.prepared_expected_gain:+.3f}",
                        f"analytic improvement={plan.improvement:+.3f}",
                        "committed Gold/Silver components and Eternal Jokers are protected from Ankh preparation sales",
                    ),
                )
        return original_score_action(self, state, action)

    PlaybookBalatroPackPolicy.score_action = score_action
    PlaybookBalatroPackPolicy._ankh_presale_policy_installed = True
