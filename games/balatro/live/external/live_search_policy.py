from __future__ import annotations

from games.balatro.actions import PLAY_CARDS
from games.balatro.live.adaptive_search import (
    AdaptiveBlindSearchConfig,
    AdaptiveRecommendationSummary,
    adaptive_blind_search_schedule,
    stable_discard_consensus,
)
from games.balatro.live.blind_clear_planner import PlannerSearchBudgetExceeded

from .auto_blind_runner import (
    _SearchDecision,
    _SearchResult,
    _accepts,
    _indices,
    _planner,
    _result_key,
    _summary,
)


def _pace_fallback(state, args) -> _SearchDecision | None:
    """Return a cheap one-step play when it keeps the blind on scoring pace.

    This is deliberately a fallback, not the primary planner. It is considered
    only after bounded multi-action searches fail to meet the active clear policy.
    The pace target is based on current remaining chips divided by current
    remaining hands, so it automatically tightens after an under-scoring hand and
    relaxes after an over-scoring hand.
    """

    if not bool(getattr(args, "allow_pace_fallback", True)):
        return None

    target = int(getattr(getattr(state, "blind", None), "requirement", 0))
    current_score = int(getattr(state, "score", 0))
    hands = max(1, int(getattr(state, "hands_remaining", 1)))
    remaining = max(0.0, float(target - current_score))
    base_required = remaining / hands
    min_ratio = float(getattr(args, "min_pace_ratio", 1.0))
    required = base_required * min_ratio

    config = AdaptiveBlindSearchConfig(
        horizon=1,
        samples=1,
        child_samples=1,
        play_width=6,
        discard_width=0,
        child_play_width=1,
        child_discard_width=0,
        max_nodes=min(max(16, int(getattr(args, "max_search_nodes", 128))), 128),
    )
    planner = _planner(config, args)
    try:
        plan = planner.plan(state)
    except PlannerSearchBudgetExceeded:
        return None

    result = _SearchResult(config=config, planner=planner, plan=plan)
    projection = planner.evaluator.project_play(state, plan.action)
    expected_hand_score = float(projection.expected_hand_score)
    pace_ratio = expected_hand_score / base_required if base_required > 0 else float("inf")

    print(
        "Pace fallback -> "
        f"required={base_required:.3f}/hand minimum-ratio={min_ratio:.3f} "
        f"selected-expected={expected_hand_score:.3f} ratio={pace_ratio:.3f}"
    )

    if _accepts(plan, getattr(args, "min_clear_probability", None)):
        print("Pace fallback -> immediate play also meets clear-probability policy")
        return _SearchDecision(result=result, mode="threshold")

    if plan.action.name == PLAY_CARDS and expected_hand_score >= required:
        print("Pace fallback -> PASS")
        return _SearchDecision(result=result, mode="pace-play")

    print("Pace fallback -> BLOCKED")
    return _SearchDecision(result=result, mode="none")


def search_with_pace_fallback(state, args) -> _SearchDecision:
    schedule = adaptive_blind_search_schedule(
        hands_remaining=int(state.hands_remaining),
        discards_remaining=int(state.discards_remaining),
        max_horizon=args.max_horizon,
        max_nodes=args.max_search_nodes,
    )
    best: _SearchResult | None = None
    completed: list[_SearchResult] = []
    summaries: list[AdaptiveRecommendationSummary] = []

    print(f"Adaptive search attempts -> {len(schedule)}")
    for attempt, config in enumerate(schedule, start=1):
        planner = _planner(config, args)
        unsupported = planner.evaluator.score_outcomes.joker_projector.unsupported_jokers(state)
        if unsupported:
            raise RuntimeError(
                "planner execution is blocked by unsupported Joker projection(s): "
                + ", ".join(unsupported)
            )

        try:
            plan = planner.plan(state)
        except PlannerSearchBudgetExceeded:
            print(
                f"  Search {attempt} -> horizon={config.horizon} "
                f"samples={config.samples} nodes={planner.nodes_evaluated}/"
                f"{config.max_nodes} BUDGET_EXCEEDED"
            )
            continue

        result = _SearchResult(config=config, planner=planner, plan=plan)
        completed.append(result)
        summaries.append(_summary(state, result))
        print(
            f"  Search {attempt} -> horizon={config.horizon} "
            f"samples={config.samples} nodes={planner.nodes_evaluated}/"
            f"{config.max_nodes} p={plan.value.clear_probability:.6f} "
            f"expected={plan.value.expected_score:.3f} exact={plan.exact}"
        )
        if best is None or _result_key(result) > _result_key(best):
            best = result

        if _accepts(plan, args.min_clear_probability):
            print(f"Adaptive escalation stop -> search {attempt} meets execution policy")
            return _SearchDecision(result=result, mode="threshold")

    if args.allow_consensus_discard and stable_discard_consensus(
        tuple(summaries),
        minimum_agreement=args.consensus_discard_agreement,
    ):
        result = completed[-1]
        indices = _indices(state, result.plan.action)
        print(
            "Adaptive setup consensus -> PASS "
            f"({args.consensus_discard_agreement} deepest completed searches agree on "
            f"DISCARD {','.join(str(index) for index in indices)})"
        )
        return _SearchDecision(result=result, mode="consensus-discard")

    paced = _pace_fallback(state, args)
    if paced is not None and paced.mode != "none":
        return paced

    if best is not None:
        return _SearchDecision(result=best, mode="none")
    if paced is not None:
        return paced
    return _SearchDecision(result=None, mode="none")
