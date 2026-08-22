from __future__ import annotations
from collections import Counter
from dataclasses import replace
from itertools import combinations
from typing import Any,Iterable
from games.balatro.bonds.mechanical_roles import enrich_development
from games.balatro.bonds.model import BondDevelopment,BondRank,BondRealization

def _floor(dev):return BondRealization.DORMANT if not dev.unlocked or dev.rank in (BondRank.LOCKED,BondRank.R0) else BondRealization.PARTIAL
def _cards(state):
 for name in ("hand","current_hand","cards_in_hand"):
  value=getattr(state,name,None)
  if value is not None:return list(value or ())
 return []
def _name(value):
 raw=value if isinstance(value,str) else getattr(value,"name",None) or value.__class__.__name__;return "".join(ch for ch in str(raw).lower() if ch.isalnum())
def _has(values,*tokens):
 names={_name(v) for v in values};return any(any(t in n for n in names) for t in tokens)
def _rank(c):return str(getattr(c,"rank","") or "").upper()
def _suit(c):return str(getattr(c,"suit","") or "").lower()
def _enh(c):return str(getattr(c,"enhancement","") or "").lower()
def _stone(c):return _enh(c)=="stone" or bool(getattr(c,"is_stone",False))
def _explicit_type(state):
 raw=getattr(state,"current_hand_type",None) or getattr(state,"best_hand_type","");return str(raw or "").upper().replace(" ","_")
def _finish(dev,active,strong=False):
 dev=enrich_development(dev)
 if _floor(dev)==BondRealization.DORMANT:return replace(dev,realization=BondRealization.DORMANT)
 if not active:return replace(dev,realization=BondRealization.PARTIAL)
 return replace(dev,realization=BondRealization.MATURE if strong and dev.rank>=BondRank.R4 else BondRealization.ACTIVE)
def _counts(hand):
 out={}
 for c in hand:
  if _stone(c):continue
  r=_rank(c)
  if r:out[r]=out.get(r,0)+1
 return out
def _effective_suits(c,smeared):
 if _enh(c)=="wild":return ("red","black") if smeared else ("hearts","diamonds","spades","clubs")
 s=_suit(c)
 if not smeared:return (s,) if s else ()
 if s in {"hearts","diamonds"}:return ("red",)
 if s in {"spades","clubs"}:return ("black",)
 return (s,) if s else ()
def _flush_available(hand,needed,smeared):
 counts=Counter()
 for c in hand:
  if not _stone(c):
   for s in _effective_suits(c,smeared):counts[s]+=1
 return any(v>=needed for v in counts.values())
def _straight_available(ranks,needed,shortcut):
 ranks=set(ranks)
 if 14 in ranks:ranks.add(1)
 vals=sorted(ranks);gapmax=2 if shortcut else 1
 if len(vals)<needed:return False
 for start in range(len(vals)):
  length=1;prev=vals[start]
  for value in vals[start+1:]:
   gap=value-prev
   if gap<=0:continue
   if gap>gapmax:break
   length+=1;prev=value
   if length>=needed:return True
 return False
def _rank_values(hand):
 m={"A":14,"K":13,"Q":12,"J":11,"10":10,"T":10,"9":9,"8":8,"7":7,"6":6,"5":5,"4":4,"3":3,"2":2};return {m[_rank(c)] for c in hand if _rank(c) in m}
def realize_full_house(dev,state):
 if _explicit_type(state)=="FULL_HOUSE":return _finish(dev,True,True)
 vals=sorted(_counts(_cards(state)).values(),reverse=True);a=len(vals)>=2 and vals[0]>=3 and vals[1]>=2;return _finish(dev,a,a)
def realize_straight_flush(dev,state):
 if _explicit_type(state)=="STRAIGHT_FLUSH":return _finish(dev,True,True)
 hand=[c for c in _cards(state) if not _stone(c)];j=list(getattr(state,"jokers",()) or ());ff=_has(j,"fourfingers");shortcut=_has(j,"shortcut");sm=_has(j,"smearedjoker","smeared")
 if ff:
  # Four Fingers may use different 4-card subsets for Straight and Flush, but
  # their union still has to fit inside one legal hand of at most five cards.
  candidates=[hand] if len(hand)<=5 else combinations(hand,5);a=any(_straight_available(_rank_values(c),4,shortcut) and _flush_available(c,4,sm) for c in candidates)
 else:
  suits={}
  for c in hand:
   r=next(iter(_rank_values([c])),None)
   if r is None:continue
   for s in _effective_suits(c,sm):suits.setdefault(s,set()).add(r)
  a=any(_straight_available(rs,5,shortcut) for rs in suits.values())
 return _finish(dev,a,a)
def realize_five_kind(dev,state):
 if _explicit_type(state)=="FIVE_OF_A_KIND":return _finish(dev,True,True)
 a=max(_counts(_cards(state)).values(),default=0)>=5;return _finish(dev,a,a)
def _five_card_candidates(hand):return combinations(hand,5) if len(hand)>=5 else ()
def realize_flush_house(dev,state):
 if _explicit_type(state)=="FLUSH_HOUSE":return _finish(dev,True,True)
 hand=[c for c in _cards(state) if not _stone(c)];j=list(getattr(state,"jokers",()) or ());ff=_has(j,"fourfingers");sm=_has(j,"smearedjoker","smeared");needed=4 if ff else 5;a=False
 for five in _five_card_candidates(hand):
  vals=sorted(_counts(five).values(),reverse=True)
  if len(vals)>=2 and vals[0]>=3 and vals[1]>=2 and _flush_available(five,needed,sm):a=True;break
 return _finish(dev,a,a)
def realize_flush_five(dev,state):
 if _explicit_type(state)=="FLUSH_FIVE":return _finish(dev,True,True)
 hand=[c for c in _cards(state) if not _stone(c)];j=list(getattr(state,"jokers",()) or ());ff=_has(j,"fourfingers");sm=_has(j,"smearedjoker","smeared");needed=4 if ff else 5;a=False
 for five in _five_card_candidates(hand):
  if max(_counts(five).values(),default=0)>=5 and _flush_available(five,needed,sm):a=True;break
 return _finish(dev,a,a)
ADVANCED_REALIZERS={"full_house":realize_full_house,"straight_flush":realize_straight_flush,"five_kind":realize_five_kind,"flush_house":realize_flush_house,"flush_five":realize_flush_five}
def realize_advanced_family(dev,state):
 fn=ADVANCED_REALIZERS.get(dev.bond_id);return enrich_development(dev) if fn is None else fn(dev,state)
