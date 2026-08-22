from __future__ import annotations
from collections import Counter
from dataclasses import replace
from typing import Any,Iterable
from games.balatro.bonds.mechanical_roles import enrich_development
from games.balatro.bonds.model import BondDevelopment,BondRank,BondRealization

def _cards(state,*names):
 for n in names:
  v=getattr(state,n,None)
  if v is not None:return list(v or ())
 return []
def _deck(state):
 v=getattr(state,"owned_deck",None);return list(v or ()) if v is not None else list(getattr(state,"deck",()) or ())
def _name(v):
 raw=v if isinstance(v,str) else getattr(v,"name",None) or v.__class__.__name__;return "".join(c for c in str(raw).lower() if c.isalnum())
def _has(vals,*ts):
 ns={_name(v) for v in vals};return any(any(t in n for n in ns) for t in ts)
def _rank(c):return str(getattr(c,"rank","") or "").upper()
def _suit(c):return str(getattr(c,"suit","") or "").lower()
def _enh(c):return str(getattr(c,"enhancement","") or "").lower()
def _seal(c):return str(getattr(c,"seal","") or "").lower()
def _stone(c):return bool(getattr(c,"is_stone",False)) or _enh(c)=="stone"
def _debuffed(c):return bool(getattr(c,"debuffed",False) or getattr(c,"is_debuffed",False))
def _floor(d):return BondRealization.DORMANT if not d.unlocked or d.rank in (BondRank.LOCKED,BondRank.R0) else BondRealization.PARTIAL
def _finish(d,*,active,strong=False):return replace(d,realization=_floor(d) if not active else BondRealization.MATURE if strong and d.rank>=BondRank.R4 else BondRealization.ACTIVE)
def _known(s):
 for n in ("current_hand_type","best_hand_type","selected_hand_type","hand_type"):
  v=getattr(s,n,None)
  if v:return str(v).upper().replace(" ","_")
 return ""
def _straight(nums,needed,shortcut):
 seq=set(nums);seq.add(1) if 14 in seq else None;vals=sorted(seq);gapmax=2 if shortcut else 1
 for i in range(len(vals)):
  length=1;prev=vals[i]
  for value in vals[i+1:]:
   gap=value-prev
   if gap<=0:continue
   if gap>gapmax:break
   length+=1;prev=value
   if length>=needed:return True
 return False
def _suits(c,smeared):
 if _enh(c)=="wild":return ("red","black") if smeared else ("hearts","diamonds","spades","clubs")
 s=_suit(c)
 if not smeared:return (s,) if s else ()
 if s in {"hearts","diamonds"}:return ("red",)
 if s in {"spades","clubs"}:return ("black",)
 return (s,) if s else ()
def _shape(cards,j):
 natural=[c for c in cards if not _stone(c)];r=Counter(_rank(c) for c in natural if _rank(c));counts=sorted(r.values(),reverse=True);sh=set()
 if natural:sh.add("HIGH_CARD")
 if counts and counts[0]>=2:sh.add("PAIR")
 if len([x for x in counts if x>=2])>=2:sh.add("TWO_PAIR")
 if counts and counts[0]>=3:sh.add("THREE_OF_A_KIND")
 if counts and counts[0]>=4:sh.add("FOUR_OF_A_KIND")
 m={"2":2,"3":3,"4":4,"5":5,"6":6,"7":7,"8":8,"9":9,"10":10,"T":10,"J":11,"Q":12,"K":13,"A":14};nums={m[x] for x in r if x in m};need=4 if _has(j,"fourfingers") else 5
 if _straight(nums,need,_has(j,"shortcut")):sh.add("STRAIGHT")
 sm=_has(j,"smearedjoker","smeared");sc=Counter()
 for c in natural:
  for s in _suits(c,sm):sc[s]+=1
 if any(v>=need for v in sc.values()):sh.add("FLUSH")
 return sh
def realize_hand_bond(d,s,t):
 d=enrich_development(d)
 if _floor(d)==BondRealization.DORMANT:return replace(d,realization=BondRealization.DORMANT)
 a=_known(s)==t or t in _shape(_cards(s,"hand","current_hand","cards_in_hand"),list(getattr(s,"jokers",()) or ()));rep=bool(getattr(s,"target_hand_repeatable",False) or getattr(s,"hand_consistency_high",False));return _finish(d,active=a,strong=a and rep)
def realize_pair(d,s):return realize_hand_bond(d,s,"PAIR")
def realize_high_card(d,s):return realize_hand_bond(d,s,"HIGH_CARD")
def realize_two_pair(d,s):return realize_hand_bond(d,s,"TWO_PAIR")
def realize_three_kind(d,s):return realize_hand_bond(d,s,"THREE_OF_A_KIND")
def realize_four_kind(d,s):return realize_hand_bond(d,s,"FOUR_OF_A_KIND")
def realize_straight(d,s):return realize_hand_bond(d,s,"STRAIGHT")
def realize_flush(d,s):return realize_hand_bond(d,s,"FLUSH")
def realize_played_retrigger(d,s):
 d=enrich_development(d);j=list(getattr(s,"jokers",()) or ());raw=getattr(s,"scoring_cards",None);played=list(raw or ()) if raw is not None else _cards(s,"selected_cards","cards_to_play");live=[c for c in played if not _debuffed(c)];par=_has(j,"pareidolia");red=sum(_seal(c)=="red" for c in live);face=len(live) if par else sum(not _stone(c) and _rank(c) in {"J","Q","K"} for c in live);hack=sum(not _stone(c) and _rank(c) in {"2","3","4","5"} for c in live);src=sum((_has(j,"sockandbuskin") and face>0,_has(j,"hack") and hack>0,_has(j,"hangingchad") and bool(played) and not _debuffed(played[0])));hl=getattr(s,"hands_left",None);src+=int(_has(j,"dusk") and bool(live) and hl is not None and int(hl) in {0,1});src+=int(red>0);return _finish(d,active=src>0,strong=src>=2 or red>=2)
def realize_deck_thinning(d,s):
 d=enrich_development(d);deck=_deck(s);reduction=max(0,52-len(deck)) if deck else int(getattr(s,"permanent_cards_removed",0) or 0);j=list(getattr(s,"jokers",()) or ());pay=_has(j,"erosion") and reduction>0;fd=bool(getattr(s,"first_discard_available",int(getattr(s,"discards_used_this_round",0) or 0)==0));sd=_cards(s,"cards_to_discard","selected_cards");tr=_has(j,"tradingcard") and fd and len(sd)==1;fh=bool(getattr(s,"first_hand_available",int(getattr(s,"hands_played_this_round",0) or 0)==0));sp=_cards(s,"cards_to_play","selected_cards");six=_has(j,"sixthsense") and fh and len(sp)==1 and not _debuffed(sp[0]) and not _stone(sp[0]) and _rank(sp[0])=="6";live=tr or six;return _finish(d,active=live or pay or (reduction>0 and d.rank>=BondRank.R2),strong=reduction>=12 and (pay or live))
def realize_deck_growth(d,s):
 d=enrich_development(d);deck=_deck(s);growth=max(0,len(deck)-52) if deck else int(getattr(s,"permanent_cards_added",0) or 0);j=list(getattr(s,"jokers",()) or ());pay=_has(j,"hologram") and growth>0;pending=bool(getattr(s,"blind_selection_pending",False));cert=_has(j,"certificate") and pending;marble=_has(j,"marblejoker") and pending;fh=bool(getattr(s,"first_hand_available",int(getattr(s,"hands_played_this_round",0) or 0)==0));sp=_cards(s,"cards_to_play","selected_cards");dna=_has(j,"dna") and fh and len(sp)==1 and not _debuffed(sp[0]);live=cert or marble or dna;return _finish(d,active=live or pay or (growth>0 and d.rank>=BondRank.R2),strong=growth>=12 and (pay or live))
COMMON_REALIZERS={"pair":realize_pair,"high_card":realize_high_card,"two_pair":realize_two_pair,"three_kind":realize_three_kind,"four_kind":realize_four_kind,"straight":realize_straight,"flush":realize_flush,"played_retrigger":realize_played_retrigger,"deck_thinning":realize_deck_thinning,"deck_growth":realize_deck_growth}
def realize_common_family(d,s):
 fn=COMMON_REALIZERS.get(d.bond_id);return enrich_development(d) if fn is None else fn(d,s)