import games.balatro  # noqa: F401 - initialize production policy stack

from games.balatro.bond_pivot_authority import _transition_score
from games.balatro.bonds.composer import Composition
from games.balatro.bonds.motifs import MotifEvaluation, MotifState
from games.balatro.build_health_runtime import RealizedEngineAnalyzer
from games.balatro.live.hand_action_policy import LiveHandActionDecisionEngine
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy
from games.balatro.live.runtime.bond_autonomous_runner import (
    PlaybookJokerAcquisitionPolicy as RuntimeJokerAcquisitionPolicy,
    PlaybookBalatroPackPolicy as RuntimePackPolicy,
    PlaybookBuildAwareShopArbiter as RuntimeShopArbiter,
)
from games.balatro.playbook.red_white.pack_policy import (
    PlaybookBalatroPackPolicy as CanonicalPackPolicy,
)
from games.balatro.playbook.red_white.shop_policy import (
    PlaybookBuildAwareShopArbiter as CanonicalShopArbiter,
)
from games.balatro.shop_booster_policy import BuildAwareShopBoosterPolicy
from games.balatro.shop_reroll_policy import BuildAwareShopRerollPolicy
from games.balatro.shop_utility_scale import ShopUtilityScale
from games.balatro.shop_voucher_policy import VoucherAcquisitionPolicy


def _motif(state: MotifState):
    return MotifEvaluation(motif_id="audit", state=state, relevant_bonds=(), present_components=(), missing_components=(), prescriptions=())


def _composition(coherence: float, motif_state: MotifState):
    motif = _motif(motif_state)
    return Composition(bond_ids=(), motifs=(motif,), conflicts=(), synergies=(), coherence_score=coherence, pivot_resistance=0.0, motif_distance=((motif.motif_id, 0),), prescriptions=())


def test_production_package_installs_all_canonical_bond_integration_layers():
    assert RuntimeJokerAcquisitionPolicy is PlaybookJokerAcquisitionPolicy
    assert RuntimePackPolicy is CanonicalPackPolicy
    assert RuntimeShopArbiter is CanonicalShopArbiter
    assert getattr(LiveHandActionDecisionEngine, "_bond_shop_health_capture_installed", False)
    assert getattr(ShopUtilityScale, "_bond_shop_health_utility_installed", False)
    assert getattr(BuildAwareShopRerollPolicy, "_bond_shop_health_reroll_installed", False)
    assert getattr(PlaybookJokerAcquisitionPolicy, "_bond_pivot_authority_installed", False)
    assert getattr(PlaybookJokerAcquisitionPolicy, "_bond_power_engine_retention_installed", False)
    assert getattr(PlaybookJokerAcquisitionPolicy, "_tactical_scaler_retention_installed", False)
    assert getattr(PlaybookJokerAcquisitionPolicy, "_stateful_admission_installed", False)
    assert getattr(BalatroPackPolicy, "_bond_prescription_policy_installed", False)
    assert getattr(ShopUtilityScale, "_bond_prescription_policy_installed", False)
    assert getattr(RealizedEngineAnalyzer, "_tactical_scaler_health_installed", False)
    assert getattr(RealizedEngineAnalyzer, "_bond_scaler_health_installed", False)
    # D1 strategy execution is now owned directly by the canonical strategy policy;
    # the retired strategy-execution installer flag must not be required.
    assert StrategyAwareLiveHandActionPolicy.__module__ == "games.balatro.live.strategy_hand_policy"
    assert not getattr(StrategyAwareLiveHandActionPolicy, "_strategy_execution_guard_policy_installed", False)
    assert getattr(BuildAwareShopBoosterPolicy, "_strategy_resource_coherence_installed", False)
    assert getattr(VoucherAcquisitionPolicy, "_strategy_resource_coherence_installed", False)


def test_pivot_authority_does_not_double_count_motif_state_already_in_coherence():
    current = _composition(5.0, MotifState.POTENTIAL)
    projected = _composition(8.0, MotifState.ACTIVE)
    net, notes = _transition_score(current, projected)
    assert net == 3.0
    assert any("already included in coherence" in note for note in notes)
