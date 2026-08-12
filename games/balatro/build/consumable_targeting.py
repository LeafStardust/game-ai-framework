from __future__ import annotations

import copy
from dataclasses import dataclass

from games.balatro.card import BalatroCard
from games.balatro.consumable import Consumable, ConsumableContext
from games.balatro.state import BalatroState

from .playing_card_synergy import ContextualPlayingCardSynergyEvaluator
from .profile import BalatroBuildProfiler, BuildProfile


@dataclass(frozen=True)
class ConsumableTargetEvaluation:
    """Explainable B6 quality score for one legal consumable target group."""

    target_indices: tuple[int, ...]
    cards: tuple[BalatroCard, ...]
    total_gain: float
    contextual_delta: float
    effective_changes: int
    overwrite_penalty: float
    rationale: tuple[str, ...] = ()


class ContextualConsumableTargetEvaluator:
    """Rank legal targets for deterministic card-transform consumables.

    Target legality and transformation semantics come from the consumable's real
    ``get_target_cards`` / ``can_use`` / ``use`` implementation. Every simulation
    runs on a deep copy of public state, so target evaluation cannot mutate the
    authoritative state or consume hidden RNG.

    This first B6 targeting slice intentionally admits only deterministic Tarot
    cards whose effect is a local rank/suit/enhancement transformation. Destructive,
    copy, generation, economy, Joker-targeted, and stochastic effects remain
    fail-closed until their timing/opportunity-cost semantics are modeled.
    """

    SUPPORTED_TAROTS = frozenset(
        {
            "The Magician",
            "The Empress",
            "The Hierophant",
            "The Lovers",
            "The Chariot",
            "Justice",
            "Strength",
            "The Devil",
            "The Tower",
            "The Star",
            "The Moon",
            "The Sun",
            "The World",
        }
    )

    def __init__(
        self,
        *,
        profiler: BalatroBuildProfiler | None = None,
        card_evaluator: ContextualPlayingCardSynergyEvaluator | None = None,
        effective_change_value: float = 0.10,
        enhancement_overwrite_penalty: float = 0.35,
    ) -> None:
        self.profiler = profiler or BalatroBuildProfiler()
        self.card_evaluator = card_evaluator or ContextualPlayingCardSynergyEvaluator(
            profiler=self.profiler
        )
        self.effective_change_value = float(effective_change_value)
        self.enhancement_overwrite_penalty = float(enhancement_overwrite_penalty)

    def supports(self, consumable: object) -> bool:
        return (
            isinstance(consumable, Consumable)
            and str(getattr(consumable, "category", "")).upper() == "TAROT"
            and str(getattr(consumable, "name", "")) in self.SUPPORTED_TAROTS
        )

    def recommend(
        self,
        state: BalatroState,
        consumable: object,
    ) -> ConsumableTargetEvaluation | None:
        ranked = self.rank_targets(state, consumable)
        return ranked[0] if ranked else None

    def rank_targets(
        self,
        state: BalatroState,
        consumable: object,
    ) -> tuple[ConsumableTargetEvaluation, ...]:
        if not self.supports(consumable):
            return ()

        profile = self.profiler.profile(state)
        index_by_id = {id(card): index for index, card in enumerate(state.hand)}
        evaluations: list[ConsumableTargetEvaluation] = []

        for group in consumable.get_target_cards(state):
            if not group or any(id(card) not in index_by_id for card in group):
                continue
            indices = tuple(index_by_id[id(card)] for card in group)
            if len(set(indices)) != len(indices):
                continue

            evaluation = self._evaluate_target(
                state,
                consumable,
                indices,
                profile=profile,
            )
            if evaluation is not None:
                evaluations.append(evaluation)

        return tuple(
            sorted(
                evaluations,
                key=lambda evaluation: (
                    -evaluation.total_gain,
                    -evaluation.effective_changes,
                    evaluation.target_indices,
                ),
            )
        )

    def _evaluate_target(
        self,
        state: BalatroState,
        consumable: Consumable,
        indices: tuple[int, ...],
        *,
        profile: BuildProfile,
    ) -> ConsumableTargetEvaluation | None:
        simulated_state = copy.deepcopy(state)
        simulated_consumable = copy.deepcopy(consumable)
        simulated_cards = [simulated_state.hand[index] for index in indices]
        context = ConsumableContext(state=simulated_state, cards=simulated_cards)

        if not simulated_consumable.can_use(context):
            return None

        before_cards = [copy.deepcopy(card) for card in simulated_cards]
        simulated_consumable.use(context)
        after_cards = simulated_cards

        contextual_delta = 0.0
        effective_changes = 0
        overwrite_penalty = 0.0
        change_notes: list[str] = []

        for original, transformed in zip(before_cards, after_cards):
            before_value = self._card_build_value(state, original, profile)
            after_value = self._card_build_value(state, transformed, profile)
            contextual_delta += after_value - before_value

            changed = self._changed_properties(original, transformed)
            if changed:
                effective_changes += 1
                change_notes.append(
                    f"{self._card_label(original)} -> {self._card_label(transformed)} "
                    f"changed={','.join(changed)}"
                )

            if (
                original.enhancement is not None
                and transformed.enhancement != original.enhancement
            ):
                overwrite_penalty += self.enhancement_overwrite_penalty

        total_gain = (
            contextual_delta
            + effective_changes * self.effective_change_value
            - overwrite_penalty
        )
        rationale = (
            f"contextual target delta={contextual_delta:.3f}",
            f"effective card changes={effective_changes}",
            f"enhancement overwrite penalty={overwrite_penalty:.3f}",
            *change_notes,
        )
        return ConsumableTargetEvaluation(
            target_indices=indices,
            cards=tuple(state.hand[index] for index in indices),
            total_gain=total_gain,
            contextual_delta=contextual_delta,
            effective_changes=effective_changes,
            overwrite_penalty=overwrite_penalty,
            rationale=rationale,
        )

    def _card_build_value(
        self,
        state: BalatroState,
        card: BalatroCard,
        profile: BuildProfile,
    ) -> float:
        return self.card_evaluator.evaluate(
            state,
            rank=card.rank,
            suit=card.suit,
            enhancement=card.enhancement,
            seal=card.seal,
            edition=card.edition,
            profile=profile,
        ).total_gain

    @staticmethod
    def _changed_properties(
        before: BalatroCard,
        after: BalatroCard,
    ) -> tuple[str, ...]:
        changed = []
        for name in ("rank", "suit", "enhancement", "edition", "seal"):
            if getattr(before, name) != getattr(after, name):
                changed.append(name)
        return tuple(changed)

    @staticmethod
    def _card_label(card: BalatroCard) -> str:
        parts = [str(card.rank), str(card.suit)]
        if card.enhancement:
            parts.append(str(card.enhancement))
        if card.edition:
            parts.append(str(card.edition))
        if card.seal:
            parts.append(f"{card.seal} Seal")
        return " ".join(parts)
