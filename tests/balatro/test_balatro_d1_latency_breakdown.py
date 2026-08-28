from games.balatro.live.path_aware_hand_action_engine import (
    _build_d1_latency_breakdown,
)


def test_d1_latency_breakdown_separates_nested_search_from_base_policy():
    breakdown = _build_d1_latency_breakdown(
        total=2.0,
        base_elapsed=1.5,
        adaptive_search=0.4,
        confirmation_search=0.2,
        immediate_fallback_search=0.1,
        adaptive_authority=0.05,
        consensus_recovery=0.05,
        strategy_health=0.2,
    )

    assert abs(breakdown.base_policy - 0.8) < 1e-12
    assert abs(breakdown.residual - 0.2) < 1e-12
    assert abs(
        breakdown.base_policy
        + breakdown.adaptive_search
        + breakdown.confirmation_search
        + breakdown.immediate_fallback_search
        + breakdown.adaptive_authority
        + breakdown.consensus_recovery
        + breakdown.strategy_health
        + breakdown.residual
        - breakdown.total
    ) < 1e-12


def test_d1_latency_breakdown_clamps_clock_overlap_instead_of_going_negative():
    breakdown = _build_d1_latency_breakdown(
        total=1.0,
        base_elapsed=0.5,
        adaptive_search=0.4,
        confirmation_search=0.3,
        immediate_fallback_search=0.2,
        adaptive_authority=-0.1,
        consensus_recovery=-0.1,
        strategy_health=0.1,
    )

    assert breakdown.base_policy == 0.0
    assert breakdown.adaptive_authority == 0.0
    assert breakdown.consensus_recovery == 0.0
    assert breakdown.residual == 0.0
    assert all(
        value >= 0.0
        for value in (
            breakdown.total,
            breakdown.base_policy,
            breakdown.adaptive_search,
            breakdown.confirmation_search,
            breakdown.immediate_fallback_search,
            breakdown.adaptive_authority,
            breakdown.consensus_recovery,
            breakdown.strategy_health,
            breakdown.residual,
        )
    )
