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
def _enh(card:Any)->str:return str(getattr(card,"enhancement","") or "").lower()
def _stone(card:Any)->bool:return _enh(card)=="stone" or bool(getattr(card,"is_stone",False))
def _debuffed(card:Any)->bool:return bool(getattr(card,"debuffed",False) or getattr(card,"is_debuffed",False))
def _live(card:Any)->bool:return not _debuffed(card)
def _floor(dev):return BondRealization.DORMANT if not dev.unlocked or dev.rank in (BondRank.LOCKED,BondRank.R0) else BondRealization.PARTIAL
def _finish(dev,active,strong=False):
    if _floor(dev)==BondRealization.DORMANT:return replace(enrich_development(dev),realization=BondRealization.DORMANT)
    realization=BondRealization.MATURE if active and strong and dev.rank>=BondRank.R4 else BondRealization.ACTIVE if active else BondRealization.PARTIAL
    return replace(enrich_development(dev),realization=realization)
def _played(state):return _cards(state,"scoring_cards","played_cards","current_played_cards")
def realize_aces(dev,state):
    p=_played(state);h=sum(1 for c in p if _live(c) and not _stone(c) and _rank(c)=="A");pay=_has(_jokers(state),"scholar","fibonacci");return _finish(dev,bool(h and pay),h>=3 and pay)
def realize_face_cards(dev,state):
    p=_played(state);j=_jokers(state);par=_has(j,"pareidolia");live=[c for c in p if _live(c)];h=len(live) if par else sum(1 for c in live if not _stone(c) and _rank(c) in {"J","Q","K"});pay=_has(j,"pareidolia","sockandbuskin","photograph","scaryface","smileyface","businesscard");return _finish(dev,bool(h and pay),h>=3 and pay)
def realize_low_ranks(dev,state):
    p=_played(state);j=_jokers(state);m=0
    for c in p:
        if _debuffed(c) or _stone(c):continue
        r=_rank(c);tr=(_has(j,"hack") and r in {"2","3","4","5"}) or (_has(j,"weejoker") and r=="2") or (_has(j,"fibonacci") and r in {"2","3","5"}) or (_has(j,"evensteven") and r in {"2","4"}) or (_has(j,"walkietalkie") and r=="4")
        if tr:m+=1
    return _finish(dev,m>0,m>=3)
def realize_jacks(dev,state):
    d=_cards(state,"discarded_cards","current_discard_cards");n=sum(1 for c in d if _live(c) and not _stone(c) and _rank(c)=="J");pay=_has(_jokers(state),"hittheroad");return _finish(dev,bool(n and pay),n>=3 and pay)
def realize_no_face_cards(dev,state):
    p=_played(state)
    if not p:return _finish(dev,False)
    j=_jokers(state);pay=_has(j,"ridethebus");interactive=[c for c in p if _live(c)];nf=not _has(j,"pareidolia") and all(_stone(c) or _rank(c) not in {"J","Q","K"} for c in interactive);st=int(getattr(state,"ride_the_bus_streak",0) or 0);return _finish(dev,pay and nf,pay and nf and st>=8)
def _realize_suit(dev,state,suit,*payoffs):
    p=_played(state);j=_jokers(state);sm=_has(j,"smearedjoker","smeared");comp={suit}
    if sm:comp={"hearts","diamonds"} if suit in {"hearts","diamonds"} else {"spades","clubs"}
    h=sum(1 for c in p if _live(c) and not _stone(c) and (_suit(c) in comp or _enh(c)=="wild"));pay=_has(j,*payoffs);return _finish(dev,bool(h and pay),h>=4 and pay)
def realize_hearts(dev,state):return _realize_suit(dev,state,"hearts","bloodstone","lustyjoker")
def realize_spades(dev,state):return _realize_suit(dev,state,"spades","arrowhead","wrathfuljoker")
def realize_clubs(dev,state):return _realize_suit(dev,state,"clubs","onyxagate","gluttonousjoker")
def realize_diamonds(dev,state):return _realize_suit(dev,state,"diamonds","roughgem","greedyjoker")
def realize_lucky(dev,state):
    p=_played(state);l=sum(1 for c in p if _live(c) and _enh(c)=="lucky");pay=_has(_jokers(state),"luckycat","oopsall6s");return _finish(dev,bool(l and pay),l>=3 and pay)
def realize_glass(dev,state):
    p=_played(state);g=sum(1 for c in p if _live(c) and _enh(c)=="glass");pay=_has(_jokers(state),"glassjoker");return _finish(dev,bool(g),g>=2 and pay)
def realize_stone(dev,state):
    p=_played(state);s=sum(1 for c in p if _live(c) and _stone(c));pay=_has(_jokers(state),"stonejoker","marblejoker");return _finish(dev,bool(s),s>=3 and pay)
def realize_gold_economy(dev,state):
    j=_jokers(state);hand=_cards(state,"hand","current_hand","cards_in_hand");p=_played(state);par=_has(j,"pareidolia");held_live=[c for c in hand if _live(c)];played_live=[c for c in p if _live(c)];hg=sum(1 for c in held_live if _enh(c)=="gold");pg=sum(1 for c in played_live if _enh(c)=="gold");pf=len(played_live) if par else sum(1 for c in played_live if not _stone(c) and _rank(c) in {"J","Q","K"});hf=len(held_live) if par else sum(1 for c in held_live if not _stone(c) and _rank(c) in {"J","Q","K"});ticket=_has(j,"goldenticket") and pg>0;midas=_has(j,"midasmask") and pf>0;parking=_has(j,"reservedparking") and hf>0;intrinsic=hg>0;sources=sum((intrinsic,ticket,midas,parking));return _finish(dev,sources>0,sources>=2 or hg>=3)
RANK_STATE_REALIZERS={"aces":realize_aces,"face_cards":realize_face_cards,"low_ranks":realize_low_ranks,"jacks":realize_jacks,"no_face_cards":realize_no_face_cards,"hearts":realize_hearts,"spades":realize_spades,"clubs":realize_clubs,"diamonds":realize_diamonds,"lucky":realize_lucky,"glass":realize_glass,"stone":realize_stone,"gold_economy":realize_gold_economy}
def realize_rank_state_family(dev,state):
    fn=RANK_STATE_REALIZERS.get(dev.bond_id);return fn(dev,state) if fn else enrich_development(dev)
