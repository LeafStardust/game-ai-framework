from __future__ import annotations

"""Value Cryptid from the visible card it will duplicate.

Cryptid has no hidden outcome once its target is chosen: it creates two exact copies
of one public hand card.  The useful question is therefore whether increasing that
card's representation improves the public permanent deck.

Use the same B6 contextual/intrinsic card model already used for Hanged Man, but in
reverse.  A source is valuable only to the extent that it is better than the current
owned-deck average; two copies contribute twice that relative improvement.  Public
permanent chip bonuses are included on the same 0.01-per-chip scale already used by
B6 rank-chip intrinsic values.  This avoids a generic shop category bonus or a
fabricated fixed Cryptid value.
"""

import copy
from dataclasses import dataclass

from games.balatro.consumable import ConsumableContext
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore


CRYPTID = "Cryptid"


@dataclass(frozen=True)
class CryptidTargetExpectation:
    cards: tuple
    target_index: int
    total_gain: float
    contextual_delta: float
    intrinsic_delta: float
    owned_deck_size: int
    rationale: tuple[str, ...]


def _intrinsic_with_permanent_chips(evaluator, card) -> float:
    return (
        evaluator._card_intrinsic_value(card)
        + 0.01 * float(getattr(card, "permanent_bonus", 0) or 0)
    )


def _best_cryptid_target(self, state, target) -> CryptidTargetExpectation | None:
    if not list(getattr(state, "hand", ())):
        return None

    owned = self.consumable_target_evaluator._owned_deck_for_thinning(state)
    if owned is None or not owned[0]:
        return None

    owned_cards, source = owned
    profile_state = copy.copy(state)
    profile_state.deck = list(owned_cards)
    profile = self.consumable_target_evaluator.profiler.profile(profile_state)

    contextual_values = [
        self.consumable_target_evaluator._card_build_value(profile_state, card, profile)
        for card in owned_cards
    ]
    intrinsic_values = [
        _intrinsic_with_permanent_chips(self.consumable_target_evaluator, card)
        for card in owned_cards
    ]
    average_contextual = sum(contextual_values) / len(contextual_values)
    average_intrinsic = sum(intrinsic_values) / len(intrinsic_values)

    candidates: list[CryptidTargetExpectation] = []
    for index, card in enumerate(state.hand):
        if not target.can_use(ConsumableContext(state=state, cards=[card])):
            continue

        contextual_per_copy = (
            self.consumable_target_evaluator._card_build_value(profile_state, card, profile)
            - average_contextual
        )
        intrinsic_per_copy = (
            _intrinsic_with_permanent_chips(self.consumable_target_evaluator, card)
            - average_intrinsic
        )
        contextual_delta = 2.0 * contextual_per_copy
        intrinsic_delta = 2.0 * intrinsic_per_copy
        total_gain = contextual_delta + intrinsic_delta

        candidates.append(
            CryptidTargetExpectation(
                cards=(card,),
                target_index=index,
                total_gain=total_gain,
                contextual_delta=contextual_delta,
                intrinsic_delta=intrinsic_delta,
                owned_deck_size=len(owned_cards),
                rationale=(
                    f"owned deck source={source}",
                    f"owned deck size={len(owned_cards)}",
                    "Cryptid creates two exact public copies of the selected card",
                    f"two-copy contextual deck delta={contextual_delta:.3f}",
                    f"two-copy intrinsic/permanent-chip deck delta={intrinsic_delta:.3f}",
                ),
            )
        )

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda candidate: (candidate.total_gain, -candidate.target_index),
    )


def install_cryptid_pack_policy() -> None:
    if getattr(BalatroPackPolicy, "_cryptid_pack_policy_installed", False):
        return

    original_score_consumable = BalatroPackPolicy._score_consumable

    def score_consumable(self, state, action, choice):
        if not (choice.kind == "SPECTRAL" and choice.label == CRYPTID):
            return original_score_consumable(self, state, action, choice)

        target = self.consumable_factory.create(choice.data, live_id=choice.live_id)
        if target is None:
            return PackActionScore(action, -1.0, ("unresolved Cryptid",))

        expectation = _best_cryptid_target(self, state, target)
        if expectation is None or expectation.total_gain <= 0.0:
            return PackActionScore(
                action,
                -1.0,
                (
                    "Cryptid has no positive public owned-deck duplication target",
                    "opened-pack choice receives no generic shop/category utility",
                ),
            )

        targeted_action = type(action)(
            action.name,
            cards=list(expectation.cards),
            target=choice,
        )
        return PackActionScore(
            targeted_action,
            float(expectation.total_gain),
            (
                "Cryptid uses deterministic two-copy B6 deck-composition value",
                f"target_index={expectation.target_index}",
                *expectation.rationale,
            ),
        )

    BalatroPackPolicy._score_consumable = score_consumable
    BalatroPackPolicy.STOCHASTIC_MODELED_SPECTRALS = frozenset(
        set(BalatroPackPolicy.STOCHASTIC_MODELED_SPECTRALS) | {CRYPTID}
    )
    BalatroPackPolicy.DEFERRED_SPECTRALS = frozenset(
        set(BalatroPackPolicy.DEFERRED_SPECTRALS) - {CRYPTID}
    )
    BalatroPackPolicy._cryptid_pack_policy_installed = True
