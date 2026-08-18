from types import SimpleNamespace

from games.balatro.build.consumable_targeting import ConsumableTargetEvaluation
from games.balatro.card import BalatroCard
from games.balatro.live.consumable_timing_base import (
    HOLD,
    USE,
    ConsumableTimingRecommendation,
)
from games.balatro.live.strategy_consumable_timing import (
    StrategyAwareConsumableTargetEvaluator,
    StrategyAwareLiveConsumableTimingPolicy,
)
from games.balatro.state import BalatroState


class _Consumable:
    category = "TAROT"

    def __init__(self, name: str) -> None:
        self.name = name


class _ItemTracker:
    def __init__(self, values: dict[str, float]) -> None:
        self.values = values

    def evaluate_item(self, state, item, *, kind: str):
        assert kind == "CONSUMABLE"
        return SimpleNamespace(value=self.values.get(item.name, 0.0))


class _FixedStrategyTimingPolicy(StrategyAwareLiveConsumableTimingPolicy):
    def __init__(self, recommendations, *, strategy_tracker) -> None:
        self._fixed = {
            id(recommendation.consumable): recommendation
            for recommendation in recommendations
        }
        super().__init__(strategy_tracker=strategy_tracker)

    def recommend(self, state, consumable):
        return self._fixed[id(consumable)]


def _recommendation(consumable, *, decision=USE, immediate_gain=0.0):
    return ConsumableTimingRecommendation(
        decision=decision,
        consumable=consumable,
        target=None,
        before_projection=None,
        after_projection=None,
        required_per_hand=0.0,
        immediate_gain=immediate_gain,
    )


def test_d5_strategy_breaks_only_an_otherwise_equal_use_tie():
    aligned = _Consumable("Alpha")
    lexical_winner = _Consumable("Zulu")
    state = BalatroState()
    state.consumables = [aligned, lexical_winner]

    policy = _FixedStrategyTimingPolicy(
        [_recommendation(aligned), _recommendation(lexical_winner)],
        strategy_tracker=_ItemTracker({"Alpha": 2.0, "Zulu": 0.0}),
    )

    ranked = policy.recommend_inventory(state)

    assert ranked[0].consumable is aligned
    assert "D5 universal-strategy use fit=+2.000000" in ranked[0].rationale


def test_d5_strategy_cannot_override_stronger_immediate_tactical_value():
    aligned = _Consumable("Aligned")
    tactical = _Consumable("Tactical")
    state = BalatroState()
    state.consumables = [aligned, tactical]

    policy = _FixedStrategyTimingPolicy(
        [
            _recommendation(aligned, immediate_gain=0.0),
            _recommendation(tactical, immediate_gain=5.0),
        ],
        strategy_tracker=_ItemTracker({"Aligned": 100.0, "Tactical": 0.0}),
    )

    ranked = policy.recommend_inventory(state)

    assert ranked[0].consumable is tactical


def test_d5_strategy_never_turns_hold_into_use():
    aligned_hold = _Consumable("Aligned Hold")
    ordinary_use = _Consumable("Ordinary Use")
    state = BalatroState()
    state.consumables = [aligned_hold, ordinary_use]

    policy = _FixedStrategyTimingPolicy(
        [
            _recommendation(aligned_hold, decision=HOLD),
            _recommendation(ordinary_use, decision=USE),
        ],
        strategy_tracker=_ItemTracker({"Aligned Hold": 100.0}),
    )

    ranked = policy.recommend_inventory(state)

    assert ranked[0].consumable is ordinary_use
    assert ranked[0].should_use
    assert not ranked[1].should_use


class _GoldEnhancer:
    name = "Test Gold Enhancer"
    category = "TAROT"

    def can_use(self, context) -> bool:
        return len(context.cards) == 1

    def use(self, context):
        context.cards[0].enhancement = "Gold"
        return context


class _FixedTargetEvaluator:
    def __init__(self, evaluations) -> None:
        self.evaluations = tuple(evaluations)

    def supports(self, consumable) -> bool:
        return True

    def rank_targets(self, state, consumable):
        return self.evaluations


class _StructuralTracker:
    def __init__(self, *, active=True) -> None:
        self.definitions = {
            "gold_cards": SimpleNamespace(
                preferred_suits=frozenset(),
                preferred_enhancements=frozenset({"Gold"}),
                preferred_seals=frozenset(),
                preferred_editions=frozenset(),
                preferred_ranks=frozenset(),
                face_mode=None,
            )
        }
        self.active = active

    def observe(self, state):
        assessment = SimpleNamespace(strategy_id="gold_cards", score=10.0)
        return SimpleNamespace(
            dominant_strategy_id="gold_cards" if self.active else None,
            relevant_strategy_ids=(),
            assessments=(assessment,),
        )

    def definitions_for_path(self, strategy_id):
        definition = self.definitions.get(strategy_id)
        return () if definition is None else (definition,)


class _InheritedStructuralTracker(_StructuralTracker):
    def __init__(self) -> None:
        super().__init__()
        parent = self.definitions.pop("gold_cards")
        leaf = SimpleNamespace(
            preferred_suits=frozenset(),
            preferred_enhancements=frozenset(),
            preferred_seals=frozenset(),
            preferred_editions=frozenset(),
            preferred_ranks=frozenset(),
            face_mode=None,
        )
        self.definitions = {"gold_parent": parent, "gold_leaf": leaf}

    def observe(self, state):
        assessment = SimpleNamespace(strategy_id="gold_leaf", score=10.0)
        return SimpleNamespace(
            dominant_strategy_id="gold_leaf",
            relevant_strategy_ids=(),
            assessments=(assessment,),
        )

    def definitions_for_path(self, strategy_id):
        assert strategy_id == "gold_leaf"
        return (self.definitions["gold_parent"], self.definitions["gold_leaf"])


def _target(index: int, card: BalatroCard, *, gain: float = 1.0):
    return ConsumableTargetEvaluation(
        target_indices=(index,),
        cards=(card,),
        total_gain=gain,
        contextual_delta=gain,
        effective_changes=1,
        overwrite_penalty=0.0,
    )


def test_d6_strategy_breaks_equal_legal_target_tie_by_projected_structure():
    already_gold = BalatroCard("A", "Spades", enhancement="Gold")
    plain = BalatroCard("K", "Hearts")
    state = BalatroState()
    state.hand = [already_gold, plain]
    first = _target(0, already_gold)
    second = _target(1, plain)

    evaluator = StrategyAwareConsumableTargetEvaluator(
        _FixedTargetEvaluator((first, second)),
        strategy_tracker=_StructuralTracker(),
    )

    ranked = evaluator.rank_targets(state, _GoldEnhancer())

    assert ranked[0].target_indices == (1,)


def test_d6_target_fit_inherits_parent_card_preferences_at_a_leaf():
    already_gold = BalatroCard("A", "Spades", enhancement="Gold")
    plain = BalatroCard("K", "Hearts")
    state = BalatroState()
    state.hand = [already_gold, plain]

    evaluator = StrategyAwareConsumableTargetEvaluator(
        _FixedTargetEvaluator((_target(0, already_gold), _target(1, plain))),
        strategy_tracker=_InheritedStructuralTracker(),
    )

    ranked = evaluator.rank_targets(state, _GoldEnhancer())

    assert ranked[0].target_indices == (1,)


def test_d6_strategy_cannot_override_higher_base_target_gain():
    already_gold = BalatroCard("A", "Spades", enhancement="Gold")
    plain = BalatroCard("K", "Hearts")
    state = BalatroState()
    state.hand = [already_gold, plain]
    stronger = _target(0, already_gold, gain=2.0)
    aligned = _target(1, plain, gain=1.0)

    evaluator = StrategyAwareConsumableTargetEvaluator(
        _FixedTargetEvaluator((stronger, aligned)),
        strategy_tracker=_StructuralTracker(),
    )

    ranked = evaluator.rank_targets(state, _GoldEnhancer())

    assert ranked[0].target_indices == (0,)


def test_d6_zero_strategy_evidence_preserves_base_target_order():
    already_gold = BalatroCard("A", "Spades", enhancement="Gold")
    plain = BalatroCard("K", "Hearts")
    state = BalatroState()
    state.hand = [already_gold, plain]
    first = _target(0, already_gold)
    second = _target(1, plain)

    evaluator = StrategyAwareConsumableTargetEvaluator(
        _FixedTargetEvaluator((first, second)),
        strategy_tracker=_StructuralTracker(active=False),
    )

    assert evaluator.rank_targets(state, _GoldEnhancer()) == (first, second)
