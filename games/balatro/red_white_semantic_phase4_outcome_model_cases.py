from __future__ import annotations

from types import SimpleNamespace

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.build.judgement_expectation import JudgementExpectationEvaluator
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


class _SyntheticJokerFactory:
    def create(self, record):
        return SimpleNamespace(
            name=str(record.get("label") or record.get("center") or "Synthetic Joker"),
            label=str(record.get("label") or record.get("center") or "Synthetic Joker"),
            edition=None,
        )


class _ConstantJokerValue:
    def evaluate(self, state, candidate):
        return SimpleNamespace(total_gain=2.0)


def _choice(label: str, kind: str) -> LivePackChoice:
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


def _generative_pack_requires_observed_public_pool() -> SemanticCheck:
    state = BalatroState()
    state.phase = "ARCANA_PACK"
    state.joker_slots = 5
    state.jokers = []
    state.joker_generation_pool_observed = False

    policy = BalatroPackPolicy(consumable_factory=_SyntheticConsumableFactory())
    ranked, select_score, skip_score = _rank_pair(
        policy,
        state,
        _choice("Judgement", "TAROT"),
    )
    passed = (
        abs(float(skip_score.total)) <= 1e-12
        and float(select_score.total) < 0.0
        and ranked[0].action.name == SKIP_BOOSTER
    )
    return SemanticCheck(
        passed,
        observed=(
            f"pool_observed={state.joker_generation_pool_observed}, "
            f"Judgement={select_score.total:.3f}, skip={skip_score.total:.3f}, "
            f"selected={ranked[0].action.name}"
        ),
        expected="generative Judgement remains below opened-pack Skip until its authoritative public outcome pool is observed",
        detail=(
            "D9 may value a random generated Joker only through the explicit public eligible-pool model; absence of that "
            "public catalogue must fail closed rather than falling back to generic Tarot value"
        ),
    )


def _judgement_public_model_is_complete_and_bounded() -> SemanticCheck:
    state = BalatroState()
    state.joker_slots = 5
    state.jokers = []
    state.stake_name = "WHITE"
    state.joker_generation_pool_observed = True
    state.joker_generation_edition_rate = 1.0
    state.visible_poker_hands = ("PAIR", "HIGH_CARD")
    records = tuple(
        {
            "center": f"j_synthetic_{index}",
            "label": f"Synthetic {index}",
            "ability_name": f"Synthetic {index}",
            "ability_set": "JOKER",
        }
        for index in range(10)
    )
    state.joker_generation_pools = {
        "COMMON": records,
        "UNCOMMON": records,
        "RARE": records,
    }

    evaluator = JudgementExpectationEvaluator(
        joker_factory=_SyntheticJokerFactory(),
        joker_value=_ConstantJokerValue(),
    )
    first = evaluator.evaluate(state)
    second = evaluator.evaluate(state)
    rationale = " | ".join(first.rationale)
    passed = (
        first.available
        and first.complete
        and first.expected_total_gain > 0.0
        and abs(float(first.expected_total_gain) - float(second.expected_total_gain)) <= 1e-12
        and first.outcome_count == 18
        and "omitted probability mass remains zero" in rationale
        and "no RNG sample" in rationale
    )
    return SemanticCheck(
        passed,
        observed=(
            f"available={first.available}, complete={first.complete}, outcomes={first.outcome_count}, "
            f"gain1={first.expected_total_gain:.3f}, gain2={second.expected_total_gain:.3f}"
        ),
        expected="Judgement uses a deterministic bounded lower bound over the observed public eligible pool, with omitted mass valued at zero",
        detail=(
            "large public outcome catalogues may be bounded for latency, but the evaluator must retain the full pool "
            "denominator and never inspect RNG state, future pool order, or a selected future outcome"
        ),
    )


def _destructive_spectral_requires_complete_public_state() -> SemanticCheck:
    state = BalatroState()
    state.phase = "SPECTRAL_PACK"
    state.hand = []

    policy = BalatroPackPolicy(consumable_factory=_SyntheticConsumableFactory())
    ranked, select_score, skip_score = _rank_pair(
        policy,
        state,
        _choice("Immolate", "SPECTRAL"),
    )
    passed = (
        abs(float(skip_score.total)) <= 1e-12
        and float(select_score.total) < 0.0
        and ranked[0].action.name == SKIP_BOOSTER
    )
    return SemanticCheck(
        passed,
        observed=(
            f"public_hand={len(state.hand)}, Immolate={select_score.total:.3f}, "
            f"skip={skip_score.total:.3f}, selected={ranked[0].action.name}"
        ),
        expected="destructive Immolate remains below Skip when the public hand cannot support its explicit destruction expectation",
        detail=(
            "destructive effects must not receive generic Spectral utility; D9 may select them only when their explicit "
            "public-state outcome model is available, complete, and positive"
        ),
    )


RED_WHITE_PHASE4_OUTCOME_MODEL_CASES = (
    SemanticBenchmarkCase(
        case_id="resource.outcome.generative_requires_public_pool",
        category="RESOURCE_COHERENCE",
        description="generative pack effect requires observed public outcome pool",
        evaluate=_generative_pack_requires_observed_public_pool,
        source="Phase 4 outcome audit: generative public-state ownership",
    ),
    SemanticBenchmarkCase(
        case_id="resource.outcome.judgement_bounded_public_model",
        category="RESOURCE_COHERENCE",
        description="Judgement expectation is deterministic bounded public-pool lower bound",
        evaluate=_judgement_public_model_is_complete_and_bounded,
        source="Phase 4 outcome audit: bounded stochastic expectation contract",
    ),
    SemanticBenchmarkCase(
        case_id="resource.outcome.destructive_requires_complete_state",
        category="RESOURCE_COHERENCE",
        description="destructive Spectral fails closed without complete public-state model",
        evaluate=_destructive_spectral_requires_complete_public_state,
        source="Phase 4 outcome audit: destructive public-state ownership",
    ),
)
