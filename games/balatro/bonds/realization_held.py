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
def _debuffed(card):return bool(getattr(card,"debuffed",False) or getattr(card,"is_debuffed",False))
def _round_end(state):
 hands=getattr(state,"hands_left",None);return bool(getattr(state,"round_end_pending",False) or getattr(state,"last_hand_played",False) or (hands is not None and int(hands)==0))
def _development_floor(dev):return BondRealization.DORMANT if not dev.unlocked or dev.rank in (BondRank.LOCKED,BondRank.R0) else BondRealization.PARTIAL
def _mature_if_rank(dev,active,strong=False):
 if not active:return _development_floor(dev)
 return BondRealization.MATURE if strong and dev.rank>=BondRank.R4 else BondRealization.ACTIVE
def _held_effect_count(card,jokers,round_end=False):
 if _debuffed(card):return 0
 effects=0;enh=_enhancement(card)
 if round_end:
  if enh=="gold":effects+=1
  if _seal(card)=="blue":effects+=1
 else:
  if enh=="steel":effects+=1
  if not _stone(card) and _has(jokers,"baron") and _rank(card)=="K":effects+=1
  if not _stone(card) and _has(jokers,"shootthemoon") and _rank(card)=="Q":effects+=1
 return effects
def _raised_fist_target(hand,jokers):
 if not _has(jokers,"raisedfist"):return None
 values={"2":2,"3":3,"4":4,"5":5,"6":6,"7":7,"8":8,"9":9,"10":10,"T":10,"J":10,"Q":10,"K":10,"A":11};ranked=[(values[_rank(c)],i) for i,c in enumerate(hand) if not _stone(c) and _rank(c) in values]
 if not ranked:return None
 low=min(v for v,_ in ranked);return max(i for v,i in ranked if v==low)
def _blackboard_card_ok(card):
 if _stone(card):return False
 if not _debuffed(card) and _enhancement(card)=="wild":return True
 return _suit(card) in {"spades","clubs"}
def realize_held_cards(dev,state):
 dev=enrich_development(dev)
 if _development_floor(dev)==BondRealization.DORMANT:return replace(dev,realization=BondRealization.DORMANT)
 hand=_cards(state,"hand","current_hand","cards_in_hand");j=_jokers(state);kh=sum(1 for c in hand if not _debuffed(c) and not _stone(c) and _rank(c)=="K");qh=sum(1 for c in hand if not _debuffed(c) and not _stone(c) and _rank(c)=="Q");steel=sum(1 for c in hand if not _debuffed(c) and _enhancement(c)=="steel");black=all(_blackboard_card_ok(c) for c in hand);fist=_raised_fist_target(hand,j);fist_live=fist is not None and not _debuffed(hand[fist]);src=sum((_has(j,"baron") and kh>0,_has(j,"shootthemoon") and qh>0,_has(j,"raisedfist") and fist_live,_has(j,"blackboard") and black,steel>0));strong=src>=2 or kh+qh+steel>=3;return replace(dev,realization=_mature_if_rank(dev,src>0,strong))
def realize_held_retrigger(dev,state):
 dev=enrich_development(dev)
 if _development_floor(dev)==BondRealization.DORMANT:return replace(dev,realization=BondRealization.DORMANT)
 hand=_cards(state,"hand","current_hand","cards_in_hand");j=_jokers(state)
 if not hand:return replace(dev,realization=BondRealization.PARTIAL)
 end=_round_end(state);fist=None if end else _raised_fist_target(hand,j);effect=sum(1 for i,c in enumerate(hand) if _held_effect_count(c,j,end)>0 or (i==fist and not _debuffed(c)));mime=_has(j,"mime");red=sum(1 for i,c in enumerate(hand) if not _debuffed(c) and _seal(c)=="red" and (_held_effect_count(c,j,end)>0 or (i==fist and not _debuffed(c))));src=int(mime and effect>0)+red;strong=src>=2 or (mime and red>=1) or red>=2;return replace(dev,realization=_mature_if_rank(dev,src>0,strong))
def realize_steel(dev,state):
 dev=enrich_development(dev)
 if _development_floor(dev)==BondRealization.DORMANT:return replace(dev,realization=BondRealization.DORMANT)
 hand=_cards(state,"hand","current_hand","cards_in_hand")
 if not hand:return replace(dev,realization=BondRealization.PARTIAL)
 n=sum(1 for c in hand if not _debuffed(c) and _enhancement(c)=="steel");mime=_has(_jokers(state),"mime");return replace(dev,realization=_mature_if_rank(dev,n>0,n>=3 or (n>=2 and mime)))
def realize_rank_payoff(dev,state,rank,*,held_tokens=(),scored_tokens=()):
 dev=enrich_development(dev)
 if _development_floor(dev)==BondRealization.DORMANT:return replace(dev,realization=BondRealization.DORMANT)
 j=_jokers(state);hand=_cards(state,"hand","current_hand","cards_in_hand");sc=_cards(state,"scoring_cards","played_cards","current_played_cards");hc=sum(1 for c in hand if not _debuffed(c) and not _stone(c) and _rank(c)==rank);pc=sum(1 for c in sc if not _debuffed(c) and not _stone(c) and _rank(c)==rank);hl=bool(held_tokens) and _has(j,*held_tokens) and hc>0;pl=bool(scored_tokens) and _has(j,*scored_tokens) and pc>0;return replace(dev,realization=_mature_if_rank(dev,hl or pl,(hl and hc>=3) or (pl and pc>=3) or (hl and pl)))
def realize_kings(dev,state):return realize_rank_payoff(dev,state,"K",held_tokens=("baron",),scored_tokens=("triboulet",))
def realize_queens(dev,state):return realize_rank_payoff(dev,state,"Q",held_tokens=("shootthemoon",),scored_tokens=("triboulet",))
HELD_REALIZERS={"held_cards":realize_held_cards,"held_retrigger":realize_held_retrigger,"steel":realize_steel,"kings":realize_kings,"queens":realize_queens}
def realize_held_family(dev,state):
 fn=HELD_REALIZERS.get(dev.bond_id);return enrich_development(dev) if fn is None else fn(dev,state)