from types import SimpleNamespace

from games.balatro.strategy import (
    AVAILABLE,
    HIGHLIGHTED,
    StrategyAssessment,
    StrategyDefinition,
    StrategyResolution,
    BalatroStrategyTracker,
)
from games.balatro.strategy_multi_engine import PRIMARY, SECONDARY, SUPPORT


def _assessment(strategy_id: str, score: float, status: str = HIGHLIGHTED):
    return StrategyAssessment(
        strategy_id=strategy_id,
        name=strategy_id,
        score=score,
        effectiveness=1.0,
        base_score=0.0,
        status=status,
        gold_owned=0,
        silver_owned=0,
        bronze_owned=0,
        banned_owned=0,
    )


def _resolution(*assessments):
    ordered = tuple(sorted(assessments, key=lambda a: (-a.score, a.strategy_id)))
    dominant = ordered[0].strategy_id if ordered else None
    return StrategyResolution(
        dominant_strategy_id=dominant,
        relevant_strategy_ids=tuple(a.strategy_id for a in ordered[1:3]),
        active_strategy_id=dominant,
        highlighted_strategy_id=dominant,
        committed_strategy_id=dominant,
        active_status=HIGHLIGHTED if ordered else AVAILABLE,
        assessments=ordered,
    )


def test_support_engine_cannot_displace_true_primary_even_with_higher_raw_score():
    tracker = BalatroStrategyTracker({
        "straight": StrategyDefinition("straight", "Straight", primary_hands=("STRAIGHT",)),
        "abstract_joker": StrategyDefinition("abstract_joker", "Abstract"),
    })
    resolution = _resolution(
        _assessment("abstract_joker", 8.0),
        _assessment("straight", 4.0),
    )

    assert tracker.strategy_role("straight") == PRIMARY
    assert tracker.strategy_role("abstract_joker") == SUPPORT
    assert tracker.primary_strategy_id(resolution) == "straight"
    assert tracker.active_engine_ids(resolution) == ("abstract_joker",)


def test_drivers_license_stays_active_as_secondary_engine_after_ante_six():
    tracker = BalatroStrategyTracker({
        "straight": StrategyDefinition("straight", "Straight", primary_hands=("STRAIGHT",)),
        "drivers_license": StrategyDefinition("drivers_license", "Driver's License"),
    })
    resolution = _resolution(
        _assessment("drivers_license", 8.0),
        _assessment("straight", 4.0),
    )
    state = SimpleNamespace(ante=8)

    assert tracker.strategy_role("drivers_license") == SECONDARY
    assert tracker.primary_strategy_id(resolution) == "straight"
    assert tracker.active_engine_ids(resolution) == ("drivers_license",)
    assert tracker._scope_factor(state, "straight", 1, resolution) == 1.0
    assert tracker._scope_factor(state, "drivers_license", 0, resolution) == 0.65


def test_competing_poker_hand_routes_do_not_become_simultaneous_engines():
    tracker = BalatroStrategyTracker({
        "straight": StrategyDefinition("straight", "Straight", primary_hands=("STRAIGHT",)),
        "flush": StrategyDefinition("flush", "Flush", primary_hands=("FLUSH",)),
    })
    resolution = _resolution(
        _assessment("straight", 6.0),
        _assessment("flush", 5.0),
    )

    assert tracker.primary_strategy_id(resolution) == "straight"
    assert tracker.active_engine_ids(resolution) == ()


def test_hand_fit_uses_primary_scoring_route_not_higher_scoring_support_engine(monkeypatch):
    tracker = BalatroStrategyTracker({
        "straight": StrategyDefinition("straight", "Straight", primary_hands=("STRAIGHT",)),
        "abstract_joker": StrategyDefinition("abstract_joker", "Abstract"),
    })
    resolution = _resolution(
        _assessment("abstract_joker", 8.0),
        _assessment("straight", 4.0),
    )
    monkeypatch.setattr(tracker, "observe", lambda state: resolution)
    monkeypatch.setattr(tracker, "strategy_pressure", lambda state: 1.0)
    state = SimpleNamespace(ante=8)

    straight_fit, _ = tracker.hand_fit(state, "STRAIGHT")
    flush_fit, _ = tracker.hand_fit(state, "FLUSH")

    assert straight_fit > 0.0
    assert flush_fit < 0.0
