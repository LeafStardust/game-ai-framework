from __future__ import annotations

from dataclasses import dataclass

import games.balatro  # install package-level production policies

from games.balatro.build.consumable_targeting import ContextualConsumableTargetEvaluator
from games.balatro.card import BalatroCard
from games.balatro.consumable import Consumable, ConsumableContext
from games.balatro.state import BalatroState


@dataclass(frozen=True)
class _CardValue:
    total_gain: float


class _NeutralCardEvaluator:
    def evaluate(self, state, **kwargs):
        return _CardValue(0.0)


class _StonePositiveCardEvaluator:
    def evaluate(self, state, **kwargs):
        return _CardValue(0.7 if kwargs.get("enhancement") == "Stone" else 0.0)


class _TowerProbe(Consumable):
    name = "The Tower"
    category = "TAROT"

    def can_use(self, context: ConsumableContext) -> bool:
        return context.has_valid_cards() and len(context.cards) == 1

    def use(self, context: ConsumableContext) -> ConsumableContext:
        context.cards[0].enhancement = "Stone"
        return context

    def get_target_cards(self, state: BalatroState):
        return [[card] for card in state.hand]


def _state(card: BalatroCard) -> BalatroState:
    state = BalatroState()
    state.hand = [card]
    return state


def test_default_target_value_does_not_reward_change_for_its_own_sake() -> None:
    evaluator = ContextualConsumableTargetEvaluator(
        card_evaluator=_NeutralCardEvaluator(),
    )

    ranked = evaluator.rank_targets(
        _state(BalatroCard("2", "Clubs")),
        _TowerProbe(),
    )

    assert evaluator.effective_change_value == 0.0
    assert len(ranked) == 1
    assert ranked[0].effective_changes == 1
    assert ranked[0].contextual_delta == 0.0
    assert ranked[0].total_gain == 0.0


def test_literal_target_value_keeps_real_contextual_improvement_positive() -> None:
    evaluator = ContextualConsumableTargetEvaluator(
        card_evaluator=_StonePositiveCardEvaluator(),
    )

    ranked = evaluator.rank_targets(
        _state(BalatroCard("2", "Clubs")),
        _TowerProbe(),
    )

    assert len(ranked) == 1
    assert ranked[0].contextual_delta == 0.7
    assert ranked[0].total_gain == 0.7


def test_identical_transform_remains_rejected_as_no_op() -> None:
    evaluator = ContextualConsumableTargetEvaluator(
        card_evaluator=_StonePositiveCardEvaluator(),
    )

    ranked = evaluator.rank_targets(
        _state(BalatroCard("2", "Clubs", enhancement="Stone")),
        _TowerProbe(),
    )

    assert ranked == ()


def test_explicit_legacy_change_value_override_remains_available() -> None:
    evaluator = ContextualConsumableTargetEvaluator(
        card_evaluator=_NeutralCardEvaluator(),
        effective_change_value=0.25,
    )

    ranked = evaluator.rank_targets(
        _state(BalatroCard("2", "Clubs")),
        _TowerProbe(),
    )

    assert ranked[0].total_gain == 0.25
