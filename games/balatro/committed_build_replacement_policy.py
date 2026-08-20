from __future__ import annotations

"""Committed-build Joker replacement contract.

Once a strategy is committed/mature, its aligned Gold/Silver components are
structural build pieces rather than ordinary flat-value incumbents. They may be
replaced by an immediately stronger component of the same committed route, but a
generic/off-path candidate may not dismantle the build merely because its local
Joker value is higher.
"""

from dataclasses import replace

from games.balatro.strategy import BRONZE, COMMITTED, GOLD, MATURE, SILVER
from games.balatro.strategy_value import StrategyAwareJokerBuildTransitionPlanner


_TIER_RANK = {BRONZE: 1, SILVER: 2, GOLD: 3}


def _primary_id(tracker, resolution):
    primary = resolution.dominant_strategy_id
    getter = getattr(tracker, "primary_strategy_id", None)
    if callable(getter):
        primary = getter(resolution)
    return primary


def _same_route_immediate_upgrade(primary_id, incumbent, candidate, option) -> bool:
    if primary_id is None:
        return False
    if not incumbent.active_alignment or not candidate.active_alignment:
        return False
    if incumbent.strategy_id != primary_id or candidate.strategy_id != primary_id:
        return False
    if incumbent.tier not in _TIER_RANK or candidate.tier not in _TIER_RANK:
        return False
    if _TIER_RANK[candidate.tier] < _TIER_RANK[incumbent.tier]:
        return False
    # build_delta is measured on the same current-build baseline. Requiring it to
    # already be positive prevents a nominally higher-tier scaler from displacing
    # a working component merely for future theoretical buildup.
    return float(option.build_delta) > 0.0


def install_committed_build_replacement_policy() -> None:
    if getattr(
        StrategyAwareJokerBuildTransitionPlanner,
        "_committed_build_replacement_policy_installed",
        False,
    ):
        return

    original_plan = StrategyAwareJokerBuildTransitionPlanner.plan

    def plan(self, state, candidate):
        transition = original_plan(self, state, candidate)
        if not transition.alternatives:
            return transition

        tracker = self.evaluator.strategy_tracker
        resolution = tracker.observe(state)
        if resolution.active_status not in {COMMITTED, MATURE}:
            return transition

        primary_id = _primary_id(tracker, resolution)
        candidate_relation = tracker.evaluate_item(state, candidate, kind="JOKER")
        rewritten = []

        for option in transition.alternatives:
            index = int(option.replace_index)
            incumbent = state.jokers[index]
            incumbent_relation = tracker.evaluate_item(state, incumbent, kind="JOKER")
            protected = (
                incumbent_relation.active_alignment
                and incumbent_relation.strategy_id == primary_id
                and incumbent_relation.tier in {GOLD, SILVER}
            )
            same_route_upgrade = _same_route_immediate_upgrade(
                primary_id,
                incumbent_relation,
                candidate_relation,
                option,
            )

            eligible = bool(option.eligible)
            blocked_reason = option.blocked_reason
            rationale = list(option.rationale)

            if protected and not same_route_upgrade:
                eligible = False
                blocked_reason = blocked_reason or (
                    "committed Gold/Silver strategy component is protected; only an "
                    "immediately stronger same-route replacement may displace it"
                )
                rationale.extend(
                    (
                        f"committed build protection: primary={primary_id}",
                        f"incumbent aligned tier={incumbent_relation.tier}",
                        "candidate is not an approved immediate same-route upgrade",
                    )
                )
            elif protected and same_route_upgrade:
                rationale.extend(
                    (
                        "committed build same-route upgrade allowed",
                        f"{incumbent_relation.tier}->{candidate_relation.tier}; current whole-build delta={float(option.build_delta):+.3f}",
                    )
                )

            rewritten.append(
                replace(
                    option,
                    eligible=eligible,
                    blocked_reason=blocked_reason,
                    rationale=tuple(rationale),
                )
            )

        alternatives = tuple(
            sorted(rewritten, key=lambda option: (-option.build_delta, option.replace_index))
        )
        eligible = tuple(option for option in alternatives if option.eligible)
        replacement = (
            eligible[0]
            if eligible and eligible[0].build_delta > self.minimum_replacement_delta
            else None
        )
        action = "REPLACE" if replacement is not None else "HOLD"
        notes = list(transition.rationale)
        notes.append(
            "committed-build replacement hierarchy applied: aligned Gold/Silver pieces are structural, not flat-value fodder"
        )
        if replacement is None and any(not option.eligible for option in alternatives):
            notes.append("no legal committed-build replacement cleared the current whole-build threshold")

        return replace(
            transition,
            action=action,
            replacement=replacement,
            alternatives=alternatives,
            rationale=tuple(notes),
        )

    StrategyAwareJokerBuildTransitionPlanner.plan = plan
    StrategyAwareJokerBuildTransitionPlanner._committed_build_replacement_policy_installed = True
