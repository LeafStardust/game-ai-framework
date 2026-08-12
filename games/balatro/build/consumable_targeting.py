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
    intrinsic_delta: float = 0.0
    rationale: tuple[str, ...] = ()


class ContextualConsumableTargetEvaluator:
    """Rank legal targets for deterministic card-transform consumables.

    Target legality and transformation semantics come from the consumable's real
    ``get_target_cards`` / ``can_use`` / ``use`` implementation. Every simulation
    runs on a deep copy of public state, so target evaluation cannot mutate the
    authoritative state or consume hidden RNG.

    This B6 targeting layer admits deterministic local transformations plus
    Death's directional public-card copy. Destructive deck thinning, generation,
    economy, Joker-targeted, and stochastic effects remain fail-closed until their
    timing/opportunity-cost semantics are modeled.
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
            "Death",
        }
    )

    _RANK_CHIP_VALUE = {
        "2": 0.02,
        "3": 0.03,
        "4": 0.04,
        "5": 0.05,
        "6": 0.06,
        "7": 0.07,
        "8": 0.08,
        "9": 0.09,
        "10": 0.10,
        "J": 0.10,
        "Q": 0.10,
        "K": 0.10,
        "A": 0.11,
    }
    _ENHANCEMENT_VALUE = {
        "Bonus": 0.90,
        "Mult": 1.20,
        "Wild": 0.80,
        "Glass": 1.80,
        "Steel": 2.20,
        "Stone": 0.70,
        "Gold": 1.60,
        "Lucky": 1.30,
    }
    _EDITION_VALUE = {
        "Foil": 0.80,
        "Holographic": 1.50,
        "Polychrome": 2.50,
        "Negative": 4.00,
    }
    _SEAL_VALUE = {
        "Red": 2.00,
        "Blue": 1.50,
        "Gold": 1.40,
        "Purple": 1.20,
    }

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

        is_death = str(getattr(consumable, "name", "")) == "Death"
        contextual_delta = 0.0
        intrinsic_delta = 0.0
        effective_changes = 0
        overwrite_penalty = 0.0
        change_notes: list[str] = []

        for original, transformed in zip(before_cards, after_cards):
            before_value = self._card_build_value(state, original, profile)
            after_value = self._card_build_value(state, transformed, profile)
            contextual_delta += after_value - before_value
            if is_death:
                intrinsic_delta += (
                    self._card_intrinsic_value(transformed)
                    - self._card_intrinsic_value(original)
                )

            changed = self._changed_properties(original, transformed)
            if changed:
                effective_changes += 1
                change_notes.append(
                    f"{self._card_label(original)} -> {self._card_label(transformed)} "
                    f"changed={','.join(changed)}"
                )

            if (
                not is_death
                and original.enhancement is not None
                and transformed.enhancement != original.enhancement
            ):
                overwrite_penalty += self.enhancement_overwrite_penalty

        change_bonus = 0.0 if is_death else (
            effective_changes * self.effective_change_value
        )
        total_gain = (
            contextual_delta
            + intrinsic_delta
            + change_bonus
            - overwrite_penalty
        )
        death_notes: tuple[str, ...] = ()
        if is_death and len(indices) == 2:
            death_notes = (
                (
                    "Death directional copy: "
                    f"hand index {indices[0]} becomes hand index {indices[1]}"
                ),
                f"intrinsic copy delta={intrinsic_delta:.3f}",
            )
        rationale = (
            f"contextual target delta={contextual_delta:.3f}",
            f"effective card changes={effective_changes}",
            f"enhancement overwrite penalty={overwrite_penalty:.3f}",
            *death_notes,
            *change_notes,
        )
        return ConsumableTargetEvaluation(
            target_indices=indices,
            cards=tuple(state.hand[index] for index in indices),
            total_gain=total_gain,
            contextual_delta=contextual_delta,
            effective_changes=effective_changes,
            overwrite_penalty=overwrite_penalty,
            intrinsic_delta=intrinsic_delta,
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

    @classmethod
    def _card_intrinsic_value(cls, card: BalatroCard) -> float:
        value = cls._RANK_CHIP_VALUE.get(str(card.rank), 0.0)
        if card.enhancement:
            value += cls._ENHANCEMENT_VALUE.get(str(card.enhancement), 0.0)
        if card.edition:
            value += cls._EDITION_VALUE.get(str(card.edition), 0.0)
        if card.seal:
            value += cls._SEAL_VALUE.get(str(card.seal), 0.0)
        return value

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
