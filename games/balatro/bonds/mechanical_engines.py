from __future__ import annotations

from typing import Any

from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank, BondRealization
from games.balatro.mechanics import (
    BLIND_SKIP_SCALING,
    BLIND_SKIP_TAG_GENERATION,
    CARD_DESTRUCTION,
    DISCARD_FACE_ECONOMY,
    DISCARD_HAND_LEVELING,
    DISCARD_JACK_SCALING,
    DISCARD_RANK_ECONOMY,
    DISCARD_SCALING,
    DISCARD_SUIT_SCALING,
    ENHANCEMENT_DENSITY_PAYOFF,
    ENHANCEMENT_GENERATION,
    FACE_DESTRUCTION_SCALING,
    GLOBAL_SELL_VALUE_GROWTH,
    GLASS_DESTRUCTION_SCALING,
    HAND_REPETITION_SCALING,
    HAND_REPETITION_XMULT,
    JOKER_FODDER_GENERATION,
    LEFT_JOKER_SACRIFICE,
    RANDOM_JOKER_SACRIFICE,
    SELF_SELL_VALUE_GROWTH,
    SELL_VALUE_SCORING,
    SPECTRAL_GENERATION,
    component_has_mechanic,
    components_have_mechanic,
)


DISCARD_THRESHOLDS = {
    BondRank.R1: 4.0, BondRank.R2: 9.0, BondRank.R3: 15.0,
    BondRank.R4: 22.0, BondRank.R5: 26.0,
}
BLIND_SKIP_THRESHOLDS = {
    BondRank.R1: 4.0, BondRank.R2: 8.0, BondRank.R3: 12.0,
    BondRank.R4: 15.0, BondRank.R5: 18.0,
}
SELL_VALUE_THRESHOLDS = {
    BondRank.R1: 4.0, BondRank.R2: 9.0, BondRank.R3: 15.0,
    BondRank.R4: 20.0, BondRank.R5: 25.0,
}
JOKER_SACRIFICE_THRESHOLDS = {
    BondRank.R1: 4.0, BondRank.R2: 9.0, BondRank.R3: 14.0,
    BondRank.R4: 18.0, BondRank.R5: 23.0,
}
CARD_DESTRUCTION_THRESHOLDS = {
    BondRank.R1: 4.0, BondRank.R2: 9.0, BondRank.R3: 15.0,
    BondRank.R4: 20.0, BondRank.R5: 26.0,
}
HAND_REPETITION_THRESHOLDS = {
    BondRank.R1: 4.0, BondRank.R2: 8.0, BondRank.R3: 13.0,
    BondRank.R4: 16.0, BondRank.R5: 20.0,
}
ENHANCED_CARDS_THRESHOLDS = {
    BondRank.R1: 4.0, BondRank.R2: 8.0, BondRank.R3: 13.0,
    BondRank.R4: 16.0, BondRank.R5: 20.0,
}


def _deck(state: Any) -> list[Any]:
    owned = getattr(state, "owned_deck", None)
    if owned is not None:
        return list(owned)
    return list(getattr(state, "deck", ()) or ())


def _band(value: int, bands: tuple[tuple[int, float], ...]) -> float:
    score = 0.0
    for threshold, candidate in bands:
        if value < threshold:
            break
        score = candidate
    return score


def _rank(total: float, thresholds: dict[BondRank, float]) -> tuple[BondRank, float | None]:
    rank = BondRank.R0
    for candidate in (BondRank.R1, BondRank.R2, BondRank.R3, BondRank.R4, BondRank.R5):
        threshold = thresholds[candidate]
        if total < threshold:
            return rank, threshold
        rank = candidate
    return BondRank.R5, None


def _finish(
    bond_id: str,
    parts: list[BondContribution],
    thresholds: dict[BondRank, float],
    *,
    unlocked: bool = True,
) -> BondDevelopment:
    total = sum(part.value for part in parts)
    rank, next_threshold = _rank(total, thresholds)
    if not unlocked:
        rank = BondRank.LOCKED
        next_threshold = thresholds[BondRank.R1]
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=unlocked,
        contribution=total if unlocked else 0.0,
        rank=rank,
        next_rank_threshold=next_threshold,
        contributions=tuple(parts) if unlocked else (),
        realization=BondRealization.DORMANT if rank in (BondRank.LOCKED, BondRank.R0) else BondRealization.PARTIAL,
    )


def _label(component: Any, fallback: str) -> str:
    name = getattr(component, "name", None)
    if name:
        return str(name)
    class_name = component.__class__.__name__
    return fallback if class_name in {"str", "SimpleNamespace"} else class_name


def _mechanic_parts(
    components: list[Any],
    specs: tuple[tuple[str, float, str], ...],
) -> list[BondContribution]:
    parts: list[BondContribution] = []
    for component in components:
        for mechanic, value, fallback in specs:
            if component_has_mechanic(component, mechanic):
                parts.append(BondContribution(_label(component, fallback), value))
                break
    return parts


def evaluate_discard_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    defining = (
        DISCARD_SCALING, DISCARD_SUIT_SCALING, DISCARD_RANK_ECONOMY,
        DISCARD_FACE_ECONOMY, DISCARD_JACK_SCALING,
    )
    if not any(components_have_mechanic(jokers, mechanic) for mechanic in defining):
        return _finish("discard", [], DISCARD_THRESHOLDS, unlocked=False)
    parts = _mechanic_parts(jokers, (
        (DISCARD_SCALING, 7.0, "Discard scaler"),
        (DISCARD_SUIT_SCALING, 5.0, "Discard suit scaler"),
        (DISCARD_RANK_ECONOMY, 4.0, "Discard rank economy"),
        (DISCARD_FACE_ECONOMY, 4.0, "Discard face economy"),
        (DISCARD_JACK_SCALING, 3.0, "Discard Jack scaler"),
        (DISCARD_HAND_LEVELING, 3.0, "Discard hand-level engine"),
    ))
    extra = max(0, int(getattr(state, "discards_per_round", 3) or 3) - 3)
    if extra:
        parts.append(BondContribution("Extra discard capacity", float(min(4, extra))))
    return _finish("discard", parts, DISCARD_THRESHOLDS)


def evaluate_blind_skip_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    if not components_have_mechanic(jokers, BLIND_SKIP_SCALING):
        return _finish("blind_skip", [], BLIND_SKIP_THRESHOLDS, unlocked=False)
    parts = _mechanic_parts(jokers, (
        (BLIND_SKIP_SCALING, 7.0, "Blind-skip scaler"),
        (BLIND_SKIP_TAG_GENERATION, 4.0, "Blind-skip tag source"),
    ))
    skipped = int(getattr(state, "blinds_skipped", 0) or 0)
    score = _band(skipped, ((1, 1.0), (3, 3.0), (5, 5.0), (8, 7.0)))
    if score:
        parts.append(BondContribution("Blind-skip history", score))
    return _finish("blind_skip", parts, BLIND_SKIP_THRESHOLDS)


def evaluate_sell_value_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    if not components_have_mechanic(jokers, SELL_VALUE_SCORING):
        return _finish("sell_value", [], SELL_VALUE_THRESHOLDS, unlocked=False)
    parts = _mechanic_parts(jokers, (
        (SELL_VALUE_SCORING, 7.0, "Sell-value scoring payoff"),
        (GLOBAL_SELL_VALUE_GROWTH, 6.0, "Global sell-value growth"),
        (SELF_SELL_VALUE_GROWTH, 5.0, "Self sell-value growth"),
    ))
    total_sell = int(getattr(state, "joker_sell_value_total", 0) or 0)
    score = _band(total_sell, ((10, 1.0), (20, 3.0), (35, 5.0), (60, 7.0)))
    if score:
        parts.append(BondContribution("Current Joker sell value", score))
    return _finish("sell_value", parts, SELL_VALUE_THRESHOLDS)


def evaluate_joker_sacrifice_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    if not (
        components_have_mechanic(jokers, LEFT_JOKER_SACRIFICE)
        or components_have_mechanic(jokers, RANDOM_JOKER_SACRIFICE)
    ):
        return _finish("joker_sacrifice", [], JOKER_SACRIFICE_THRESHOLDS, unlocked=False)
    parts = _mechanic_parts(jokers, (
        (LEFT_JOKER_SACRIFICE, 7.0, "Left-Joker sacrifice scaler"),
        (RANDOM_JOKER_SACRIFICE, 6.0, "Random-Joker sacrifice scaler"),
        (JOKER_FODDER_GENERATION, 3.0, "Joker fodder generation"),
    ))
    sacrificed = int(getattr(state, "jokers_destroyed", 0) or 0)
    score = _band(sacrificed, ((1, 1.0), (3, 3.0), (6, 5.0), (10, 7.0)))
    if score:
        parts.append(BondContribution("Destroyed Joker history", score))
    return _finish("joker_sacrifice", parts, JOKER_SACRIFICE_THRESHOLDS)


def evaluate_card_destruction_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    defining = any(
        components_have_mechanic(jokers, mechanic)
        for mechanic in (CARD_DESTRUCTION, FACE_DESTRUCTION_SCALING, GLASS_DESTRUCTION_SCALING)
    )
    if not defining:
        return _finish("card_destruction", [], CARD_DESTRUCTION_THRESHOLDS, unlocked=False)
    parts: list[BondContribution] = []
    for component in jokers:
        if component_has_mechanic(component, FACE_DESTRUCTION_SCALING):
            parts.append(BondContribution(_label(component, "Face-destruction scaler"), 7.0))
        elif component_has_mechanic(component, GLASS_DESTRUCTION_SCALING):
            parts.append(BondContribution(_label(component, "Glass-destruction scaler"), 3.0))
        elif component_has_mechanic(component, CARD_DESTRUCTION):
            value = 4.0 if component_has_mechanic(component, SPECTRAL_GENERATION) else 5.0
            parts.append(BondContribution(_label(component, "Card-destruction engine"), value))
    destroyed = int(getattr(state, "cards_destroyed", 0) or 0)
    score = _band(destroyed, ((2, 1.0), (5, 3.0), (10, 5.0), (16, 7.0)))
    if score:
        parts.append(BondContribution("Destroyed playing-card history", score))
    return _finish("card_destruction", parts, CARD_DESTRUCTION_THRESHOLDS)


def evaluate_hand_repetition_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    if not (
        components_have_mechanic(jokers, HAND_REPETITION_XMULT)
        or components_have_mechanic(jokers, HAND_REPETITION_SCALING)
    ):
        return _finish("hand_repetition", [], HAND_REPETITION_THRESHOLDS, unlocked=False)
    parts = _mechanic_parts(jokers, (
        (HAND_REPETITION_XMULT, 7.0, "Repeated-hand XMult"),
        (HAND_REPETITION_SCALING, 6.0, "Repeated-hand scaler"),
    ))
    counts = getattr(state, "hand_play_counts", {}) or {}
    most = max((int(value or 0) for value in counts.values()), default=0)
    score = _band(most, ((5, 1.0), (10, 3.0), (18, 5.0), (30, 7.0)))
    if score:
        parts.append(BondContribution("Repeated hand history", score))
    return _finish("hand_repetition", parts, HAND_REPETITION_THRESHOLDS)


def evaluate_enhanced_cards_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    if not components_have_mechanic(jokers, ENHANCEMENT_DENSITY_PAYOFF):
        return _finish("enhanced_cards", [], ENHANCED_CARDS_THRESHOLDS, unlocked=False)
    parts = _mechanic_parts(jokers, (
        (ENHANCEMENT_DENSITY_PAYOFF, 7.0, "Enhancement-density payoff"),
        (ENHANCEMENT_GENERATION, 3.0, "Enhancement generation"),
    ))
    enhanced = sum(
        1 for card in _deck(state)
        if str(getattr(card, "enhancement", "") or "").strip()
    )
    score = _band(enhanced, ((8, 1.0), (12, 3.0), (16, 5.0), (24, 7.0)))
    if score:
        parts.append(BondContribution("Enhanced-card density", score))
    return _finish("enhanced_cards", parts, ENHANCED_CARDS_THRESHOLDS)


MECHANICAL_ENGINE_EVALUATORS = {
    "discard": evaluate_discard_bond,
    "blind_skip": evaluate_blind_skip_bond,
    "sell_value": evaluate_sell_value_bond,
    "joker_sacrifice": evaluate_joker_sacrifice_bond,
    "card_destruction": evaluate_card_destruction_bond,
    "hand_repetition": evaluate_hand_repetition_bond,
    "enhanced_cards": evaluate_enhanced_cards_bond,
}
