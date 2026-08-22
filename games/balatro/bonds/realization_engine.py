from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable

from games.balatro.bonds.mechanical_roles import enrich_development
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization


def _name(value: Any) -> str:
    raw = value if isinstance(value, str) else getattr(value, "name", None) or value.__class__.__name__
    return "".join(ch for ch in str(raw).lower() if ch.isalnum())

def _has(values: Iterable[Any], *tokens: str) -> bool:
    names={_name(v) for v in values};return any(any(token in name for name in names) for token in tokens)
def _cards(state: Any,*names:str)->list[Any]:
    for name in names:
        value=getattr(state,name,None)
        if value is not None:return list(value or ())
    return []
def _jokers(state:Any)->list[Any]:return list(getattr(state,"jokers",()) or ())
def _stone(card:Any)->bool:return bool(getattr(card,"is_stone",False)) or str(getattr(card,"enhancement","") or "").lower()=="stone"
def _floor(dev):return BondRealization.DORMANT if not dev.unlocked or dev.rank in (BondRank.LOCKED,BondRank.R0) else BondRealization.PARTIAL
def _finish(dev,active,strong=False):
    dev=enrich_development(dev)
    if _floor(dev)==BondRealization.DORMANT:return replace(dev,realization=BondRealization.DORMANT)
    if not active:return replace(dev,realization=BondRealization.PARTIAL)
    if strong and dev.rank>=BondRank.R4:return replace(dev,realization=BondRealization.MATURE)
    return replace(dev,realization=BondRealization.ACTIVE)
def realize_burnt(dev,state):
    left=int(getattr(state,"discards_left",getattr(state,"discards_remaining",0)) or 0);used=int(getattr(state,"discards_used_this_round",0) or 0);first=bool(getattr(state,"first_discard_available",left>0 and used==0));target=dev.target or str(getattr(state,"target_hand","HIGH_CARD") or "HIGH_CARD");return _finish(dev,first and bool(target),first and bool(target) and dev.rank>=BondRank.R4)
def realize_cash(dev,state):
    money=int(getattr(state,"money",0) or 0);j=_jokers(state);hand=_cards(state,"hand","current_hand","cards_in_hand");deck=_cards(state,"owned_deck","deck");par=_has(j,"pareidolia");pay=_has(j,"bull","bootstraps");un=_has(j,"rocket","goldenjoker");interest=_has(j,"tothemoon") and money>=5;faces=bool(hand) if par else any(not _stone(c) and str(getattr(c,"rank","") or "").upper() in {"J","Q","K"} for c in hand);parking=_has(j,"reservedparking") and faces;cloud=_has(j,"cloud9") and any(not _stone(c) and str(getattr(c,"rank","") or "")=="9" for c in deck);sat=_has(j,"satellite");hist=getattr(state,"unique_planets_used",getattr(state,"satellite_planets_used",None));sateng=sat and (hist is None or int(hist or 0)>0);src=sum((un,interest,parking,cloud,sateng));return _finish(dev,(pay and money>=25) or src>0,(pay and money>=75) or src>=2 or (src>0 and money>=50))
def realize_no_discard(dev,state):
    j=_jokers(state);tokens=("greenjoker","burglar","delayedgratification","ramen","banner");n=sum(1 for t in tokens if _has(j,t));discarded=int(getattr(state,"discards_used_this_round",0) or 0);active=n>0 and discarded==0;return _finish(dev,active,active and n>=2)
def realize_tarot(dev,state):
    j=_jokers(state);v=list(getattr(state,"vouchers",()) or ());c=_cards(state,"consumables","consumable_cards");t=any("tarot" in _name(x) or str(getattr(x,"set","")).lower()=="tarot" for x in c);e=_has(j,"cartomancer","vagabond","hallucination","fortuneteller","superposition","8ball","eightball");s=_has(v,"tarotmerchant","tarottycoon");return _finish(dev,t or e or s,sum((t,e,s))>=2)
def realize_planet(dev,state):
    j=_jokers(state);v=list(getattr(state,"vouchers",()) or ());c=_cards(state,"consumables","consumable_cards");p=any("planet" in _name(x) or str(getattr(x,"set","")).lower()=="planet" for x in c);e=_has(j,"constellation","astronomer","spacejoker");b=any(str(getattr(x,"seal","") or "").lower()=="blue" for x in _cards(state,"hand","current_hand","cards_in_hand"));s=_has(v,"planetmerchant","planettycoon","telescope");return _finish(dev,p or e or b or s,sum((p,e,b,s))>=2)
def realize_discard(dev,state):
    j=_jokers(state);discarded=_cards(state,"discarded_cards","current_discard_cards","cards_to_discard");left=int(getattr(state,"discards_left",getattr(state,"discards_remaining",0)) or 0)
    if not discarded or left<=0:return _finish(dev,False)
    par=_has(j,"pareidolia");faces=len(discarded) if par else sum(1 for c in discarded if not _stone(c) and str(getattr(c,"rank","") or "").upper() in {"J","Q","K"});jacks=sum(1 for c in discarded if not _stone(c) and str(getattr(c,"rank","") or "").upper()=="J")
    target_rank=str(getattr(state,"mail_in_rebate_rank",getattr(state,"rebate_rank","")) or "").upper();rebate=bool(target_rank) and any(not _stone(c) and str(getattr(c,"rank","") or "").upper()==target_rank for c in discarded)
    castle_suit=str(getattr(state,"castle_suit",getattr(state,"castle_target_suit","")) or "").lower();castle=bool(castle_suit) and any(not _stone(c) and (str(getattr(c,"suit","") or "").lower()==castle_suit or str(getattr(c,"enhancement","") or "").lower()=="wild") for c in discarded)
    sources=sum((_has(j,"yorick"),_has(j,"facelessjoker") and faces>=3,_has(j,"hittheroad") and jacks>0,_has(j,"mailinrebate") and rebate,_has(j,"castle") and castle));return _finish(dev,sources>0,sources>=2)
def realize_blind_skip(dev,state):
    active=_has(_jokers(state),"throwback");skipped=int(getattr(state,"blinds_skipped",0) or 0);return _finish(dev,active,active and skipped>=5)
def realize_sell_value(dev,state):
    total=int(getattr(state,"joker_sell_value_total",0) or 0);active=_has(_jokers(state),"swashbuckler") and total>0;return _finish(dev,active,active and total>=35)
def realize_joker_sacrifice(dev,state):
    j=_jokers(state);idx=next((i for i,x in enumerate(j) if "ceremonialdagger" in _name(x)),None);target=idx is not None and idx+1<len(j);fodder=target and (bool(getattr(state,"sacrificable_joker_available",False)) or "riffraff" in _name(j[idx+1]));kind=_name(getattr(state,"blind_type",getattr(state,"blind_kind","")));boss=bool(getattr(state,"is_boss_blind",False)) or "boss" in kind;mad=_has(j,"madness");pending=bool(getattr(state,"blind_selection_pending",True));active=fodder or (mad and pending and not boss);return _finish(dev,active,active and int(getattr(state,"jokers_destroyed",0) or 0)>=6)
def realize_card_destruction(dev,state):
    j=_jokers(state);hand=_cards(state,"hand","current_hand","cards_in_hand");fd=bool(getattr(state,"first_discard_available",int(getattr(state,"discards_used_this_round",0) or 0)==0));fh=bool(getattr(state,"first_hand_available",int(getattr(state,"hands_played_this_round",0) or 0)==0));sd=_cards(state,"selected_cards","cards_to_discard");sp=_cards(state,"cards_to_play","selected_cards");tr=_has(j,"tradingcard") and fd and len(sd)==1;six=_has(j,"sixthsense") and fh and len(sp)==1 and not _stone(sp[0]) and str(getattr(sp[0],"rank",""))=="6";raw=getattr(state,"scoring_cards",None);pool=list(raw or ()) if raw is not None else (_cards(state,"played_cards","current_played_cards") or hand);glass=_has(j,"glassjoker") and any(str(getattr(c,"enhancement","") or "").lower()=="glass" for c in pool);canio=_has(j,"canio") and int(getattr(state,"cards_destroyed",0) or 0)>0;active=tr or six or glass or canio;return _finish(dev,active,sum((tr,six,glass,canio))>=2)
def realize_hand_repetition(dev,state):
    j=_jokers(state);cur=str(getattr(state,"current_hand_type",getattr(state,"last_hand_type","")) or "").upper().replace(" ","_");counts=getattr(state,"hand_play_counts",{}) or {};norm={str(k).upper().replace(" ","_"):int(v or 0) for k,v in counts.items()};prior=norm.get(cur,0) if cur else 0;prev=str(getattr(state,"previous_hand_type","") or "").upper().replace(" ","_");hist=prior>0 if norm else bool(cur) and cur==prev;cs=_has(j,"cardsharp") and bool(cur) and hist;sn=_has(j,"supernova") and bool(cur);active=cs or sn;return _finish(dev,active,active and max(norm.values(),default=0)>=18)
def realize_enhanced_cards(dev,state):
    if not _has(_jokers(state),"driverslicense"):return _finish(dev,False)
    enhanced=sum(1 for c in _cards(state,"owned_deck","deck") if str(getattr(c,"enhancement","") or "").strip());active=enhanced>=16;return _finish(dev,active,active)
def realize_vampire(dev,state):
    j=_jokers(state);vi=next((i for i,x in enumerate(j) if "vampire" in _name(x)),None)
    if vi is None:return _finish(dev,False)
    hand=_cards(state,"hand","current_hand","cards_in_hand");deck=_cards(state,"owned_deck","deck");raw=getattr(state,"scoring_cards",None);sc=list(raw or ()) if raw is not None else _cards(state,"played_cards","current_played_cards");feedcards=sc if raw is not None else (sc or hand);feed=sum(1 for c in feedcards if str(getattr(c,"enhancement","") or "").strip());mi=next((i for i,x in enumerate(j) if "midasmask" in _name(x)),None);before=mi is not None and mi<vi;par=_has(j,"pareidolia");pool=sc if raw is not None else (sc or hand or deck);face=bool(pool) if par else any(not _stone(c) and str(getattr(c,"rank","") or "").upper() in {"J","Q","K"} for c in pool);renew=before and face;active=feed>0 or renew;return _finish(dev,active,feed>=2 or (renew and int(getattr(state,"vampire_enhancements_consumed",0) or 0)>=15))
ENGINE_REALIZERS={"burnt":realize_burnt,"cash":realize_cash,"no_discard":realize_no_discard,"tarot":realize_tarot,"planet":realize_planet,"discard":realize_discard,"blind_skip":realize_blind_skip,"sell_value":realize_sell_value,"joker_sacrifice":realize_joker_sacrifice,"card_destruction":realize_card_destruction,"hand_repetition":realize_hand_repetition,"enhanced_cards":realize_enhanced_cards,"vampire":realize_vampire}
def realize_engine_family(dev,state):
    fn=ENGINE_REALIZERS.get(dev.bond_id);return enrich_development(dev) if fn is None else fn(dev,state)
