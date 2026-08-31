from __future__ import annotations

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.live.pack import LivePackChoice
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.semantic_benchmark import SemanticBenchmarkCase, SemanticCheck
from games.balatro.state import BalatroState


class _SyntheticConsumable:
    def can_use(self, context) -> bool:
        return True


class _SyntheticConsumableFactory:
    def create(self, data, *, live_id=None):
        return _SyntheticConsumable()


class _NoTargetEvaluator:
    def recommend(self, state, consumable):
        return None


def _pack_choice(*, label: str, kind: str) -> LivePackChoice:
    return LivePackChoice(
        area_index=0,
        address=1,
        data={
            "ability_set": kind,
            "label": label,
            "ability_name": label,
            "live_id": 1,
        },
    )


def _rank_pair(policy: BalatroPackPolicy, state: BalatroState, choice: LivePackChoice):
    select = BalatroAction(SELECT_PACK_CARD, target=choice)
    skip = BalatroAction(SKIP_BOOSTER)
    ranked = policy.rank_actions(state, [select, skip])
    select_score = next(score for score in ranked if score.action.name == SELECT_PACK_CARD)
    skip_score = next(score for score in ranked if score.action.name == SKIP_BOOSTER)
    return ranked, select_score, skip_score


def _targeted_consumable_without_legal_positive_target_skips() -> SemanticCheck:
    state = BalatroState()
    state.phase = "ARCANA_PACK"
    policy = BalatroPackPolicy(
        consumable_factory=_SyntheticConsumableFactory(),
        consumable_target_evaluator=_NoTargetEvaluator(),
    )
    ranked, select_score, skip_score = _rank_pair(
        policy,
        state,
        _pack_choice(label="Death", kind="TAROT"),
    )
    passed = (
        abs(float(skip_score.total)) <= 1e-12
        and float(select_score.total) < 0.0
        and ranked[0].action.name == SKIP_BOOSTER
    )
    return SemanticCheck(
        passed,
        observed=(
            f"Death={select_score.total:.3f}, skip={skip_score.total:.3f}, "
            f"selected={ranked[0].action.name}"
        ),
        expected="installed D9 keeps a targeted Tarot below Skip when D10/B6 supplies no positive legal target",
        detail=(
            "opened-pack target legality belongs to D10/B6; generic Tarot/category value and strategy evidence "
            "must not authorize a targeted effect whose public state has no positive admitted target"
        ),
    )


def _nonadmitted_stochastic_effect_fails_closed() -> SemanticCheck:
    state = BalatroState()
    state.phase = "SPECTRAL_PACK"
    policy = BalatroPackPolicy(consumable_factory=_SyntheticConsumableFactory())
    ranked, select_score, skip_score = _rank_pair(
        policy,
        state,
        _pack_choice(label="Ectoplasm", kind="SPECTRAL"),
    )
    passed = (
        abs(float(skip_score.total)) <= 1e-12
        and float(select_score.total) < 0.0
        and ranked[0].action.name == SKIP_BOOSTER
    )
    return SemanticCheck(
        passed,
        observed=(
            f"Ectoplasm={select_score.total:.3f}, skip={skip_score.total:.3f}, "
            f"selected={ranked[0].action.name}"
        ),
        expected="a stochastic/destructive Spectral not admitted in the current public state remains below opened-pack Skip=0",
        detail=(
            "classification metadata may change when an explicit outcome model is installed; the semantic invariant "
            "is action-level admission: without positive complete public-state value, generic Spectral utility must "
            "not lift the visible choice above Skip"
        ),
    )


def _unclassified_spectral_fails_closed() -> SemanticCheck:
    state = BalatroState()
    state.phase = "SPECTRAL_PACK"
    label = "Synthetic Unmodeled Spectral"
    policy = BalatroPackPolicy(consumable_factory=_SyntheticConsumableFactory())
    ranked, select_score, skip_score = _rank_pair(
        policy,
        state,
        _pack_choice(label=label, kind="SPECTRAL"),
    )
    passed = (
        label not in BalatroPackPolicy.classified_spectrals()
        and abs(float(skip_score.total)) <= 1e-12
        and float(select_score.total) < 0.0
        and ranked[0].action.name == SKIP_BOOSTER
    )
    return SemanticCheck(
        passed,
        observed=(
            f"classified={(label in BalatroPackPolicy.classified_spectrals())}, "
            f"unmodeled={select_score.total:.3f}, skip={skip_score.total:.3f}, "
            f"selected={ranked[0].action.name}"
        ),
        expected="an unclassified visible Spectral fails closed instead of inheriting generic positive utility",
        detail=(
            "D9 must require explicit mechanics/outcome ownership for unknown stochastic effects; strategy-plan "
            "bonuses are admission-subordinate and cannot lift a non-positive base choice"
        ),
    )


RED_WHITE_PHASE4_PACK_CASES = (
    SemanticBenchmarkCase(
        case_id="resource.pack.target_requires_positive_legal_target",
        category="RESOURCE_COHERENCE",
        description="targeted opened-pack effect requires positive D10/B6 target",
        evaluate=_targeted_consumable_without_legal_positive_target_skips,
        source="Phase 4 pack audit: installed D9 target-legality boundary",
    ),
    SemanticBenchmarkCase(
        case_id="resource.pack.deferred_stochastic_fails_closed",
        category="RESOURCE_COHERENCE",
        description="non-admitted stochastic opened-pack effect remains below Skip",
        evaluate=_nonadmitted_stochastic_effect_fails_closed,
        source="Phase 4 pack audit: explicit stochastic-model admission boundary",
    ),
    SemanticBenchmarkCase(
        case_id="resource.pack.unclassified_effect_fails_closed",
        category="RESOURCE_COHERENCE",
        description="unclassified opened-pack effect cannot inherit generic utility",
        evaluate=_unclassified_spectral_fails_closed,
        source="Phase 4 pack audit: unsupported visible-effect fail-closed boundary",
    ),
)
