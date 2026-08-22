from __future__ import annotations
from dataclasses import replace
from typing import Any
from games.balatro.bonds.mechanical_roles import enrich_development
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization

def _name(value:Any)->str:
    raw=value if isinstance(value,str) else getattr(value,"name",None) or value.__class__.__name__;return "".join(ch for ch in str(raw).lower() if ch.isalnum())
def _has(values,*tokens):
    names={_name(v) for v in values};return any(any(t in n for n in names) for t in tokens)
def _cards(state,*names):
    for name in names:
        value=getattr(state,name,None)
        if value is not None:return list(value or ())
    return []
def _enh(card):return str(getattr(card,"enhancement","") or "").lower()
def _stone(card):return _enh(card)=="stone" or bool(getattr(card,"is_stone",False))
def _rank(card):return str(getattr(card,"rank","") or "").upper()
def _suit(card):return str(getattr(card,"suit","") or "").lower()
def _finish(dev,active,strong=False):
    dev=enrich_development(dev)
    if not dev.unlocked or dev.rank in (BondRank.LOCKED,BondRank.R0):return replace(dev,realization=BondRealization.DORMANT)
    if not active:return replace(dev,realization=BondRealization.PARTIAL)
    if strong and dev.rank>=BondRank.R4:return replace(dev,realization=BondRealization.MATURE)
    return replace(dev,realization=BondRealization.ACTIVE)
def _known_hand_type(state):
    for f in ("current_hand_type","selected_hand_type","best_hand_type","hand_type"):
        v=getattr(state,f,None)
        if v:return str(v).upper().replace(" ","_")
    return ""
def realize_tarot_triggered(dev,state):
    j=list(getattr(state,"jokers",()) or ());v=list(getattr(state,"vouchers",()) or ());cons=_cards(state,"consumables","consumable_cards");raw=getattr(state,"scoring_cards",None);sc=list(raw or ()) if raw is not None else _cards(state,"cards_to_play","selected_cards","played_cards");tarot=any("tarot" in _name(c) or str(getattr(c,"set","")).lower()=="tarot" for c in cons);shop=_has(v,"tarotmerchant","tarottycoon");cart=_has(j,"cartomancer") and bool(getattr(state,"blind_selection_pending",False));money=int(getattr(state,"money",0) or 0);vag=_has(j,"vagabond") and money<=4 and bool(sc);boost=bool(getattr(state,"booster_pack_open",False) or getattr(state,"booster_open",False) or getattr(state,"booster_pack_pending",False));hall=_has(j,"hallucination") and boost;used=int(getattr(state,"tarot_cards_used",getattr(state,"tarots_used",0)) or 0);fortune=_has(j,"fortuneteller") and used>0;straight=_known_hand_type(state) in {"STRAIGHT","STRAIGHT_FLUSH"};ace=any(not _stone(c) and _rank(c)=="A" for c in sc);superp=_has(j,"superposition") and straight and ace;eight=any(not _stone(c) and _rank(c) in {"8","EIGHT"} for c in sc);ball=_has(j,"8ball","eightball") and eight;s=sum((tarot,shop,cart,vag,hall,fortune,superp,ball));return _finish(dev,s>0,s>=2)
def realize_planet_triggered(dev,state):
    j=list(getattr(state,"jokers",()) or ());v=list(getattr(state,"vouchers",()) or ());cons=_cards(state,"consumables","consumable_cards");hand=_cards(state,"hand","current_hand","cards_in_hand");planet=any("planet" in _name(c) or str(getattr(c,"set","")).lower()=="planet" for c in cons);shop=_has(v,"planetmerchant","planettycoon","telescope");used=int(getattr(state,"planet_cards_used",getattr(state,"planets_used",0)) or 0);constellation=_has(j,"constellation") and used>0;astronomer=_has(j,"astronomer") and planet;raw=getattr(state,"scoring_cards",None);played=list(raw or ()) if raw is not None else _cards(state,"cards_to_play","selected_cards","played_cards");space=_has(j,"spacejoker") and bool(played);round_end=bool(getattr(state,"round_end_pending",False) or getattr(state,"last_hand_played",False) or int(getattr(state,"hands_left",1) or 1)==0);blue=round_end and any(str(getattr(c,"seal","") or "").lower()=="blue" for c in hand);s=sum((planet,shop,constellation,astronomer,space,blue));return _finish(dev,s>0,s>=2)
def realize_discard_triggered(dev,state):
    jokers=list(getattr(state,"jokers",()) or ())
    discarded=_cards(state,"discarded_cards","current_discard_cards","cards_to_discard","selected_cards")
    if not discarded:return _finish(dev,False)
    nonstone=[c for c in discarded if not _stone(c)]
    yorick=_has(jokers,"yorick") and bool(discarded)
    castle_suit=str(getattr(state,"castle_suit",getattr(state,"current_castle_suit","")) or "").lower()
    castle=_has(jokers,"castle") and bool(castle_suit) and any(_suit(c)==castle_suit for c in nonstone)
    rebate_rank=str(getattr(state,"mail_in_rebate_rank",getattr(state,"rebate_rank","")) or "").upper()
    rebate=_has(jokers,"mailinrebate") and bool(rebate_rank) and any(_rank(c)==rebate_rank for c in nonstone)
    pareidolia=_has(jokers,"pareidolia")
    face_count=len(discarded) if pareidolia else sum(1 for c in nonstone if _rank(c) in {"J","Q","K"})
    faceless=_has(jokers,"facelessjoker") and face_count>=3
    hitroad=_has(jokers,"hittheroad") and any(_rank(c)=="J" for c in nonstone)
    sources=sum((yorick,castle,rebate,faceless,hitroad));return _finish(dev,sources>0,sources>=2)
TRIGGERED_ENGINE_OVERRIDES={"tarot":realize_tarot_triggered,"planet":realize_planet_triggered,"discard":realize_discard_triggered}
