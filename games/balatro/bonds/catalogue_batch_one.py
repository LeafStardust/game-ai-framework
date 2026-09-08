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


def _contains_named(values: Iterable[Any], *tokens: str) -> bool:
    normalized = {_name(value) for value in values}
    return any(any(token in candidate for candidate in normalized) for token in tokens)


def _owned_deck(state: Any) -> list[Any]:
    owned = getattr(state, "owned_deck", None)
    if owned is not None:
        return list(owned)
    return list(getattr(state, "deck", ()) or ())


def _band(count: int, bands: tuple[tuple[int, float], ...]) -> float:
    value = 0.0
    for threshold, score in bands:
        if count >= threshold:
            value = score
        else:
            break
    return value


def _rank(total: float, thresholds: dict[BondRank, float]) -> tuple[BondRank, float | None]:
    rank = BondRank.R0
    for candidate in (BondRank.R1, BondRank.R2, BondRank.R3, BondRank.R4, BondRank.R5):
        if total >= thresholds[candidate]:
            rank = candidate
        else:
            return rank, thresholds[candidate]
    return BondRank.R5, None


def _finish(
    bond_id: str,
    parts: list[BondContribution],
    thresholds: dict[BondRank, float],
    *,
    target: str | None = None,
) -> BondDevelopment:
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
        if _contains_named(jokers, *tokens):
            parts.append(BondContribution(label, value))
    return parts


def _hand_level(state: Any, hand: str) -> int:
    return int((getattr(state, "hand_levels", {}) or {}).get(hand, 1) or 1)


def _level_band(level: int) -> float:
    if level <= 1:
        return 0.0
    if level <= 3:
        return 1.0
    if level <= 6:
        return 3.0
    if level <= 10:
        return 5.0
    return 7.0


# ---------------------------------------------------------------------------
# 3. Held Retrigger
# ---------------------------------------------------------------------------
HELD_RETRIGGER_THRESHOLDS = {BondRank.R1: 4.0, BondRank.R2: 8.0, BondRank.R3: 13.0, BondRank.R4: 19.0, BondRank.R5: 26.0}
HELD_RETRIGGER_POLICIES = {
    BondRank.R1: ("recognize_held_retrigger_value",),
    BondRank.R2: ("prefer_retriggerable_held_effects", "protect_meaningful_retrigger_sources"),
    BondRank.R3: ("actively_pair_held_retrigger_with_held_payoffs",),
    BondRank.R4: ("eligible_as_power_engine_support", "seek_held_retrigger_motifs"),
    BondRank.R5: ("capstone_held_retrigger_commitment",),
}


def evaluate_held_retrigger_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    parts = _joker_parts(jokers, (("Mime", 6.0, ("mimejoker", "mime")),))
    deck = _owned_deck(state)
    red = sum(1 for c in deck if str(getattr(c, "seal", "") or "").lower() == "red")
    red_score = _band(red, ((1, 1.0), (2, 3.0), (4, 5.0), (6, 7.0)))
    if red_score:
        parts.append(BondContribution("Red Seal retrigger infrastructure", red_score))
    has_mime = _contains_named(jokers, "mimejoker", "mime")
    if has_mime and _contains_named(jokers, "blueprintjoker", "blueprint"):
        parts.append(BondContribution("Blueprint copying Mime potential", 4.0))
    if has_mime and _contains_named(jokers, "brainstormjoker", "brainstorm"):
        parts.append(BondContribution("Brainstorm copying Mime potential", 4.0))
    return _finish("held_retrigger", parts, HELD_RETRIGGER_THRESHOLDS)


# ---------------------------------------------------------------------------
# 4. Steel
# ---------------------------------------------------------------------------
STEEL_THRESHOLDS = {BondRank.R1: 4.0, BondRank.R2: 8.0, BondRank.R3: 14.0, BondRank.R4: 21.0, BondRank.R5: 29.0}
STEEL_POLICIES = {
    BondRank.R1: ("recognize_steel_held_xmult",),
    BondRank.R2: ("prefer_useful_steel_creation", "avoid_needlessly_playing_steel_cards"),
    BondRank.R3: ("actively_shape_deck_toward_steel_density",),
    BondRank.R4: ("eligible_as_power_engine", "strongly_value_held_retrigger_synergy"),
    BondRank.R5: ("capstone_steel_commitment",),
}


def evaluate_steel_bond(state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    parts = _joker_parts(jokers, (("Steel Joker", 5.0, ("steeljoker",)),))
    deck = _owned_deck(state)
    steel = [c for c in deck if str(getattr(c,"enhancement","") or "").lower()=="steel"]
    score = _band(len(steel), ((1,1.0),(2,3.0),(4,6.0),(6,9.0),(10,12.0)))
    if score: parts.append(BondContribution("Steel card density", score))
    red_steel=sum(1 for c in steel if str(getattr(c,"seal","") or "").lower()=="red")
    red_score=_band(red_steel,((1,1.0),(2,2.0),(4,3.0)))
    if red_score: parts.append(BondContribution("Red-Seal Steel overlap",red_score))
    return _finish("steel",parts,STEEL_THRESHOLDS)

PAIR_THRESHOLDS={BondRank.R1:4.0,BondRank.R2:8.0,BondRank.R3:13.0,BondRank.R4:19.0,BondRank.R5:26.0}
PAIR_POLICIES={BondRank.R1:("recognize_pair_specialization",),BondRank.R2:("prefer_pair_consistency_and_planets",),BondRank.R3:("actively_shape_scoring_around_pair",),BondRank.R4:("eligible_as_power_engine",),BondRank.R5:("capstone_pair_commitment",)}
def evaluate_pair_bond(state:Any)->BondDevelopment:
 jokers=list(getattr(state,"jokers",()) or ());parts=_joker_parts(jokers,(("The Duo",6.0,("theduojoker","theduo")),("Jolly Joker",4.0,("jollyjoker",)),("Sly Joker",4.0,("slyjoker",)),("Half Joker",2.0,("halfjoker",))))
 level_score=_level_band(_hand_level(state,"PAIR"));
 if level_score:parts.append(BondContribution("PAIR permanent hand level",level_score))
 return _finish("pair",parts,PAIR_THRESHOLDS,target="PAIR")

HIGH_CARD_THRESHOLDS=PAIR_THRESHOLDS
HIGH_CARD_POLICIES={BondRank.R1:("recognize_high_card_specialization",),BondRank.R2:("prefer_high_card_consistency_and_planets",),BondRank.R3:("actively_shape_scoring_around_high_card",),BondRank.R4:("eligible_as_power_engine",),BondRank.R5:("capstone_high_card_commitment",)}
def evaluate_high_card_bond(state:Any)->BondDevelopment:
 parts=_joker_parts(list(getattr(state,"jokers",()) or ()),(("Stuntman",6.0,("stuntmanjoker","stuntman")),("Half Joker",3.0,("halfjoker",))));score=_level_band(_hand_level(state,"HIGH_CARD"));
 if score:parts.append(BondContribution("HIGH_CARD permanent hand level",score))
 return _finish("high_card",parts,HIGH_CARD_THRESHOLDS,target="HIGH_CARD")

ACES_THRESHOLDS=PAIR_THRESHOLDS
ACES_POLICIES={BondRank.R1:("recognize_ace_payoff",),BondRank.R2:("prefer_ace_density_and_ace_scoring_support",),BondRank.R3:("actively_shape_deck_toward_aces",),BondRank.R4:("eligible_as_power_engine_support",),BondRank.R5:("capstone_ace_commitment",)}
def evaluate_aces_bond(state:Any)->BondDevelopment:
 jokers=list(getattr(state,"jokers",()) or ());parts=_joker_parts(jokers,(("Scholar",6.0,("scholarjoker","scholar")),("Fibonacci",3.0,("fibonaccijoker","fibonacci"))));deck=_owned_deck(state);aces=sum(1 for c in deck if str(getattr(c,"rank","") or "").upper()=="A");score=_band(aces,((4,1.0),(6,3.0),(8,5.0),(12,7.0)))
 if score:parts.append(BondContribution("Ace density",score))
 if aces>=6 and _contains_named(jokers,"dnajoker","dna"):parts.append(BondContribution("DNA Ace-duplication bridge",4.0))
 return _finish("aces",parts,ACES_THRESHOLDS,target="A")

NO_DISCARD_THRESHOLDS=PAIR_THRESHOLDS
NO_DISCARD_POLICIES={BondRank.R1:("recognize_no_discard_value",),BondRank.R2:("avoid_discarding_when_value_exceeds_hand_improvement",),BondRank.R3:("actively_build_around_zero_discard_execution",),BondRank.R4:("eligible_as_power_engine","strongly_preserve_no_discard_scalers"),BondRank.R5:("capstone_no_discard_commitment",)}
def evaluate_no_discard_bond(state:Any)->BondDevelopment:
 parts=_joker_parts(list(getattr(state,"jokers",()) or ()),(("Green Joker",6.0,("greenjoker",)),("Burglar",6.0,("burglarjoker","burglar")),("Delayed Gratification",4.0,("delayedgratificationjoker","delayedgratification")),("Ramen",4.0,("ramenjoker","ramen")),("Banner",2.0,("bannerjoker","banner"))));return _finish("no_discard",parts,NO_DISCARD_THRESHOLDS)

CASH_THRESHOLDS={BondRank.R1:4.0,BondRank.R2:9.0,BondRank.R3:15.0,BondRank.R4:22.0,BondRank.R5:30.0}
CASH_POLICIES={BondRank.R1:("recognize_cash_as_strategic_infrastructure",),BondRank.R2:("preserve_interest_and_cash_scaling_when_safe",),BondRank.R3:("actively_balance_spending_against_cash_engine_value",),BondRank.R4:("eligible_as_power_engine","protect_mature_cash_scoring"),BondRank.R5:("capstone_cash_commitment",)}
def evaluate_cash_bond(state:Any)->BondDevelopment:
 jokers=list(getattr(state,"jokers",()) or ());parts=_joker_parts(jokers,(("Bull",5.0,("bulljoker","bull")),("Bootstraps",5.0,("bootstrapsjoker","bootstraps")),("Rocket",4.0,("rocketjoker","rocket")),("Golden Joker",3.0,("goldenjoker",)),("To the Moon",3.0,("tothemoonjoker","tothemoon")),("Satellite",3.0,("satellitejoker","satellite")),("Reserved Parking",2.0,("reservedparkingjoker","reservedparking")),("Cloud 9",3.0,("cloud9joker","cloud9"))));money=int(getattr(state,"money",0) or 0);score=_band(money,((25,1.0),(50,3.0),(100,5.0),(150,7.0)))
 if score:parts.append(BondContribution("Current bankroll",score))
 return _finish("cash",parts,CASH_THRESHOLDS)

LUCKY_THRESHOLDS=PAIR_THRESHOLDS
LUCKY_POLICIES={BondRank.R1:("recognize_lucky_card_payoff",),BondRank.R2:("prefer_lucky_creation_and_trigger_support",),BondRank.R3:("actively_shape_deck_toward_lucky_density",),BondRank.R4:("eligible_as_power_engine_support",),BondRank.R5:("capstone_lucky_commitment",)}
def evaluate_lucky_bond(state:Any)->BondDevelopment:
 jokers=list(getattr(state,"jokers",()) or ());parts=_joker_parts(jokers,(("Lucky Cat",6.0,("luckycatjoker","luckycat")),("Oops! All 6s",4.0,("oopsall6sjoker","oopsall6s"))));deck=_owned_deck(state);n=sum(1 for c in deck if str(getattr(c,"enhancement","") or "").lower()=="lucky");score=_band(n,((1,1.0),(3,3.0),(6,5.0),(10,7.0)))
 if score:parts.append(BondContribution("Lucky card density",score))
 return _finish("lucky",parts,LUCKY_THRESHOLDS)

GLASS_THRESHOLDS=PAIR_THRESHOLDS
GLASS_POLICIES={BondRank.R1:("recognize_glass_xmult",),BondRank.R2:("prefer_safe_glass_creation_and_use",),BondRank.R3:("actively_shape_deck_around_glass_payoff",),BondRank.R4:("eligible_as_power_engine",),BondRank.R5:("capstone_glass_commitment",)}
def evaluate_glass_bond(state:Any)->BondDevelopment:
 jokers=list(getattr(state,"jokers",()) or ());parts=_joker_parts(jokers,(("Glass Joker",6.0,("glassjoker",)),));deck=_owned_deck(state);n=sum(1 for c in deck if str(getattr(c,"enhancement","") or "").lower()=="glass");score=_band(n,((1,1.0),(3,3.0),(6,5.0),(10,7.0)))
 if score:parts.append(BondContribution("Glass card density",score))
 destroyed=int(getattr(state,"glass_cards_destroyed",0) or 0)
 if _contains_named(jokers,"glassjoker") and destroyed>0:parts.append(BondContribution("Glass Joker accumulated destruction",_band(destroyed,((1,1.0),(3,2.0),(6,4.0),(10,6.0)))))
 return _finish("glass",parts,GLASS_THRESHOLDS)

FACE_CARDS_THRESHOLDS={BondRank.R1:4.0,BondRank.R2:9.0,BondRank.R3:15.0,BondRank.R4:22.0,BondRank.R5:30.0}
FACE_CARDS_POLICIES={BondRank.R1:("recognize_face_card_payoff",),BondRank.R2:("prefer_face_density_and_face_scoring_support",),BondRank.R3:("actively_shape_deck_toward_face_cards",),BondRank.R4:("eligible_as_power_engine","adapt_realization_against_face_debuff_bosses"),BondRank.R5:("capstone_face_card_commitment",)}
def evaluate_face_cards_bond(state:Any)->BondDevelopment:
 jokers=list(getattr(state,"jokers",()) or ());parts=_joker_parts(jokers,(("Pareidolia",6.0,("pareidoliajoker","pareidolia")),("Sock and Buskin",5.0,("sockandbuskinjoker","sockandbuskin")),("Photograph",4.0,("photographjoker","photograph")),("Scary Face",4.0,("scaryfacejoker","scaryface")),("Smiley Face",4.0,("smileyfacejoker","smileyface")),("Business Card",2.0,("businesscardjoker","businesscard"))));deck=_owned_deck(state);n=sum(1 for c in deck if str(getattr(c,"rank","") or "").upper() in {"J","Q","K"});score=_band(n,((12,1.0),(16,3.0),(20,5.0),(26,7.0)))
 if score:parts.append(BondContribution("Face-card density",score))
 return _finish("face_cards",parts,FACE_CARDS_THRESHOLDS,target="J/Q/K")

BATCH_ONE_EVALUATORS={"held_retrigger":evaluate_held_retrigger_bond,"steel":evaluate_steel_bond,"pair":evaluate_pair_bond,"high_card":evaluate_high_card_bond,"aces":evaluate_aces_bond,"no_discard":evaluate_no_discard_bond,"cash":evaluate_cash_bond,"lucky":evaluate_lucky_bond,"glass":evaluate_glass_bond,"face_cards":evaluate_face_cards_bond}
BOND_RELATIONSHIPS={frozenset(("burnt","no_discard")):"CONFLICT",frozenset(("held_cards","steel")):"SYNERGY"}
