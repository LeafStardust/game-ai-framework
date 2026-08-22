from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable

from games.balatro.bonds.mechanical_roles import enrich_development
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization


def _cards(state: Any, *names: str) -> list[Any]:
    for name in names:
        value = getattr(state, name, None)
        if value is not None:return list(value or ())
    return []
def _jokers(state: Any)->list[Any]:return list(getattr(state,"jokers",()) or ())
def _name(value:Any)->str:
    raw=value if isinstance(value,str) else getattr(value,"name",None) or value.__class__.__name__;return "".join(ch for ch in str(raw).lower() if ch.isalnum())
def _has(values:Iterable[Any],*tokens:str)->bool:
    names={_name(v) for v in values};return any(any(token in name for name in names) for token in tokens)
def _rank(card:Any)->str:return str(getattr(card,"rank","") or "").upper()
def _suit(card:Any)->str:return str(getattr(card,"suit","") or "").lower()
def _enhancement(card:Any)->str:return str(getattr(card,"enhancement","") or "").lower()
def _seal(card:Any)->str:return str(getattr(card,"seal","") or "").lower()
def _stone(card:Any)->bool:return _enhancement(card)=="stone" or bool(getattr(card,"is_stone",False))
def _development_floor(dev):
    if not dev.unlocked or dev.rank in (BondRank.LOCKED,BondRank.R0):return BondRealization.DORMANT
    return BondRealization.PARTIAL
def _mature_if_rank(dev,active,strong=False):
    if not active:return _development_floor(dev)
    if strong and dev.rank>=BondRank.R4:return BondRealization.MATURE
    return BondRealization.ACTIVE
def _held_effect_count(card,jokers):
    effects=0;enh=_enhancement(card)
    # Stone replaces the card enhancement, so a Stone card cannot simultaneously
    # be Steel/Gold. Seals remain valid on Stone cards and still retrigger.
    if enh in {"steel","gold"}:effects+=1
    if _seal(card)=="blue":effects+=1
    if not _stone(card) and _has(jokers,"baron") and _rank(card)=="K":effects+=1
    if not _stone(card) and _has(jokers,"shootthemoon") and _rank(card)=="Q":effects+=1
    return effects
def _raised_fist_target(hand,jokers):
    if not _has(jokers,"raisedfist"):return None
    values={"2":2,"3":3,"4":4,"5":5,"6":6,"7":7,"8":8,"9":9,"10":10,"T":10,"J":10,"Q":10,"K":10,"A":11}
    ranked=[(values[_rank(card)],index) for index,card in enumerate(hand) if not _stone(card) and _rank(card) in values]
    if not ranked:return None
    lowest=min(value for value,_ in ranked);return max(index for value,index in ranked if value==lowest)
def realize_held_cards(dev,state):
    dev=enrich_development(dev)
    if _development_floor(dev)==BondRealization.DORMANT:return replace(dev,realization=BondRealization.DORMANT)
    hand=_cards(state,"hand","current_hand","cards_in_hand");jokers=_jokers(state);has_baron=_has(jokers,"baron");has_stm=_has(jokers,"shootthemoon");has_fist=_has(jokers,"raisedfist");has_blackboard=_has(jokers,"blackboard")
    king_hits=sum(1 for c in hand if not _stone(c) and _rank(c)=="K");queen_hits=sum(1 for c in hand if not _stone(c) and _rank(c)=="Q");steel_hits=sum(1 for c in hand if _enhancement(c)=="steel")
    # Stone cards have no suit and therefore prevent Blackboard while held.
    blackboard_ok=all(not _stone(c) and (_suit(c) in {"spades","clubs"} or _enhancement(c)=="wild") for c in hand)
    active_sources=0
    if has_baron and king_hits:active_sources+=1
    if has_stm and queen_hits:active_sources+=1
    if has_fist and _raised_fist_target(hand,jokers) is not None:active_sources+=1
    if has_blackboard and blackboard_ok:active_sources+=1
    if steel_hits:active_sources+=1
    strong=active_sources>=2 or king_hits+queen_hits+steel_hits>=3;return replace(dev,realization=_mature_if_rank(dev,active_sources>0,strong))
def realize_held_retrigger(dev,state):
    dev=enrich_development(dev)
    if _development_floor(dev)==BondRealization.DORMANT:return replace(dev,realization=BondRealization.DORMANT)
    hand=_cards(state,"hand","current_hand","cards_in_hand");jokers=_jokers(state)
    if not hand:return replace(dev,realization=BondRealization.PARTIAL)
    fist_target=_raised_fist_target(hand,jokers);held_effect_cards=sum(1 for index,card in enumerate(hand) if _held_effect_count(card,jokers)>0 or index==fist_target);mime=_has(jokers,"mime");red_held=sum(1 for index,card in enumerate(hand) if _seal(card)=="red" and (_held_effect_count(card,jokers)>0 or index==fist_target));active_sources=int(mime and held_effect_cards>0)+red_held;strong=active_sources>=2 or (mime and red_held>=1) or red_held>=2;return replace(dev,realization=_mature_if_rank(dev,active_sources>0,strong))
def realize_steel(dev,state):
    dev=enrich_development(dev)
    if _development_floor(dev)==BondRealization.DORMANT:return replace(dev,realization=BondRealization.DORMANT)
    hand=_cards(state,"hand","current_hand","cards_in_hand")
    if not hand:return replace(dev,realization=BondRealization.PARTIAL)
    held_steel=sum(1 for c in hand if _enhancement(c)=="steel");mime=_has(_jokers(state),"mime");strong=held_steel>=3 or (held_steel>=2 and mime);return replace(dev,realization=_mature_if_rank(dev,held_steel>0,strong))
def realize_rank_payoff(dev,state,rank,*,held_tokens=(),scored_tokens=()):
    dev=enrich_development(dev)
    if _development_floor(dev)==BondRealization.DORMANT:return replace(dev,realization=BondRealization.DORMANT)
    jokers=_jokers(state);hand=_cards(state,"hand","current_hand","cards_in_hand");scoring=_cards(state,"scoring_cards","played_cards","current_played_cards");held_count=sum(1 for c in hand if not _stone(c) and _rank(c)==rank);scored_count=sum(1 for c in scoring if not _stone(c) and _rank(c)==rank);held_live=bool(held_tokens) and _has(jokers,*held_tokens) and held_count>0;scored_live=bool(scored_tokens) and _has(jokers,*scored_tokens) and scored_count>0;active=held_live or scored_live;strong=(held_live and held_count>=3) or (scored_live and scored_count>=3) or (held_live and scored_live);return replace(dev,realization=_mature_if_rank(dev,active,strong))
def realize_kings(dev,state):return realize_rank_payoff(dev,state,"K",held_tokens=("baron",),scored_tokens=("triboulet",))
def realize_queens(dev,state):return realize_rank_payoff(dev,state,"Q",held_tokens=("shootthemoon",),scored_tokens=("triboulet",))
HELD_REALIZERS={"held_cards":realize_held_cards,"held_retrigger":realize_held_retrigger,"steel":realize_steel,"kings":realize_kings,"queens":realize_queens}
def realize_held_family(dev,state):
    fn=HELD_REALIZERS.get(dev.bond_id);return enrich_development(dev) if fn is None else fn(dev,state)
