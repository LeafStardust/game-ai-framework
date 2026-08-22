from games.balatro.bond_pivot_authority import _REQUIRED_NET_GAIN, _transition_score
from games.balatro.bonds.composer import Composition
from games.balatro.bonds.motifs import MotifEvaluation, MotifState
from games.balatro.live.strategy_health import StrategyHealthMode


def _motif(motif_id: str, state: MotifState, missing: int = 0):
    return MotifEvaluation(
        motif_id=motif_id,
        state=state,
        relevant_bonds=(),
        present_components=(),
        missing_components=tuple(f"M{i}" for i in range(missing)),
        prescriptions=(),
    )


def _composition(*, coherence=0.0, resistance=0.0, motifs=()):
    return Composition(
        bond_ids=(),
        motifs=tuple(motifs),
        conflicts=(),
        synergies=(),
        coherence_score=float(coherence),
        pivot_resistance=float(resistance),
        motif_distance=tuple((m.motif_id, m.missing_count) for m in motifs),
        prescriptions=(),
    )


def test_health_thresholds_make_strong_builds_harder_to_pivot():
    assert _REQUIRED_NET_GAIN[StrategyHealthMode.SURVIVE] < _REQUIRED_NET_GAIN[StrategyHealthMode.REPAIR]
    assert _REQUIRED_NET_GAIN[StrategyHealthMode.REPAIR] < _REQUIRED_NET_GAIN[StrategyHealthMode.HOLD]
    assert _REQUIRED_NET_GAIN[StrategyHealthMode.HOLD] < _REQUIRED_NET_GAIN[StrategyHealthMode.REINFORCE]
    assert _REQUIRED_NET_GAIN[StrategyHealthMode.REINFORCE] < _REQUIRED_NET_GAIN[StrategyHealthMode.EXPLOIT]


def test_losing_active_motif_and_resistance_is_explicit_disruption_cost():
    current = _composition(
        coherence=12.0,
        resistance=6.0,
        motifs=(_motif("engine", MotifState.ACTIVE),),
    )
    projected = _composition(coherence=14.0, resistance=2.0, motifs=())
    net, notes = _transition_score(current, projected)
    assert net < 0.0
    assert any("disruption cost=" in note for note in notes)


def test_motif_upgrade_and_closer_distance_reward_reinforcement():
    current = _composition(
        coherence=8.0,
        resistance=3.0,
        motifs=(_motif("engine", MotifState.POTENTIAL, missing=2),),
    )
    projected = _composition(
        coherence=10.0,
        resistance=3.0,
        motifs=(_motif("engine", MotifState.ACTIVE, missing=0),),
    )
    net, _ = _transition_score(current, projected)
    assert net > 0.0


def test_more_coherence_without_structure_loss_is_positive():
    current = _composition(coherence=5.0, resistance=2.0)
    projected = _composition(coherence=8.0, resistance=2.0)
    net, _ = _transition_score(current, projected)
    assert net == 3.0
