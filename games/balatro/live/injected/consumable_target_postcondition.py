from __future__ import annotations

import copy
from dataclasses import dataclass

from games.balatro.build import ContextualConsumableTargetEvaluator
from games.balatro.consumable import ConsumableContext
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator


CardSignature = tuple[str, str, str | None, str | None, str | None]
ExpectedTarget = tuple[int | str, CardSignature | None]


@dataclass(frozen=True)
class ConsumableTargetPostcondition:
    """Expected semantic result for exact live hand-card targets."""

    expected_targets: tuple[ExpectedTarget, ...]

    @property
    def live_ids(self) -> tuple[int | str, ...]:
        return tuple(live_id for live_id, _ in self.expected_targets)

    def matches(self, snapshot: LiveBalatroSnapshot) -> bool:
        hand_by_live_id = {
            card.get("live_id"): card
            for card in _area_cards(snapshot, "hand")
            if card.get("live_id") is not None
        }

        for live_id, expected_signature in self.expected_targets:
            record = hand_by_live_id.get(live_id)
            if expected_signature is None:
                if record is not None:
                    return False
                continue
            if record is None or _snapshot_card_signature(record) != expected_signature:
                return False
        return True


def build_consumable_target_postcondition(
    state,
    *,
    consumable_index: int,
    target_indices: tuple[int, ...],
) -> ConsumableTargetPostcondition | None:
    """Simulate a modeled deterministic target and derive its live postcondition."""

    if not target_indices:
        return None

    consumables = list(getattr(state, "consumables", ()))
    hand = list(getattr(state, "hand", ()))
    if not (0 <= consumable_index < len(consumables)):
        return None
    if any(index < 0 or index >= len(hand) for index in target_indices):
        return None

    evaluator = ContextualConsumableTargetEvaluator()
    consumable = consumables[consumable_index]
    if not evaluator.supports(consumable):
        return None

    live_ids = tuple(getattr(hand[index], "live_id", None) for index in target_indices)
    if any(live_id is None for live_id in live_ids):
        raise ValueError(
            "modeled targeted consumable verification requires live_id on every target"
        )
    if len(set(live_ids)) != len(live_ids):
        raise ValueError("modeled targeted consumable verification requires unique live_ids")

    simulated = copy.deepcopy(state)
    simulated_consumable = simulated.consumables[consumable_index]
    simulated_cards = [simulated.hand[index] for index in target_indices]
    context = ConsumableContext(state=simulated, cards=simulated_cards)
    if not simulated_consumable.can_use(context):
        raise ValueError(
            "modeled targeted consumable failed can_use during verification simulation"
        )

    simulated_consumable.use(context)
    post_hand_by_live_id = {
        getattr(card, "live_id", None): card
        for card in getattr(simulated, "hand", ())
        if getattr(card, "live_id", None) is not None
    }

    expected: list[ExpectedTarget] = []
    for live_id in live_ids:
        card = post_hand_by_live_id.get(live_id)
        expected.append(
            (
                live_id,
                _model_card_signature(card) if card is not None else None,
            )
        )
    return ConsumableTargetPostcondition(tuple(expected))


def _area_cards(snapshot: LiveBalatroSnapshot, name: str) -> list[dict]:
    area = snapshot.payload.get(name)
    if not isinstance(area, dict):
        return []
    cards = area.get("cards")
    if not isinstance(cards, list):
        return []
    return [card for card in cards if isinstance(card, dict)]


def _model_card_signature(card) -> CardSignature:
    return (
        str(card.rank),
        str(card.suit),
        getattr(card, "enhancement", None),
        getattr(card, "edition", None),
        getattr(card, "seal", None),
    )


def _snapshot_card_signature(card: dict) -> CardSignature | None:
    value = card.get("value") or card
    modifier = card.get("modifier") or card
    if not isinstance(value, dict) or not isinstance(modifier, dict):
        return None

    rank = value.get("rank")
    suit = value.get("suit")
    if rank is None or suit is None:
        return None

    rank_text = str(rank)
    suit_text = str(suit)
    enhancement = modifier.get("enhancement")
    edition = modifier.get("edition")
    seal = modifier.get("seal")

    return (
        DefaultBalatroStateTranslator.RANKS.get(rank_text, rank_text),
        DefaultBalatroStateTranslator.SUITS.get(suit_text, suit_text),
        DefaultBalatroStateTranslator.ENHANCEMENTS.get(enhancement, enhancement),
        DefaultBalatroStateTranslator.EDITIONS.get(edition, edition),
        DefaultBalatroStateTranslator.SEALS.get(seal, seal),
    )
