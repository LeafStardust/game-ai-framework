from __future__ import annotations

"""Post-commit strategy hysteresis derived from live Red/White run review.

The universal tracker intentionally remains current-state based. This policy adds a
stateless late-game admission rule rather than remembering a mutable previous route,
because shop/build evaluation frequently observes hypothetical copied states.

From Ante 6 onward:
* a clear score leader keeps control;
* a lead smaller than the pivot margin is treated as ambiguous;
* only strictly stronger Gold/core evidence may overturn that near-tied raw leader.

This prevents small deck-shape or support-score changes from repeatedly flipping the
primary route while still allowing a genuinely stronger build to pivot immediately.
"""

from dataclasses import replace

from games.balatro.strategy import (
    AVAILABLE,
    CANDIDATE,
    COMMITTED,
    HIGHLIGHTED,
    MATURE,
    BalatroStrategyTracker,
    StrategyAssessment,
)

DEFAULT_POST_COMMIT_PIVOT_MARGIN = 3.0


def _positive_owned(assessment: StrategyAssessment) -> int:
    return (
        int(assessment.gold_owned)
        + int(assessment.silver_owned)
        + int(assessment.bronze_owned)
    )


def _status_strength(status: str) -> int:
    return {
        AVAILABLE: 0,
        CANDIDATE: 1,
        HIGHLIGHTED: 2,
        COMMITTED: 3,
        MATURE: 4,
    }.get(str(status), 0)


def choose_post_commit_dominant(
    assessments: tuple[StrategyAssessment, ...],
    *,
    ante: int,
    pivot_margin: float = DEFAULT_POST_COMMIT_PIVOT_MARGIN,
) -> StrategyAssessment | None:
    """Choose a stable late-game leader without hidden/history-dependent state.

    Before Ante 6, raw score ordering remains authoritative. From Ante 6 onward a
    challenger with a lead >= ``pivot_margin`` is also authoritative. Inside that
    margin, the raw score leader remains authoritative unless another near-tied
    route owns strictly more Gold/core evidence. Silver/Bronze support count alone
    may never overthrow the raw leader: inherited/generic support is exactly the
    transient evidence that caused Pair/Two-Pair and other late-route oscillation.
    """

    positive = tuple(a for a in assessments if float(a.score) > 0.0)
    if not positive:
        return None

    leader = positive[0]
    if int(ante) < 6 or len(positive) == 1:
        return leader

    runner_up = positive[1]
    margin = max(0.0, float(pivot_margin))
    if float(leader.score) - float(runner_up.score) >= margin:
        return leader

    near_tied = tuple(
        assessment
        for assessment in positive
        if float(leader.score) - float(assessment.score) < margin
    )
    strongest_gold = max(int(a.gold_owned) for a in near_tied)
    if strongest_gold <= int(leader.gold_owned):
        return leader

    gold_challengers = tuple(
        a for a in near_tied if int(a.gold_owned) == strongest_gold
    )
    return max(
        gold_challengers,
        key=lambda assessment: (
            float(assessment.score),
            _positive_owned(assessment),
            _status_strength(assessment.status),
            -int(assessment.banned_owned),
            assessment.strategy_id,
        ),
    )


def install_strategy_commitment_hysteresis() -> None:
    if getattr(BalatroStrategyTracker, "_commitment_hysteresis_installed", False):
        return

    original_observe = BalatroStrategyTracker.observe

    def observe(self, state):
        resolution = original_observe(self, state)
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        if ante < 6 or not resolution.assessments:
            return resolution

        config = self._config(state)
        pivot_margin = self._number(
            config,
            "post_commit_pivot_margin",
            DEFAULT_POST_COMMIT_PIVOT_MARGIN,
        )
        selected = choose_post_commit_dominant(
            resolution.assessments,
            ante=ante,
            pivot_margin=pivot_margin,
        )
        if selected is None or selected.strategy_id == resolution.dominant_strategy_id:
            return resolution

        max_relevant = max(
            0,
            int(self._number(config, "max_relevant_strategies", 2.0)),
        )
        relevant_floor = self._number(config, "relevant_strategy_floor", 1.0)
        relevant_ratio = self._number(config, "relevant_strategy_ratio", 0.35)
        positive = [a for a in resolution.assessments if float(a.score) > 0.0]
        floor = max(relevant_floor, float(selected.score) * relevant_ratio)
        relevant = [
            a
            for a in positive
            if a.strategy_id != selected.strategy_id and float(a.score) >= floor
        ][:max_relevant]
        relevant_ids = tuple(a.strategy_id for a in relevant)

        active_status = MATURE if selected.status == MATURE else COMMITTED
        previous_name = resolution.dominant_strategy_id or "none"
        rationale = (
            *resolution.rationale,
            "post-commit hysteresis retained stronger Gold/core route="
            f"{selected.name} score={selected.score:.3f}; raw leader={previous_name}; "
            f"pivot margin={pivot_margin:.3f}; gold={selected.gold_owned}; "
            f"positive_jokers={_positive_owned(selected)}",
        )

        self._last_dominant_strategy_id = selected.strategy_id
        self._last_relevant_strategy_ids = relevant_ids
        return replace(
            resolution,
            dominant_strategy_id=selected.strategy_id,
            relevant_strategy_ids=relevant_ids,
            active_strategy_id=selected.strategy_id,
            highlighted_strategy_id=selected.strategy_id,
            committed_strategy_id=selected.strategy_id,
            active_status=active_status,
            changed=True,
            rationale=rationale,
        )

    BalatroStrategyTracker.observe = observe
    BalatroStrategyTracker._commitment_hysteresis_installed = True
