from __future__ import annotations
from dataclasses import replace
from typing import Any, Iterable
from games.balatro.bonds.mechanical_roles import enrich_development
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization

def _cards(state: Any,*names:str)->list[Any]:
 for name in names:
  value=getattr(state,name,None)
  if value is not None:return list(value or ())
 return []
def _jokers(state):return list(getattr(state,"jokers",()) or ())
def _name(value):
 raw=value if isinstance(value,str) else getattr(value,"name",None) or value.__class__.__name__;return "".join(ch for ch in str(raw).lower() if ch.isalnum())
def _has(values,*tokens):
 names={_name(v) for v in values};return any(any(token in name for name in names) for token in tokens)
def _rank(card):return str(getattr(card,"rank","") or "").upper()
def _suit(card):return str(getattr(card,"suit","") or "").lower()
def _enhancement(card):return str(getattr(card,"enhancement","") or "").lower()
def _seal(card):return str(getattr(card,"seal","") or "").lower()
def _stone(card):return _enhancement(card)=="stone" or bool(getattr(card,"is_stone",False))
def _development_floor(dev):return BondRealization.DORMANT if not dev.unlocked or dev.rank in (BondRank.LOCKED,BondRank.R0) else BondRealization.PARTIAL
def _mature_if_rank(dev,active,strong=False):
 if not active:return _development_floor(dev)
 return BondRealization.MATURE if strong and dev.rank>=BondRank.R4 else BondRealization.ACTIVE
def _held_effect_count(card,jokers):
 effects=0;enh=_enhancement(card)
 if enh in {"steel","gold"}:effects+=1
 if not _stone(card) and _has(jokers,"baron") and _rank(card)=="K":effects+=1
 if not _stone(card) and _has(jokers,"shootthemoon") and _rank(card)=="Q":effects+=1
 return effects
def _raised_fist_target(hand,jokers):
 if not _has(jokers,"raisedfist"):return None
 values={"2":2,"3":3,"4":4,"5":5,"6":6,"7":7,"8":8,"9":9,"10":10,"T":10,"J":10,"Q":10,"K":10,"A":11};ranked=[(values[_rank(c)],i) for i,c in enumerate(hand) if not _stone(c) and _rank(c) in values]
 if not ranked:return None
 low=min(v for v,_ in ranked);return max(i for v,i in ranked if v==low)
def realize_held_cards(dev,state):
 dev=enrich_development(dev)
 if _development_floor(dev)==BondRealization.DORMANT:return replace(dev,realization=BondRealization.DORMANT)
 hand=_cards(state,"hand","current_hand","cards_in_hand");j=_jokers(state);kh=sum(1 for c in hand if not _stone(c) and _rank(c)=="K");qh=sum(1 for c in hand if not _stone(c) and _rank(c)=="Q");steel=sum(1 for c in hand if _enhancement(c)=="steel");black=all(not _stone(c) and (_suit(c) in {"spades","clubs"} or _enhancement(c)=="wild") for c in hand);src=sum((_has(j,"baron") and kh>0,_has(j,"shootthemoon") and qh>0,_has(j,"raisedfist") and _raised_fist_target(hand,j) is not None,_has(j,"blackboard") and black,steel>0));strong=src>=2 or kh+qh+steel>=3;return replace(dev,realization=_mature_if_rank(dev,src>0,strong))
def realize_held_retrigger(dev,state):
 dev=enrich_development(dev)
 if _development_floor(dev)==BondRealization.DORMANT:return replace(dev,realization=BondRealization.DORMANT)
 hand=_cards(state,"hand","current_hand","cards_in_hand");j=_jokers(state)
 if not hand:return replace(dev,realization=BondRealization.PARTIAL)
 fist=_raised_fist_target(hand,j);effect=sum(1 for i,c in enumerate(hand) if _held_effect_count(c,j)>0 or i==fist);mime=_has(j,"mime");red=sum(1 for i,c in enumerate(hand) if _seal(c)=="red" and (_held_effect_count(c,j)>0 or i==fist));src=int(mime and effect>0)+red;strong=src>=2 or (mime and red>=1) or red>=2;return replace(dev,realization=_mature_if_rank(dev,src>0,strong))
def realize_steel(dev,state):
 dev=enrich_development(dev)
 if _development_floor(dev)==BondRealization.DORMANT:return replace(dev,realization=BondRealization.DORMANT)
 hand=_cards(state,"hand","current_hand","cards_in_hand")
 if not hand:return replace(dev,realization=BondRealization.PARTIAL)
 n=sum(1 for c in hand if _enhancement(c)=="steel");mime=_has(_jokers(state),"mime");return replace(dev,realization=_mature_if_rank(dev,n>0,n>=3 or (n>=2 and mime)))
def realize_rank_payoff(dev,state,rank,*,held_tokens=(),scored_tokens=()):
 dev=enrich_development(dev)
 if _development_floor(dev)==BondRealization.DORMANT:return replace(dev,realization=BondRealization.DORMANT)
 j=_jokers(state);hand=_cards(state,"hand","current_hand","cards_in_hand");sc=_cards(state,"scoring_cards","played_cards","current_played_cards");hc=sum(1 for c in hand if not _stone(c) and _rank(c)==rank);pc=sum(1 for c in sc if not _stone(c) and _rank(c)==rank);hl=bool(held_tokens) and _has(j,*held_tokens) and hc>0;pl=bool(scored_tokens) and _has(j,*scored_tokens) and pc>0;return replace(dev,realization=_mature_if_rank(dev,hl or pl,(hl and hc>=3) or (pl and pc>=3) or (hl and pl)))
def realize_kings(dev,state):return realize_rank_payoff(dev,state,"K",held_tokens=("baron",),scored_tokens=("triboulet",))
def realize_queens(dev,state):return realize_rank_payoff(dev,state,"Q",held_tokens=("shootthemoon",),scored_tokens=("triboulet",))
HELD_REALIZERS={"held_cards":realize_held_cards,"held_retrigger":realize_held_retrigger,"steel":realize_steel,"kings":realize_kings,"queens":realize_queens}
def realize_held_family(dev,state):
 fn=HELD_REALIZERS.get(dev.bond_id);return enrich_development(dev) if fn is None else fn(dev,state)