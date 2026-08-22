from types import SimpleNamespace

from games.balatro.bonds.build_health import BuildHealthState
from games.balatro.bonds.composer import Composition
from games.balatro.bonds.score_projection import project_score
from games.balatro.live.bond_health import (
    evaluate_live_build_health,
    score_projection_from_blind_plan,
    score_projection_from_live_play,
)


def state(*, requirement=1000, score=100, hands=3):
    return SimpleNamespace(
        blind=SimpleNamespace(requirement=requirement),
        score=score,
        hands_remaining=hands,
        money=25,
        ante=4,
    )


def empty_composition(coherence=0.0):
    return Composition(
        bond_ids=(),
        motifs=(),
        conflicts=(),
        synergies=(),
        coherence_score=coherence,
        pivot_resistance=0.0,
        motif_distance=(),
        prescriptions=(),
    )


def test_generic_projection_reads_actual_live_state_fields():
    live = state(requirement=1200, score=300, hands=3)
    projection = project_score(live, candidate_hand_scores=[250])
    assert projection.blind_requirement == 1200
    assert projection.current_score == 300
    assert projection.expected_total == 1050


def test_live_play_adapter_preserves_real_min_expected_max_without_averaging():
    live = state(requirement=2000, score=200, hands=4)
    raw = SimpleNamespace(
        hand_score=300,
        expected_hand_score=450.0,
        maximum_hand_score=700,
        clear_probability=0.25,
    )
    projection = score_projection_from_live_play(live, raw)
    assert projection.conservative_hand_score == 300
    assert projection.expected_hand_score == 450
    assert projection.ceiling_hand_score == 700
    assert projection.clear_probability == 0.25
    assert projection.expected_total == 2000


def test_search_plan_probability_is_forwarded_without_claiming_a_guaranteed_floor():
    live = state(requirement=1000, score=200, hands=2)
    plan = SimpleNamespace(
        value=SimpleNamespace(expected_score=900.0, clear_probability=0.72)
    )
    projection = score_projection_from_blind_plan(live, plan)
    assert projection.clear_probability == 0.72
    assert projection.conservative_hand_score == 0.0
    assert projection.expected_total == 900.0


def test_high_coherence_cannot_rescue_live_projection_whose_ceiling_cannot_clear():
    live = state(requirement=5000, score=0, hands=2)
    raw = SimpleNamespace(
        hand_score=200,
        expected_hand_score=300.0,
        maximum_hand_score=400,
        clear_probability=0.0,
    )
    snapshot = evaluate_live_build_health(
        live,
        developments=(),
        composition=empty_composition(coherence=9999.0),
        live_projection=raw,
    )
    assert snapshot.source == "live_play"
    assert snapshot.projection.ceiling_margin < 0
    assert snapshot.health.state == BuildHealthState.COLLAPSING
