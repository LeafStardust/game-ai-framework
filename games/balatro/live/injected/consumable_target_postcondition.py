from __future__ import annotations

import copy
from dataclasses import dataclass

from games.balatro.build import ContextualConsumableTargetEvaluator
from games.balatro.consumable import ConsumableContext
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator


CardSignature = tuple[str, str, str | None, str | None, str | None]
ExpectedTarget = tuple[int | str, CardSignature | None]
ExpectedEditionTarget = tuple[int | str, CardSignature, tuple[str, ...]]
ExpectedHandLevel = tuple[str, int]


@dataclass(frozen=True)
class ConsumableTargetPostcondition:
    """Expected semantic result for a modeled consumable use."""

    expected_targets: tuple[ExpectedTarget, ...] = ()
    expected_edition_targets: tuple[ExpectedEditionTarget, ...] = ()
    expected_hand_level: ExpectedHandLevel | None = None

    @property
    def live_ids(self) -> tuple[int | str, ...]:
        exact = tuple(live_id for live_id, _ in self.expected_targets)
        edition = tuple(
            live_id for live_id, _, _ in self.expected_edition_targets
        )
        return (*exact, *edition)

    def matches(self, snapshot: LiveBalatroSnapshot) -> bool:
        cards_by_live_id = {
            card.get("live_id"): card
            for card in _target_card_records(snapshot)
            if card.get("live_id") is not None
        }

        for live_id, expected_signature in self.expected_targets:
            record = cards_by_live_id.get(live_id)
            if expected_signature is None:
                if record is not None:
                    return False
                continue
            if record is None or _snapshot_card_signature(record) != expected_signature:
                return False

        for live_id, before_signature, allowed_editions in self.expected_edition_targets:
            record = cards_by_live_id.get(live_id)
            if record is None:
                return False
            signature = _snapshot_card_signature(record)
            if signature is None:
                return False
            if (
                signature[0] != before_signature[0]
                or signature[1] != before_signature[1]
                or signature[2] != before_signature[2]
                or signature[4] != before_signature[4]
                or signature[3] not in allowed_editions
            ):
                return False

        if self.expected_hand_level is not None:
            hand_type, expected_level = self.expected_hand_level
            if _snapshot_hand_level(snapshot, hand_type) != expected_level:
                return False

        return True


def build_consumable_target_postcondition(
    state,
    *,
    consumable_index: int,
    target_indices: tuple[int, ...],
) -> ConsumableTargetPostcondition | None:
    """Simulate a modeled held selection and derive its live postcondition."""

    consumables = list(getattr(state, "consumables", ()))
    if not (0 <= consumable_index < len(consumables)):
        return None
    return build_consumable_target_postcondition_for_consumable(
        state,
        consumable=consumables[consumable_index],
        target_indices=target_indices,
    )


def build_consumable_target_postcondition_for_consumable(
    state,
    *,
    consumable,
    target_indices: tuple[int, ...],
) -> ConsumableTargetPostcondition | None:
    """Derive the same semantic postcondition for held or pack consumables."""

    category = str(getattr(consumable, "category", "")).upper()
    name = str(getattr(consumable, "name", ""))
    if category == "PLANET":
        if target_indices:
            raise ValueError("modeled Planet verification does not accept hand targets")
        return _build_planet_hand_level_postcondition(state, consumable)

    if not target_indices:
        return None

    hand = list(getattr(state, "hand", ()))
    if any(index < 0 or index >= len(hand) for index in target_indices):
        return None

    if category == "SPECTRAL" and name == "Aura":
        return _build_aura_edition_postcondition(
            state,
            consumable,
            target_indices=target_indices,
        )

    evaluator = ContextualConsumableTargetEvaluator()
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
    simulated_consumable = copy.deepcopy(consumable)
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


def _build_aura_edition_postcondition(
    state,
    consumable,
    *,
    target_indices: tuple[int, ...],
) -> ConsumableTargetPostcondition | None:
    if len(target_indices) != 1:
        raise ValueError("modeled Aura verification requires exactly one hand target")

    hand = list(getattr(state, "hand", ()))
    index = target_indices[0]
    card = hand[index]
    live_id = getattr(card, "live_id", None)
    if live_id is None:
        raise ValueError("modeled Aura verification requires live_id on its target")
    if getattr(card, "edition", None) not in (None, ""):
        return None

    context = ConsumableContext(state=state, cards=[card])
    if not consumable.can_use(context):
        raise ValueError("modeled Aura failed can_use during verification")

    return ConsumableTargetPostcondition(
        expected_edition_targets=(
            (
                live_id,
                _model_card_signature(card),
                ("Foil", "Holographic", "Polychrome"),
            ),
        )
    )


def _build_planet_hand_level_postcondition(
    state,
    consumable,
) -> ConsumableTargetPostcondition | None:
    hand_type = str(getattr(consumable, "hand_type", ""))
    if not hand_type:
        return None

    hand_levels = getattr(state, "hand_levels", None)
    if not isinstance(hand_levels, dict) or hand_type not in hand_levels:
        return None

    simulated = copy.deepcopy(state)
    simulated_consumable = copy.deepcopy(consumable)
    context = ConsumableContext(state=simulated)
    if not simulated_consumable.can_use(context):
        raise ValueError(
            "modeled Planet failed can_use during verification simulation"
        )

    before_level = int(simulated.hand_levels[hand_type])
    simulated_consumable.use(context)
    after_level = int(simulated.hand_levels.get(hand_type, before_level))
    if after_level <= before_level:
        raise ValueError(
            "modeled Planet verification requires a positive hand-level transition"
        )

    return ConsumableTargetPostcondition(
        expected_hand_level=(hand_type, after_level),
    )


def _area_cards(snapshot: LiveBalatroSnapshot, name: str) -> list[dict]:
    area = snapshot.payload.get(name)
    if not isinstance(area, dict):
        return []
    cards = area.get("cards")
    if not isinstance(cards, list):
        return []
    return [card for card in cards if isinstance(card, dict)]


def _target_card_records(snapshot: LiveBalatroSnapshot) -> list[dict]:
    if "owned_cards" in snapshot.payload:
        return _area_cards(snapshot, "owned_cards")
    if "owned_deck" in snapshot.payload:
        return _area_cards(snapshot, "owned_deck")
    return _area_cards(snapshot, "hand")


def _snapshot_hand_level(
    snapshot: LiveBalatroSnapshot,
    hand_type: str,
) -> int | None:
    hands = snapshot.payload.get("hands")
    if not isinstance(hands, dict):
        return None

    keys = [hand_type]
    keys.extend(
        display_name
        for display_name, normalized in DefaultBalatroStateTranslator.HAND_NAMES.items()
        if normalized == hand_type
    )

    for key in keys:
        value = hands.get(key)
        if isinstance(value, dict):
            level = value.get("level")
        else:
            level = value
        if isinstance(level, bool) or not isinstance(level, (int, float)):
            continue
        return int(level)
    return None


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
