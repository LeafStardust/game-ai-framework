from __future__ import annotations

"""Decision-integrity fixes exposed by the 2026-08-20 five-run batch."""

from dataclasses import replace

from games.balatro.actions import SELL_JOKER, BalatroAction
from games.balatro.build import JokerBuildTransitionPlanner
from games.balatro.joker_policy import BUY, HOLD, REPLACE
from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy
from games.balatro.playbook.red_white.pack_policy import PlaybookBalatroPackPolicy
from games.balatro.pack_policy import PackActionScore
from games.balatro.strategy import COMMITTED, GOLD, HIGHLIGHTED, MATURE, SILVER
from games.balatro.strategy_tree_tracker import TreeAwareStateAwareBalatroStrategyTracker
from games.balatro.strategy_value import StrategyAwareJokerBuildTransitionPlanner


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _primary_id(tracker, resolution):
    primary = resolution.dominant_strategy_id
    getter = getattr(tracker, "primary_strategy_id", None)
    if callable(getter):
        primary = getter(resolution)
    return primary


def _tracker_from_policy(policy):
    planner = getattr(policy, "transition_planner", None)
    evaluator = getattr(planner, "evaluator", None)
    return getattr(evaluator, "strategy_tracker", None)


def _early_survival_buy(policy, state, candidate, decision):
    """Admit immediate scoring in Antes 1-2 when strategy purity would reject it.

    The ordinary D2 economics remain authoritative. The only thing relaxed is an
    early off-strategy adjustment: survival comes before route purity while the run
    is still in its foundation phase. The candidate must have a free slot, produce
    positive immediate scoring on the shared build evaluator, and leave at least the
    configured reserve after purchase.
    """

    if decision.action != HOLD or not getattr(decision, "options", None):
        return decision
    ante = max(1, int(getattr(state, "ante", 1) or 1))
    if ante > 2:
        return decision
    if len(getattr(state, "jokers", ()) or ()) >= int(getattr(state, "joker_slots", 0) or 0):
        return decision

    transition = policy.transition_planner.plan(state, candidate)
    value = transition.candidate_value
    direct_value = float(getattr(value, "direct_scoring_value", 0.0) or 0.0)
    if direct_value <= 0.0:
        return decision

    option = decision.options[0]
    if not option.eligible:
        return decision
    reserve_target = int(getattr(decision.thresholds, "reserve_target", 5) or 0)
    if int(option.economics.money_after) < reserve_target:
        return decision

    # Strategy-adjusted values may suppress an otherwise useful immediate scorer.
    # During Antes 1-2, compare the same transaction after removing only that
    # strategy-purity penalty. Price, interest, reserve, and slot costs remain.
    total_gain = float(getattr(value, "total_gain", 0.0) or 0.0)
    base_gain = float(getattr(value, "base_total_gain", total_gain) or 0.0)
    relaxed_advantage = float(option.total_advantage) + max(0.0, base_gain - total_gain)
    threshold = float(decision.thresholds.minimum_purchase_advantage)
    if relaxed_advantage <= threshold:
        return decision

    selected = replace(
        option,
        total_advantage=relaxed_advantage,
        rationale=(
            *option.rationale,
            "Ante 1-2 survival override: immediate scoring is allowed to ignore off-strategy purity pressure",
            "price/interest/reserve/slot economics remain authoritative",
            f"immediate scoring value={direct_value:.3f}",
            f"survival-adjusted buy advantage={relaxed_advantage:.3f}",
        ),
    )
    return replace(
        decision,
        action=BUY,
        selected=selected,
        rationale=(
            *decision.rationale,
            "Ante 1-2 survival takes precedence over strategy purity",
            f"purchase leaves ${int(option.economics.money_after)} >= reserve ${reserve_target}",
        ),
    )


def _madness_threatens_tracker(tracker, state, candidate) -> bool:
    if _normalize(getattr(candidate, "name", type(candidate).__name__)) not in {
        "madness",
        "madnessjoker",
    }:
        return False
    if tracker is None:
        return False
    resolution = tracker.observe(state)
    if resolution.active_status not in {HIGHLIGHTED, COMMITTED, MATURE}:
        return False
    primary = _primary_id(tracker, resolution)
    if primary is None:
        return False
    if resolution.active_status == HIGHLIGHTED:
        assessment = resolution.assessment(primary)
        if assessment is None or float(assessment.score) < 6.0:
            return False

    for joker in getattr(state, "jokers", ()) or ():
        if bool(getattr(joker, "eternal", False)):
            continue
        relation = tracker.evaluate_item(state, joker, kind="JOKER")
        if (
            relation.active_alignment
            and relation.strategy_id == primary
            and relation.tier in {GOLD, SILVER}
        ):
            return True
    return False


def _madness_threatens_established_build(policy, state, candidate) -> bool:
    return _madness_threatens_tracker(_tracker_from_policy(policy), state, candidate)


def _definition_is_retired(definition) -> bool:
    required = getattr(definition, "required_jokers", ()) or ()
    for token in required:
        normalized = _normalize(token)
        if normalized.startswith("retired") or normalized.startswith("mergedinto"):
            return True
    return False


def install_five_run_decision_integrity_policy() -> None:
    if not getattr(
        PlaybookJokerAcquisitionPolicy,
        "_madness_build_protection_installed",
        False,
    ):
        original_decide = PlaybookJokerAcquisitionPolicy.decide

        def decide(self, state, candidate):
            decision = original_decide(self, state, candidate)
            decision = _early_survival_buy(self, state, candidate, decision)
            if not _madness_threatens_established_build(self, state, candidate):
                return decision
            return replace(
                decision,
                action=HOLD,
                selected=None,
                rationale=(
                    *decision.rationale,
                    "Madness acquisition blocked: its blind-selection destruction can dismantle non-Eternal Gold/Silver components of the established build",
                ),
            )

        PlaybookJokerAcquisitionPolicy.decide = decide
        PlaybookJokerAcquisitionPolicy._madness_build_protection_installed = True

    if not getattr(
        PlaybookBalatroPackPolicy,
        "_strategy_aware_buffoon_replacement_installed",
        False,
    ):
        def _buffoon_replacement_score(self, state, action, choice):
            if str(getattr(state, "phase", "")) != "BUFFOON_PACK":
                return None
            if getattr(choice, "kind", None) != "JOKER":
                return None
            joker_slots = max(0, int(getattr(state, "joker_slots", 0) or 0))
            if len(getattr(state, "jokers", ()) or ()) < joker_slots:
                return None

            data = getattr(choice, "data", None)
            if not isinstance(data, dict):
                return PackActionScore(
                    action,
                    -1.0,
                    ("full-roster Buffoon Joker cannot be modeled for replacement",),
                )
            candidate = self._pack_joker_factory.create(data)
            evaluator = getattr(self.item_estimator, "joker_build_value", None)
            if candidate is None or evaluator is None:
                return PackActionScore(
                    action,
                    -1.0,
                    ("full-roster Buffoon Joker replacement evaluator unavailable",),
                )

            planner_cls = (
                StrategyAwareJokerBuildTransitionPlanner
                if getattr(evaluator, "strategy_tracker", None) is not None
                else JokerBuildTransitionPlanner
            )
            policy = PlaybookJokerAcquisitionPolicy(
                planner_cls(evaluator=evaluator),
            )
            decision = policy.decide(state, candidate)
            selected = decision.selected
            if decision.action != REPLACE or selected is None or selected.replace_index is None:
                return PackActionScore(
                    action,
                    -1.0,
                    (
                        "visible Buffoon Joker does not justify replacing an incumbent",
                        *decision.rationale,
                    ),
                )

            sell = BalatroAction(SELL_JOKER, target=int(selected.replace_index))
            return PackActionScore(
                sell,
                float(selected.total_advantage),
                (
                    f"visible Buffoon Joker selected for strategy-aware replacement: {decision.candidate}",
                    f"sell incumbent slot {selected.replace_index} only after pack reveal",
                    "re-observe the same Buffoon pack after the sale, then take the selected Joker",
                    *decision.rationale,
                    *selected.rationale,
                ),
            )

        PlaybookBalatroPackPolicy._buffoon_replacement_score = _buffoon_replacement_score
        PlaybookBalatroPackPolicy._strategy_aware_buffoon_replacement_installed = True

    if not getattr(
        PlaybookBalatroPackPolicy,
        "_madness_buffoon_guard_installed",
        False,
    ):
        original_score_action = PlaybookBalatroPackPolicy.score_action

        def score_action(self, state, action):
            choice = getattr(action, "target", None)
            if (
                str(getattr(state, "phase", "")) == "BUFFOON_PACK"
                and getattr(choice, "kind", None) == "JOKER"
            ):
                data = getattr(choice, "data", None)
                candidate = (
                    self._pack_joker_factory.create(data)
                    if isinstance(data, dict)
                    else None
                )
                evaluator = getattr(self.item_estimator, "joker_build_value", None)
                tracker = getattr(evaluator, "strategy_tracker", None)
                if candidate is not None and _madness_threatens_tracker(
                    tracker, state, candidate
                ):
                    return PackActionScore(
                        action,
                        -1.0,
                        (
                            "Madness Buffoon choice blocked: blind-selection destruction threatens non-Eternal Gold/Silver components of the established build",
                        ),
                    )
            return original_score_action(self, state, action)

        PlaybookBalatroPackPolicy.score_action = score_action
        PlaybookBalatroPackPolicy._madness_buffoon_guard_installed = True

    if not getattr(
        TreeAwareStateAwareBalatroStrategyTracker,
        "_retired_strategy_visibility_filter_installed",
        False,
    ):
        original_assess = TreeAwareStateAwareBalatroStrategyTracker.assess

        def assess(self, state):
            assessments = original_assess(self, state)
            return tuple(
                assessment
                for assessment in assessments
                if not _definition_is_retired(self.definitions[assessment.strategy_id])
            )

        TreeAwareStateAwareBalatroStrategyTracker.assess = assess
        TreeAwareStateAwareBalatroStrategyTracker._retired_strategy_visibility_filter_installed = True
