from __future__ import annotations

from typing import Any, Iterable

from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank, BondRealization


def _name(value: Any) -> str:
    if isinstance(value, str):
        raw = value
    else:
        raw = getattr(value, "name", None)
        if raw is None:
            raw = value.__class__.__name__
    return "".join(ch for ch in str(raw).lower() if ch.isalnum())


def _contains(values: Iterable[Any], *tokens: str) -> bool:
    names = {_name(v) for v in values}
    return any(any(token in name for name in names) for token in tokens)


def _deck(state: Any) -> list[Any]:
    owned = getattr(state, "owned_deck", None)
    if owned is not None:
        return list(owned)
    return list(getattr(state, "deck", ()) or ())


def _band(value: int, bands: tuple[tuple[int, float], ...]) -> float:
    out = 0.0
    for threshold, score in bands:
        if value >= threshold:
            out = score
        else:
            break
    return out


DEFAULT_THRESHOLDS = {
    BondRank.R1: 4.0,
    BondRank.R2: 9.0,
    BondRank.R3: 15.0,
    BondRank.R4: 22.0,
    BondRank.R5: 30.0,
}


def _rank(total: float, thresholds: dict[BondRank, float]) -> tuple[BondRank, float | None]:
    rank = BondRank.R0
    for candidate in (BondRank.R1, BondRank.R2, BondRank.R3, BondRank.R4, BondRank.R5):
        if total >= thresholds[candidate]:
            rank = candidate
        else:
            return rank, thresholds[candidate]
    return BondRank.R5, None


def _finish(bond_id: str, parts: list[BondContribution], thresholds: dict[BondRank, float] = DEFAULT_THRESHOLDS) -> BondDevelopment:
    total = sum(part.value for part in parts)
    rank, nxt = _rank(total, thresholds)
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=True,
        contribution=total,
        rank=rank,
        next_rank_threshold=nxt,
        contributions=tuple(parts),
        realization=BondRealization.DORMANT if rank == BondRank.R0 else BondRealization.PARTIAL,
    )


def _locked(bond_id: str, threshold: float = 4.0) -> BondDevelopment:
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=False,
        contribution=0.0,
        rank=BondRank.LOCKED,
        next_rank_threshold=threshold,
        contributions=(),
        realization=BondRealization.DORMANT,
    )


def _joker_parts(jokers: list[Any], specs: tuple[tuple[str, float, tuple[str, ...]], ...]) -> list[BondContribution]:
    parts: list[BondContribution] = []
    for label, value, tokens in specs:
        if _contains(jokers, *tokens):
            parts.append(BondContribution(label, value))
    return parts


# Discard: generic discard capacity/history is support, not an unlock. Burnt can
# deepen this Bond but Burnt alone remains its own defining strategy.
DISCARD_THRESHOLDS = DEFAULT_THRESHOLDS
DISCARD_POLICIES = {
    BondRank.R1: ("recognize_discard_as_engine_resource",),
    BondRank.R2: ("prefer_high_value_discard_lines",),
    BondRank.R3: ("actively_shape_play_around_discard_payoffs",),
    BondRank.R4: ("eligible_as_power_engine_support",),
    BondRank.R5: ("capstone_discard_commitment",),
}

def evaluate_discard_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    if not _contains(jokers, "yorick", "castle", "mailinrebate", "facelessjoker", "hittheroad"):
        return _locked("discard")
    parts = _joker_parts(jokers, (
        ("Yorick", 7.0, ("yorick",)),
        ("Castle", 5.0, ("castle",)),
        ("Mail-In Rebate", 4.0, ("mailinrebate",)),
        ("Faceless Joker", 4.0, ("facelessjoker",)),
        ("Hit the Road", 3.0, ("hittheroad",)),
        ("Burnt Joker", 3.0, ("burntjoker",)),
    ))
    discards = int(getattr(state, "discards_per_round", 3) or 3)
    extra = max(0, discards - 3)
    if extra:
        parts.append(BondContribution("Extra discard capacity", float(min(4, extra))))
    return _finish("discard", parts, DISCARD_THRESHOLDS)


# Blind Skip: Throwback is the defining persistent payoff. Diet Cola/history
# deepen a Throwback plan but do not independently create one. The capped
# contributor economy tops out at 18 (Throwback 7 + Diet Cola 4 + history 7), so
# the upper ranks sit on the final real history milestones rather than unreachable
# generic thresholds.
BLIND_SKIP_THRESHOLDS = {
    BondRank.R1: 4.0,
    BondRank.R2: 9.0,
    BondRank.R3: 15.0,
    BondRank.R4: 16.0,
    BondRank.R5: 18.0,
}
BLIND_SKIP_POLICIES = {
    BondRank.R1: ("recognize_skip_payoff",),
    BondRank.R2: ("prefer_high_value_tags_when_runway_allows",),
    BondRank.R3: ("actively_balance_skip_scaling_against_shop_loss",),
    BondRank.R4: ("eligible_as_scaling_support_engine",),
    BondRank.R5: ("capstone_skip_commitment",),
}

def evaluate_blind_skip_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    if not _contains(jokers, "throwback"):
        return _locked("blind_skip")
    parts = _joker_parts(jokers, (
        ("Throwback", 7.0, ("throwback",)),
        ("Diet Cola", 4.0, ("dietcola",)),
    ))
    skipped = int(getattr(state, "blinds_skipped", 0) or 0)
    score = _band(skipped, ((1, 1.0), (3, 3.0), (5, 5.0), (8, 7.0)))
    if score:
        parts.append(BondContribution("Blind-skip history", score))
    return _finish("blind_skip", parts, BLIND_SKIP_THRESHOLDS)


# Sell Value: Swashbuckler is the defining payoff. Egg/Gift Card are economy
# components unless Swashbuckler converts their sell value into scoring. Maximum
# modeled contribution is 25, so R5 is the literal full-payoff capstone.
SELL_VALUE_THRESHOLDS = {
    BondRank.R1: 4.0,
    BondRank.R2: 9.0,
    BondRank.R3: 15.0,
    BondRank.R4: 22.0,
    BondRank.R5: 25.0,
}
SELL_VALUE_POLICIES = {
    BondRank.R1: ("recognize_sell_value_as_scoring_resource",),
    BondRank.R2: ("prefer_sell_value_growth_when_payoff_exists",),
    BondRank.R3: ("actively_preserve_and_convert_sell_value",),
    BondRank.R4: ("eligible_as_scoring_engine",),
    BondRank.R5: ("capstone_sell_value_commitment",),
}

def evaluate_sell_value_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    if not _contains(jokers, "swashbuckler"):
        return _locked("sell_value")
    parts = _joker_parts(jokers, (
        ("Swashbuckler", 7.0, ("swashbuckler",)),
        ("Gift Card", 6.0, ("giftcard",)),
        ("Egg", 5.0, ("eggjoker", "egg")),
    ))
    total_sell = int(getattr(state, "joker_sell_value_total", 0) or 0)
    score = _band(total_sell, ((10, 1.0), (20, 3.0), (35, 5.0), (60, 7.0)))
    if score:
        parts.append(BondContribution("Current Joker sell value", score))
    return _finish("sell_value", parts, SELL_VALUE_THRESHOLDS)


# Joker Sacrifice: Dagger or Madness must currently exist. Historical sacrifice
# without a surviving payoff is not a current Bond. Maximum modeled contribution
# is 23, so the existing reachable R4 is retained and R5 moves to that capstone.
JOKER_SACRIFICE_THRESHOLDS = {
    BondRank.R1: 4.0,
    BondRank.R2: 9.0,
    BondRank.R3: 15.0,
    BondRank.R4: 22.0,
    BondRank.R5: 23.0,
}
JOKER_SACRIFICE_POLICIES = {
    BondRank.R1: ("recognize_joker_sacrifice_value",),
    BondRank.R2: ("prefer_safe_fodder_when_scaler_requires_it",),
    BondRank.R3: ("actively_manage_slots_for_sacrifice_scaling",),
    BondRank.R4: ("eligible_as_power_engine",),
    BondRank.R5: ("capstone_sacrifice_commitment",),
}

def evaluate_joker_sacrifice_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    if not _contains(jokers, "ceremonialdagger", "madness"):
        return _locked("joker_sacrifice")
    parts = _joker_parts(jokers, (
        ("Ceremonial Dagger", 7.0, ("ceremonialdagger",)),
        ("Madness", 6.0, ("madness",)),
        ("Riff-Raff", 3.0, ("riffraff",)),
    ))
    sacrificed = int(getattr(state, "jokers_destroyed", 0) or 0)
    score = _band(sacrificed, ((1, 1.0), (3, 3.0), (6, 5.0), (10, 7.0)))
    if score:
        parts.append(BondContribution("Destroyed Joker history", score))
    return _finish("joker_sacrifice", parts, JOKER_SACRIFICE_THRESHOLDS)


# Card Destruction: current destruction engine/payoff required. Permanent deck
# reduction after the engine disappears belongs to Deck Thinning instead. Maximum
# modeled contribution is 26, so the existing reachable R4 is retained and R5 is
# the full engine/history capstone.
CARD_DESTRUCTION_THRESHOLDS = {
    BondRank.R1: 4.0,
    BondRank.R2: 9.0,
    BondRank.R3: 15.0,
    BondRank.R4: 22.0,
    BondRank.R5: 26.0,
}
CARD_DESTRUCTION_POLICIES = {
    BondRank.R1: ("recognize_card_destruction_payoff",),
    BondRank.R2: ("prefer_targeted_destruction_of_low_value_cards",),
    BondRank.R3: ("actively_shape_deck_through_destruction",),
    BondRank.R4: ("eligible_as_scaling_or_concentration_engine",),
    BondRank.R5: ("capstone_card_destruction_commitment",),
}

def evaluate_card_destruction_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    if not _contains(jokers, "canio", "tradingcard", "sixthsense", "glassjoker"):
        return _locked("card_destruction")
    parts = _joker_parts(jokers, (
        ("Canio", 7.0, ("canio",)),
        ("Trading Card", 5.0, ("tradingcard",)),
        ("Sixth Sense", 4.0, ("sixthsense",)),
        ("Glass Joker", 3.0, ("glassjoker",)),
    ))
    destroyed = int(getattr(state, "cards_destroyed", 0) or 0)
    score = _band(destroyed, ((2, 1.0), (5, 3.0), (10, 5.0), (16, 7.0)))
    if score:
        parts.append(BondContribution("Destroyed playing-card history", score))
    return _finish("card_destruction", parts, CARD_DESTRUCTION_THRESHOLDS)


# Hand Repetition: repeated play history is evidence only after Card Sharp or
# Supernova gives repetition independent strategic meaning. The modeled economy
# tops out at 20, with the last two history milestones producing 18 and 20.
HAND_REPETITION_THRESHOLDS = {
    BondRank.R1: 4.0,
    BondRank.R2: 9.0,
    BondRank.R3: 15.0,
    BondRank.R4: 18.0,
    BondRank.R5: 20.0,
}
HAND_REPETITION_POLICIES = {
    BondRank.R1: ("recognize_repeated_hand_payoff",),
    BondRank.R2: ("prefer_consistent_repetition_of_selected_hand",),
    BondRank.R3: ("actively_shape_run_around_repeated_hand_use",),
    BondRank.R4: ("eligible_as_power_engine_support",),
    BondRank.R5: ("capstone_hand_repetition_commitment",),
}

def evaluate_hand_repetition_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    if not _contains(jokers, "cardsharp", "supernova"):
        return _locked("hand_repetition")
    parts = _joker_parts(jokers, (
        ("Card Sharp", 7.0, ("cardsharp",)),
        ("Supernova", 6.0, ("supernova",)),
    ))
    counts = getattr(state, "hand_play_counts", {}) or {}
    most = max((int(v or 0) for v in counts.values()), default=0)
    score = _band(most, ((5, 1.0), (10, 3.0), (18, 5.0), (30, 7.0)))
    if score:
        parts.append(BondContribution("Repeated hand history", score))
    return _finish("hand_repetition", parts, HAND_REPETITION_THRESHOLDS)


# Enhanced Cards survives audit only as a Driver's License defining-payoff Bond.
# Generic enhancement density without Driver's License belongs to the specific
# enhancement/deck-shaping Bonds and ordinary card valuation. Driver's License,
# both modeled feed engines and the final density milestones top out at 20.
ENHANCED_CARDS_THRESHOLDS = {
    BondRank.R1: 4.0,
    BondRank.R2: 9.0,
    BondRank.R3: 15.0,
    BondRank.R4: 18.0,
    BondRank.R5: 20.0,
}
ENHANCED_CARDS_POLICIES = {
    BondRank.R1: ("recognize_drivers_license_payoff",),
    BondRank.R2: ("prefer_high_quality_enhancement_creation",),
    BondRank.R3: ("actively_shape_deck_toward_license_threshold",),
    BondRank.R4: ("eligible_as_xmult_engine",),
    BondRank.R5: ("capstone_enhancement_commitment",),
}

def evaluate_enhanced_cards_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    if not _contains(jokers, "driverslicense"):
        return _locked("enhanced_cards")
    parts = _joker_parts(jokers, (
        ("Driver's License", 7.0, ("driverslicense",)),
        ("Midas Mask", 3.0, ("midasmask",)),
        ("Marble Joker", 3.0, ("marblejoker",)),
    ))
    enhanced = sum(1 for card in _deck(state) if str(getattr(card, "enhancement", "") or "").strip())
    score = _band(enhanced, ((8, 1.0), (12, 3.0), (16, 5.0), (24, 7.0)))
    if score:
        parts.append(BondContribution("Enhanced-card density", score))
    return _finish("enhanced_cards", parts, ENHANCED_CARDS_THRESHOLDS)


BATCH_FIVE_EVALUATORS = {
    "discard": evaluate_discard_bond,
    "blind_skip": evaluate_blind_skip_bond,
    "sell_value": evaluate_sell_value_bond,
    "joker_sacrifice": evaluate_joker_sacrifice_bond,
    "card_destruction": evaluate_card_destruction_bond,
    "hand_repetition": evaluate_hand_repetition_bond,
    "enhanced_cards": evaluate_enhanced_cards_bond,
}

BATCH_FIVE_RELATIONSHIPS = {
    frozenset(("discard", "no_discard")): "CONFLICT",
    frozenset(("discard", "burnt")): "SYNERGY",
    frozenset(("card_destruction", "deck_thinning")): "SYNERGY",
}
