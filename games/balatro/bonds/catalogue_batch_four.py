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


def _rank(total: float, thresholds: dict[BondRank, float]) -> tuple[BondRank, float | None]:
    rank = BondRank.R0
    for candidate in (BondRank.R1, BondRank.R2, BondRank.R3, BondRank.R4, BondRank.R5):
        if total >= thresholds[candidate]:
            rank = candidate
        else:
            return rank, thresholds[candidate]
    return BondRank.R5, None


def _finish(bond_id: str, parts: list[BondContribution], thresholds: dict[BondRank, float], *, target: str | None = None) -> BondDevelopment:
    total = sum(part.value for part in parts)
    rank, next_threshold = _rank(total, thresholds)
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=True,
        contribution=total,
        rank=rank,
        next_rank_threshold=next_threshold,
        contributions=tuple(parts),
        target=target,
        realization=BondRealization.DORMANT if rank == BondRank.R0 else BondRealization.PARTIAL,
    )


def _joker_parts(jokers: list[Any], specs: tuple[tuple[str, float, tuple[str, ...]], ...]) -> list[BondContribution]:
    parts: list[BondContribution] = []
    for label, value, tokens in specs:
        if _contains(jokers, *tokens):
            parts.append(BondContribution(label, value))
    return parts


RANK_THRESHOLDS = {BondRank.R1: 4.0, BondRank.R2: 9.0, BondRank.R3: 15.0, BondRank.R4: 22.0, BondRank.R5: 30.0}
ENHANCEMENT_THRESHOLDS = {BondRank.R1: 4.0, BondRank.R2: 8.0, BondRank.R3: 13.0, BondRank.R4: 19.0, BondRank.R5: 26.0}
CONSUMABLE_THRESHOLDS = {BondRank.R1: 4.0, BondRank.R2: 9.0, BondRank.R3: 15.0, BondRank.R4: 22.0, BondRank.R5: 30.0}


def _rank_density(state: Any, ranks: set[str]) -> float:
    count = sum(1 for card in _deck(state) if str(getattr(card, "rank", "") or "").upper() in ranks)
    return _band(count, ((4, 1.0), (6, 3.0), (9, 5.0), (13, 7.0), (18, 9.0)))


def _rank_bond(state: Any, bond_id: str, ranks: set[str], specs: tuple[tuple[str, float, tuple[str, ...]], ...]) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    parts = _joker_parts(jokers, specs)
    density = _rank_density(state, ranks)
    if density:
        parts.append(BondContribution(f"{bond_id} rank density", density))
    return _finish(bond_id, parts, RANK_THRESHOLDS, target="/".join(sorted(ranks)))


def _enhancement_bond(state: Any, bond_id: str, enhancement: str, specs: tuple[tuple[str, float, tuple[str, ...]], ...]) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    parts = _joker_parts(jokers, specs)
    count = sum(1 for card in _deck(state) if str(getattr(card, "enhancement", "") or "").lower() == enhancement.lower())
    density = _band(count, ((1, 1.0), (3, 3.0), (6, 5.0), (10, 7.0)))
    if density:
        parts.append(BondContribution(f"{enhancement} card density", density))
    return _finish(bond_id, parts, ENHANCEMENT_THRESHOLDS)


# 33. Kings
KINGS_THRESHOLDS = RANK_THRESHOLDS
KINGS_POLICIES = {
    BondRank.R1: ("recognize_king_payoff",),
    BondRank.R2: ("prefer_king_density_and_preservation",),
    BondRank.R3: ("actively_shape_deck_toward_kings",),
    BondRank.R4: ("eligible_as_power_engine_support",),
    BondRank.R5: ("capstone_king_commitment",),
}

def evaluate_kings_bond(state: Any) -> BondDevelopment:
    return _rank_bond(state, "kings", {"K"}, (
        ("Baron", 7.0, ("baronjoker", "baron")),
        ("Triboulet", 6.0, ("triboulet",)),
    ))


# 34. Queens
QUEENS_THRESHOLDS = RANK_THRESHOLDS
QUEENS_POLICIES = {
    BondRank.R1: ("recognize_queen_payoff",),
    BondRank.R2: ("prefer_queen_density_and_preservation",),
    BondRank.R3: ("actively_shape_deck_toward_queens",),
    BondRank.R4: ("eligible_as_power_engine_support",),
    BondRank.R5: ("capstone_queen_commitment",),
}

def evaluate_queens_bond(state: Any) -> BondDevelopment:
    return _rank_bond(state, "queens", {"Q"}, (
        ("Shoot the Moon", 6.0, ("shootthemoon",)),
        ("Triboulet", 5.0, ("triboulet",)),
    ))


# 35. Jacks
JACKS_THRESHOLDS = RANK_THRESHOLDS
JACKS_POLICIES = {
    BondRank.R1: ("recognize_jack_payoff",),
    BondRank.R2: ("prefer_jack_density_when_supported",),
    BondRank.R3: ("actively_shape_deck_toward_jacks",),
    BondRank.R4: ("eligible_as_power_engine_support",),
    BondRank.R5: ("capstone_jack_commitment",),
}

def evaluate_jacks_bond(state: Any) -> BondDevelopment:
    return _rank_bond(state, "jacks", {"J"}, (
        ("Hit the Road", 7.0, ("hittheroad",)),
    ))


# 36. Tens
TENS_THRESHOLDS = RANK_THRESHOLDS
TENS_POLICIES = {
    BondRank.R1: ("recognize_ten_payoff",),
    BondRank.R2: ("prefer_ten_density_when_supported",),
    BondRank.R3: ("actively_shape_deck_toward_tens",),
    BondRank.R4: ("eligible_as_power_engine_support",),
    BondRank.R5: ("capstone_ten_commitment",),
}

def evaluate_tens_bond(state: Any) -> BondDevelopment:
    return _rank_bond(state, "tens", {"10"}, (
        ("Walkie Talkie", 3.0, ("walkietalkie",)),
    ))


# 37. Wild Cards
WILD_THRESHOLDS = ENHANCEMENT_THRESHOLDS
WILD_POLICIES = {
    BondRank.R1: ("recognize_wild_card_flexibility",),
    BondRank.R2: ("prefer_wild_creation_when_suit_flexibility_matters",),
    BondRank.R3: ("actively_use_wild_density_to_support_suit_plans",),
    BondRank.R4: ("eligible_as_multi_suit_support_engine",),
    BondRank.R5: ("capstone_wild_commitment",),
}

def evaluate_wild_bond(state: Any) -> BondDevelopment:
    return _enhancement_bond(state, "wild", "Wild", (
        ("Flower Pot", 3.0, ("flowerpot",)),
    ))


# 38. Mult Cards
MULT_CARDS_THRESHOLDS = ENHANCEMENT_THRESHOLDS
MULT_CARDS_POLICIES = {
    BondRank.R1: ("recognize_mult_card_value",),
    BondRank.R2: ("prefer_mult_card_creation_when_scoring_needs_flat_mult",),
    BondRank.R3: ("actively_shape_scoring_cards_around_mult_enhancements",),
    BondRank.R4: ("eligible_as_scoring_support_engine",),
    BondRank.R5: ("capstone_mult_card_commitment",),
}

def evaluate_mult_cards_bond(state: Any) -> BondDevelopment:
    return _enhancement_bond(state, "mult_cards", "Mult", (
        ("Vampire", 2.0, ("vampire",)),
    ))


# 39. Bonus Cards
BONUS_CARDS_THRESHOLDS = ENHANCEMENT_THRESHOLDS
BONUS_CARDS_POLICIES = {
    BondRank.R1: ("recognize_bonus_card_chip_value",),
    BondRank.R2: ("prefer_bonus_creation_when_chip_scaling_matters",),
    BondRank.R3: ("actively_shape_scoring_cards_around_bonus_enhancements",),
    BondRank.R4: ("eligible_as_chip_support_engine",),
    BondRank.R5: ("capstone_bonus_card_commitment",),
}

def evaluate_bonus_cards_bond(state: Any) -> BondDevelopment:
    return _enhancement_bond(state, "bonus_cards", "Bonus", ())


# 40. Tarot
TAROT_THRESHOLDS = CONSUMABLE_THRESHOLDS
TAROT_POLICIES = {
    BondRank.R1: ("recognize_tarot_generation_and_use",),
    BondRank.R2: ("prefer_tarot_access_when_deck_shaping_is_useful",),
    BondRank.R3: ("actively_use_tarots_to_shape_combined_build",),
    BondRank.R4: ("eligible_as_deck_shaping_resource_engine",),
    BondRank.R5: ("capstone_tarot_infrastructure",),
}

def evaluate_tarot_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    vouchers = list(getattr(state, "vouchers", ()) or ())
    parts = _joker_parts(jokers, (
        ("Cartomancer", 6.0, ("cartomancer",)),
        ("Vagabond", 5.0, ("vagabond",)),
        ("Hallucination", 4.0, ("hallucination",)),
        ("Fortune Teller", 4.0, ("fortuneteller",)),
    ))
    if _contains(vouchers, "tarotmerchant"):
        parts.append(BondContribution("Tarot Merchant", 4.0))
    if _contains(vouchers, "tarottycoon"):
        parts.append(BondContribution("Tarot Tycoon", 6.0))
    return _finish("tarot", parts, TAROT_THRESHOLDS)


# 41. Planet
PLANET_THRESHOLDS = CONSUMABLE_THRESHOLDS
PLANET_POLICIES = {
    BondRank.R1: ("recognize_planet_generation_and_hand_leveling",),
    BondRank.R2: ("prefer_planet_access_for_relevant_hand_bonds",),
    BondRank.R3: ("actively_reinforce_selected_hand_specialization",),
    BondRank.R4: ("eligible_as_hand_level_resource_engine",),
    BondRank.R5: ("capstone_planet_infrastructure",),
}

def evaluate_planet_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    vouchers = list(getattr(state, "vouchers", ()) or ())
    parts = _joker_parts(jokers, (
        ("Constellation", 6.0, ("constellation",)),
        ("Astronomer", 4.0, ("astronomer",)),
        ("Space Joker", 3.0, ("spacejoker",)),
    ))
    if _contains(vouchers, "telescope"):
        parts.append(BondContribution("Telescope", 5.0))
    if _contains(vouchers, "planetmerchant"):
        parts.append(BondContribution("Planet Merchant", 4.0))
    if _contains(vouchers, "planettycoon"):
        parts.append(BondContribution("Planet Tycoon", 6.0))
    blue = sum(1 for card in _deck(state) if str(getattr(card, "seal", "") or "").lower() == "blue")
    blue_score = _band(blue, ((1, 1.0), (2, 3.0), (4, 5.0), (7, 7.0)))
    if blue_score:
        parts.append(BondContribution("Blue Seal Planet infrastructure", blue_score))
    return _finish("planet", parts, PLANET_THRESHOLDS)


# 42. Spectral
SPECTRAL_THRESHOLDS = CONSUMABLE_THRESHOLDS
SPECTRAL_POLICIES = {
    BondRank.R1: ("recognize_spectral_generation_and_transform_value",),
    BondRank.R2: ("prefer_spectral_access_when_transformations_fit_build",),
    BondRank.R3: ("actively_use_spectrals_for_high_impact_structure",),
    BondRank.R4: ("eligible_as_transformation_resource_engine",),
    BondRank.R5: ("capstone_spectral_infrastructure",),
}

def evaluate_spectral_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    parts = _joker_parts(jokers, (
        ("Sixth Sense", 6.0, ("sixthsense",)),
        ("Seance", 6.0, ("seance",)),
    ))
    return _finish("spectral", parts, SPECTRAL_THRESHOLDS)


BATCH_FOUR_EVALUATORS = {
    "kings": evaluate_kings_bond,
    "queens": evaluate_queens_bond,
    "jacks": evaluate_jacks_bond,
    "tens": evaluate_tens_bond,
    "wild": evaluate_wild_bond,
    "mult_cards": evaluate_mult_cards_bond,
    "bonus_cards": evaluate_bonus_cards_bond,
    "tarot": evaluate_tarot_bond,
    "planet": evaluate_planet_bond,
    "spectral": evaluate_spectral_bond,
}
