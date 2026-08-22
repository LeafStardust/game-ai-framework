from __future__ import annotations

from collections import Counter
from dataclasses import replace
from typing import Any, Iterable

from games.balatro.bonds.mechanical_roles import enrich_development
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization


def _cards(state: Any, *names: str) -> list[Any]:
    for name in names:
        value = getattr(state, name, None)
        if value is not None:return list(value or ())
    return []
def _deck(state:Any)->list[Any]:
    owned=getattr(state,"owned_deck",None);return list(owned or ()) if owned is not None else list(getattr(state,"deck",()) or ())
def _name(value:Any)->str:
    raw=value if isinstance(value,str) else getattr(value,"name",None) or value.__class__.__name__;return "".join(ch for ch in str(raw).lower() if ch.isalnum())
def _has(values:Iterable[Any],*tokens:str)->bool:
    names={_name(v) for v in values};return any(any(t in n for n in names) for t in tokens)
def _rank(c):return str(getattr(c,"rank","") or "").upper()
def _suit(c):return str(getattr(c,"suit","") or "").lower()
def _enh(c):return str(getattr(c,"enhancement","") or "").lower()
def _seal(c):return str(getattr(c,"seal","") or "").lower()
def _stone(c):return bool(getattr(c,"is_stone",False)) or _enh(c)=="stone"
def _floor(dev):return BondRealization.DORMANT if not dev.unlocked or dev.rank in (BondRank.LOCKED,BondRank.R0) else BondRealization.PARTIAL
def _finish(dev,*,active,strong=False):
    if not active:return replace(dev,realization=_floor(dev))
    return replace(dev,realization=BondRealization.MATURE if strong and dev.rank>=BondRank.R4 else BondRealization.ACTIVE)
def _known_hand_type(state):
    for n in ("current_hand_type","best_hand_type","selected_hand_type","hand_type"):
        v=getattr(state,n,None)
        if v:return str(v).upper().replace(" ","_")
    return ""
def _straight_available(nums,*,needed,shortcut):
    seq=set(nums)
    if 14 in seq:seq.add(1)
    vals=sorted(seq);gapmax=2 if shortcut else 1
    for start in range(len(vals)):
        length=1;prev=vals[start]
        for value in vals[start+1:]:
            gap=value-prev
            if gap<=0:continue
            if gap>gapmax:break
            length+=1;prev=value
            if length>=needed:return True
    return False
def _effective_suits(c,*,smeared):
    if _enh(c)=="wild":return ("red","black") if smeared else ("hearts","diamonds","spades","clubs")
    s=_suit(c)
    if not smeared:return (s,) if s else ()
    if s in {"hearts","diamonds"}:return ("red",)
    if s in {"spades","clubs"}:return ("black",)
    return (s,) if s else ()
def _hand_shape(cards,jokers):
    natural=[c for c in cards if not _stone(c)];ranks=Counter(_rank(c) for c in natural if _rank(c));counts=sorted(ranks.values(),reverse=True);sh=set()
    if natural:sh.add("HIGH_CARD")
    if counts and counts[0]>=2:sh.add("PAIR")
    if len([n for n in counts if n>=2])>=2:sh.add("TWO_PAIR")
    if counts and counts[0]>=3:sh.add("THREE_OF_A_KIND")
    if counts and counts[0]>=4:sh.add("FOUR_OF_A_KIND")
    values={"2":2,"3":3,"4":4,"5":5,"6":6,"7":7,"8":8,"9":9,"10":10,"T":10,"J":11,"Q":12,"K":13,"A":14};nums={values[r] for r in ranks if r in values};needed=4 if _has(jokers,"fourfingers") else 5
    if _straight_available(nums,needed=needed,shortcut=_has(jokers,"shortcut")):sh.add("STRAIGHT")
    smeared=_has(jokers,"smearedjoker","smeared");sc=Counter()
    for c in natural:
        for s in _effective_suits(c,smeared=smeared):sc[s]+=1
    if any(v>=(4 if _has(jokers,"fourfingers") else 5) for v in sc.values()):sh.add("FLUSH")
    return sh
def realize_hand_bond(dev,state,hand_type):
    dev=enrich_development(dev)
    if _floor(dev)==BondRealization.DORMANT:return replace(dev,realization=BondRealization.DORMANT)
    active=_known_hand_type(state)==hand_type or hand_type in _hand_shape(_cards(state,"hand","current_hand","cards_in_hand"),list(getattr(state,"jokers",()) or ()));repeat=bool(getattr(state,"target_hand_repeatable",False) or getattr(state,"hand_consistency_high",False));return _finish(dev,active=active,strong=active and repeat)
def realize_pair(d,s):return realize_hand_bond(d,s,"PAIR")
def realize_high_card(d,s):return realize_hand_bond(d,s,"HIGH_CARD")
def realize_two_pair(d,s):return realize_hand_bond(d,s,"TWO_PAIR")
def realize_three_kind(d,s):return realize_hand_bond(d,s,"THREE_OF_A_KIND")
def realize_four_kind(d,s):return realize_hand_bond(d,s,"FOUR_OF_A_KIND")
def realize_straight(d,s):return realize_hand_bond(d,s,"STRAIGHT")
def realize_flush(d,s):return realize_hand_bond(d,s,"FLUSH")
def realize_played_retrigger(dev,state):
    dev=enrich_development(dev)
    if _floor(dev)==BondRealization.DORMANT:return replace(dev,realization=BondRealization.DORMANT)
    j=list(getattr(state,"jokers",()) or ());raw=getattr(state,"scoring_cards",None);played=list(raw or ()) if raw is not None else _cards(state,"selected_cards","cards_to_play")
    if raw is None and not played:played=_cards(state,"hand","current_hand","cards_in_hand")
    par=_has(j,"pareidolia");red=sum(1 for c in played if _seal(c)=="red");face=len(played) if par else sum(1 for c in played if not _stone(c) and _rank(c) in {"J","Q","K"});hack=sum(1 for c in played if not _stone(c) and _rank(c) in {"2","3","4","5"});src=0
    if _has(j,"sockandbuskin") and face:src+=1
    if _has(j,"hack") and hack:src+=1
    if _has(j,"hangingchad") and played:src+=1
    # Dusk retriggers on the final hand of the round. Depending on telemetry,
    # hands_left may be observed immediately before play (1) or after decrement (0).
    hands_left=getattr(state,"hands_left",None)
    if _has(j,"dusk") and played and hands_left is not None and int(hands_left)==0:src+=1
    elif _has(j,"dusk") and played and hands_left is not None and int(hands_left)==1:src+=1
    if red:src+=1
    return _finish(dev,active=src>0,strong=src>=2 or red>=2)
def realize_deck_thinning(dev,state):
    dev=enrich_development(dev);deck=_deck(state);reduction=max(0,52-len(deck)) if deck else int(getattr(state,"permanent_cards_removed",0) or 0);j=list(getattr(state,"jokers",()) or ());pay=_has(j,"erosion") and reduction>0;fd=bool(getattr(state,"first_discard_available",int(getattr(state,"discards_used_this_round",0) or 0)==0));sd=_cards(state,"cards_to_discard","selected_cards");tr=_has(j,"tradingcard") and fd and len(sd)==1;fh=bool(getattr(state,"first_hand_available",int(getattr(state,"hands_played_this_round",0) or 0)==0));sp=_cards(state,"cards_to_play","selected_cards");six=_has(j,"sixthsense") and fh and len(sp)==1 and not _stone(sp[0]) and _rank(sp[0])=="6";live=tr or six;return _finish(dev,active=live or pay or (reduction>0 and dev.rank>=BondRank.R2),strong=reduction>=12 and (pay or live))
def realize_deck_growth(dev,state):
    dev=enrich_development(dev);deck=_deck(state);growth=max(0,len(deck)-52) if deck else int(getattr(state,"permanent_cards_added",0) or 0);j=list(getattr(state,"jokers",()) or ());pay=_has(j,"hologram") and growth>0;pending=bool(getattr(state,"blind_selection_pending",False));cert=_has(j,"certificate") and pending;marble=_has(j,"marblejoker") and pending;fh=bool(getattr(state,"first_hand_available",int(getattr(state,"hands_played_this_round",0) or 0)==0));sp=_cards(state,"cards_to_play","selected_cards");dna=_has(j,"dna") and fh and len(sp)==1;live=cert or marble or dna;return _finish(dev,active=live or pay or (growth>0 and dev.rank>=BondRank.R2),strong=growth>=12 and (pay or live))
COMMON_REALIZERS={"pair":realize_pair,"high_card":realize_high_card,"two_pair":realize_two_pair,"three_kind":realize_three_kind,"four_kind":realize_four_kind,"straight":realize_straight,"flush":realize_flush,"played_retrigger":realize_played_retrigger,"deck_thinning":realize_deck_thinning,"deck_growth":realize_deck_growth}
def realize_common_family(dev,state):
 fn=COMMON_REALIZERS.get(dev.bond_id);return enrich_development(dev) if fn is None else fn(dev,state)