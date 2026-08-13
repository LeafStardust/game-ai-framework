from types import SimpleNamespace

import pytest

from games.balatro.build.joker_semantics import (
    CONSUMABLE_DUPLICATE,
    SemanticJokerBehaviorAnalyzer,
)
from games.balatro.card import BalatroCard
from games.balatro.jokers.perkeo import PerkeoJoker
from games.balatro.live.external.live_memory_planet_policy_validation import (
    _execution_guard_errors,
    _state_fingerprint,
    build_live_d7_view,
)
from games.balatro.live.joker_projection import LiveJokerScoreProjector
from games.balatro.live.planet_policy import USE, LivePlanetPolicy
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.planets import create_planet
from games.balatro.state import BalatroState


class _Blind:
    requirement = 100_000


class _ActionGenerator:
    def generate_play_actions(self, state):
        return [object()]


class _HandEvaluator:
    def __init__(self):
        self.action_generator = _ActionGenerator()

    def project_play(self, state, action):
        level = int(state.hand_levels.get("PAIR", 1))
        score = 100.0 + 15.0 * (level - 1)
        return SimpleNamespace(
            clear_probability=0.0,
            expected_hand_score=score,
            hand_score=int(score),
            maximum_hand_score=int(score),
            joker_projection_complete=True,
        )


class _Descriptor:
    def __init__(self, duplicate):
        self.produces = frozenset({CONSUMABLE_DUPLICATE}) if duplicate else frozenset()

    def feature_magnitude(self, feature):
        return 1.0


class _Analyzer:
    def __init__(self, duplicate):
        self.duplicate = duplicate

    def describe(self, joker):
        return _Descriptor(self.duplicate)


def _snapshot():
    return LiveBalatroSnapshot(1, "SELECTING_HAND", True, {})


def _state(*, duplicate=False):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [BalatroCard("8", "Hearts"), BalatroCard("8", "Clubs")]
    state.blind = _Blind()
    planet = create_planet("MERCURY")
    planet.live_id = 501
    state.consumables = [planet]
    state.jokers = [object()] if duplicate else []
    return state


def _policy(duplicate=False):
    return LivePlanetPolicy(
        hand_evaluator=_HandEvaluator(),
        joker_analyzer=_Analyzer(duplicate),
    )


def test_view_exposes_default_use_and_positive_hold():
    use_view = build_live_d7_view(_snapshot(), _state(), policy=_policy())
    assert use_view.candidates[0].decision.decision == USE
    assert use_view.recommendation is use_view.candidates[0]

    hold_view = build_live_d7_view(
        _snapshot(),
        _state(duplicate=True),
        policy=_policy(True),
    )
    assert hold_view.candidates[0].decision.duplicate_hold_value == 1.0
    assert hold_view.candidates[0].decision.decision == "HOLD"
    assert hold_view.recommendation is None


def test_real_perkeo_is_score_neutral_and_creates_positive_planet_hold_value():
    perkeo = PerkeoJoker()
    assert LiveJokerScoreProjector.supports(perkeo)

    descriptor = SemanticJokerBehaviorAnalyzer().describe(perkeo)
    assert CONSUMABLE_DUPLICATE in descriptor.produces
    assert descriptor.feature_magnitude(CONSUMABLE_DUPLICATE) >= 1.0

    state = _state()
    state.jokers = [perkeo]
    view = build_live_d7_view(
        _snapshot(),
        state,
        policy=LivePlanetPolicy(hand_evaluator=_HandEvaluator()),
    )
    decision = view.candidates[0].decision

    assert decision.decision == "HOLD"
    assert decision.duplicate_hold_value >= 1.0
    assert decision.rationale[0].startswith(
        "HOLD: observable consumable-duplication value"
    )
    assert view.recommendation is None


def test_execution_guard_requires_exact_top_use():
    view = build_live_d7_view(_snapshot(), _state(), policy=_policy())
    assert _execution_guard_errors(
        view,
        expect_planet="Mercury",
        expect_index=0,
        expect_decision=USE,
    ) == ()
    assert _execution_guard_errors(
        view,
        expect_planet="Jupiter",
        expect_index=0,
        expect_decision=USE,
    )


def test_fingerprint_tracks_planet_relevant_changes():
    state = _state()
    before = _state_fingerprint(state)
    state.hand_levels["PAIR"] += 1
    assert _state_fingerprint(state) != before

    state = _state()
    before = _state_fingerprint(state)
    state.consumables[0].live_id = 999
    assert _state_fingerprint(state) != before


def test_view_rejects_non_hand_phase():
    state = _state()
    state.phase = "SHOP"
    with pytest.raises(ValueError, match="requires SELECTING_HAND"):
        build_live_d7_view(_snapshot(), state, policy=_policy())
