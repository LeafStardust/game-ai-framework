from __future__ import annotations

"""Prevent an actively Banned strategy from becoming the controlling route.

Banned is categorical mechanical incompatibility, not merely a large negative
preference.  The numeric -12 penalty remains useful for ranking/diagnostics, but a
strategy with an actually owned Banned component may not become dominant until the
conflict is removed.  This avoids Ante-6 forced commitment resurrecting a conflicted
route after enough positive evidence numerically outweighs the penalty.
"""

from dataclasses import replace

from games.balatro.strategy import (
    AVAILABLE,
    COMMITTED,
    MATURE,
    BalatroStrategyTracker,
)


def install_strategy_banned_conflict_policy() -> None:
    if getattr(BalatroStrategyTracker, "_banned_conflict_policy_installed", False):
        return

    original_observe = BalatroStrategyTracker.observe

    def observe(self, state):
        resolution = original_observe(self, state)
        if resolution.dominant_strategy_id is None:
            return resolution

        by_id = {item.strategy_id: item for item in resolution.assessments}
        current = by_id.get(resolution.dominant_strategy_id)
        if current is None or int(current.banned_owned) <= 0:
            return resolution

        clean = next(
            (
                item
                for item in resolution.assessments
                if float(item.score) > 0.0 and int(item.banned_owned) == 0
            ),
            None,
        )
        if clean is None:
            self._last_dominant_strategy_id = None
            self._last_relevant_strategy_ids = ()
            return replace(
                resolution,
                dominant_strategy_id=None,
                relevant_strategy_ids=(),
                active_strategy_id=None,
                highlighted_strategy_id=None,
                committed_strategy_id=None,
                active_status=AVAILABLE,
                changed=True,
                rationale=(
                    *resolution.rationale,
                    f"conflicted strategy {current.name} cannot control while banned_owned={current.banned_owned}",
                    "no positive conflict-free strategy remains; ordinary/meta value leads",
                ),
            )

        config = self._config(state)
        max_relevant = max(0, int(self._number(config, "max_relevant_strategies", 2.0)))
        relevant_floor = self._number(config, "relevant_strategy_floor", 1.0)
        relevant_ratio = self._number(config, "relevant_strategy_ratio", 0.35)
        floor = max(relevant_floor, float(clean.score) * relevant_ratio)
        relevant = tuple(
            item
            for item in resolution.assessments
            if (
                item.strategy_id != clean.strategy_id
                and float(item.score) > 0.0
                and int(item.banned_owned) == 0
                and float(item.score) >= floor
            )
        )[:max_relevant]
        relevant_ids = tuple(item.strategy_id for item in relevant)

        ante = max(1, int(getattr(state, "ante", 1) or 1))
        if ante >= 6:
            active_status = MATURE if clean.status == MATURE else COMMITTED
            committed_id = clean.strategy_id
        else:
            active_status = clean.status
            committed_id = None

        self._last_dominant_strategy_id = clean.strategy_id
        self._last_relevant_strategy_ids = relevant_ids
        return replace(
            resolution,
            dominant_strategy_id=clean.strategy_id,
            relevant_strategy_ids=relevant_ids,
            active_strategy_id=clean.strategy_id,
            highlighted_strategy_id=clean.strategy_id,
            committed_strategy_id=committed_id,
            active_status=active_status,
            changed=True,
            rationale=(
                *resolution.rationale,
                f"conflicted strategy {current.name} excluded while banned_owned={current.banned_owned}",
                f"highest conflict-free strategy={clean.name} score={clean.score:.3f}",
            ),
        )

    BalatroStrategyTracker.observe = observe
    BalatroStrategyTracker._banned_conflict_policy_installed = True
