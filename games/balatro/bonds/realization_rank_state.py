from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable

from games.balatro.bonds.mechanical_roles import enrich_development
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization


def _cards(state: Any, *names: str) -> list[Any]:
    for name in names:
        value = getattr(state, name, None)
        if value is not None:
            return list(value or ())
    return []


def _jokers(state: Any) -> list[Any]: return list(getattr(state, "jokers", ()) or ())
def _name(value: Any) -> str:
    raw=value if isinstance(value,str) else getattr(value,"name",None) or value.__class__.__name__;return "".join(ch for ch in str(raw).lower() if ch.isalnum())
def _has(values: Iterable[Any], *tokens: str) -> bool:
    names={_name(v) for v in values};return any(any(token in name for name in names) for token in tokens)
def _rank(card: Any) -> str: return str(getattr(card,"rank","") or "").upper()
def _suit(card: Any) -> str: return str(getattr(card,"suit","") or "").lower()
def _enh(card: Any) -> str: return str(getattr(card,"enhancement","") or "").lower()
def _stone(card: Any) -> bool: return _enh(card)=="stone" or bool(getattr(card,"is_stone",False))
def _floor(dev: BondDevelopment) -> BondRealization:
    if not dev.unlocked or dev.rank in (BondRank.LOCKED,BondRank.R0): return BondRealization.DORMANT
    return BondRealization.PARTIAL
def _finish(dev: BondDevelopment, active: bool, strong: bool=False) -> BondDevelopment:
    if _floor(dev)==BondRealization.DORMANT:return replace(enrich_development(dev),realization=BondRealization.DORMANT)
    realization=BondRealization.MATURE if active and strong and dev.rank>=BondRank.R4 else BondRealization.ACTIVE if active else BondRealization.PARTIAL
    return replace(enrich_development(dev),realization=realization)
def _played(state: Any) -> list[Any]: return _cards(state,"scoring_cards","played_cards","current_played_cards")

def realize_aces(dev,state):
    played=_played(state);hits=sum(1 for c in played if not _stone(c) and _rank(c)=="A");payoff=_has(_jokers(state),"scholar","fibonacci");return _finish(dev,bool(hits and payoff),hits>=3 and payoff)

def realize_face_cards(dev,state):
    played=_played(state);jokers=_jokers(state);pareidolia=_has(jokers,"pareidolia")
    # Pareidolia gives even Stone cards the face-card property; without it,
    # Stone's hidden rank must not leak through as J/Q/K.
    hits=len(played) if pareidolia else sum(1 for c in played if not _stone(c) and _rank(c) in {"J","Q","K"})
    payoff=_has(jokers,"pareidolia","sockandbuskin","photograph","scaryface","smileyface","businesscard")
    return _finish(dev,bool(hits and payoff),hits>=3 and payoff)

def realize_low_ranks(dev,state):
    played=_played(state);jokers=_jokers(state)
    matching = 0
    for card in played:
        if _stone(card):
            continue
        rank = _rank(card)
        triggered = (
            (_has(jokers,"hack") and rank in {"2","3","4","5"})
            or (_has(jokers,"weejoker") and rank == "2")
            or (_has(jokers,"fibonacci") and rank in {"2","3","5"})
            or (_has(jokers,"evensteven") and rank in {"2","4"})
            or (_has(jokers,"walkietalkie") and rank == "4")
        )
        if triggered:
            matching += 1
    return _finish(dev, matching>0, matching>=3)

def realize_jacks(dev,state):
    discarded=_cards(state,"discarded_cards","current_discard_cards");jacks=sum(1 for c in discarded if not _stone(c) and _rank(c)=="J");payoff=_has(_jokers(state),"hittheroad");return _finish(dev,bool(jacks and payoff),jacks>=3 and payoff)

def realize_no_face_cards(dev,state):
    played=_played(state)
    if not played:return _finish(dev,False)
    jokers=_jokers(state);payoff=_has(jokers,"ridethebus")
    no_faces=not _has(jokers,"pareidolia") and all(_stone(c) or _rank(c) not in {"J","Q","K"} for c in played)
    streak=int(getattr(state,"ride_the_bus_streak",0) or 0);return _finish(dev,payoff and no_faces,payoff and no_faces and streak>=8)

def _realize_suit(dev,state,suit,*payoffs):
    played=_played(state);jokers=_jokers(state);smeared=_has(jokers,"smearedjoker","smeared")
    compatible={suit}
    if smeared:
        if suit in {"hearts","diamonds"}:compatible={"hearts","diamonds"}
        elif suit in {"spades","clubs"}:compatible={"spades","clubs"}
    hits=sum(1 for c in played if not _stone(c) and (_suit(c) in compatible or _enh(c)=="wild"));payoff=_has(jokers,*payoffs);return _finish(dev,bool(hits and payoff),hits>=4 and payoff)
def realize_hearts(dev,state): return _realize_suit(dev,state,"hearts","bloodstone","lustyjoker")
def realize_spades(dev,state): return _realize_suit(dev,state,"spades","arrowhead","wrathfuljoker")
def realize_clubs(dev,state): return _realize_suit(dev,state,"clubs","onyxagate","gluttonousjoker")
def realize_diamonds(dev,state): return _realize_suit(dev,state,"diamonds","roughgem","greedyjoker")

def realize_lucky(dev,state):
    played=_played(state);lucky=sum(1 for c in played if _enh(c)=="lucky");payoff=_has(_jokers(state),"luckycat","oopsall6s");return _finish(dev,bool(lucky),lucky>=3 and payoff)
def realize_glass(dev,state):
    played=_played(state);glass=sum(1 for c in played if _enh(c)=="glass");payoff=_has(_jokers(state),"glassjoker");return _finish(dev,bool(glass),glass>=2 and payoff)
def realize_stone(dev,state):
    played=_played(state);stone=sum(1 for c in played if _stone(c));payoff=_has(_jokers(state),"stonejoker","marblejoker");return _finish(dev,bool(stone),stone>=3 and payoff)

def realize_gold_economy(dev,state):
    jokers=_jokers(state);hand=_cards(state,"hand","current_hand","cards_in_hand");played=_played(state)
    pareidolia=_has(jokers,"pareidolia")
    held_gold=sum(1 for c in hand if _enh(c)=="gold")
    played_gold=sum(1 for c in played if _enh(c)=="gold")
    played_faces=len(played) if pareidolia else sum(1 for c in played if not _stone(c) and _rank(c) in {"J","Q","K"})
    held_faces=len(hand) if pareidolia else sum(1 for c in hand if not _stone(c) and _rank(c) in {"J","Q","K"})
    golden_ticket=_has(jokers,"goldenticket") and played_gold>0
    midas=_has(jokers,"midasmask") and played_faces>0
    parking=_has(jokers,"reservedparking") and held_faces>0
    intrinsic=held_gold>0
    sources=sum((intrinsic,golden_ticket,midas,parking))
    return _finish(dev,sources>0,sources>=2 or held_gold>=3)

RANK_STATE_REALIZERS={"aces":realize_aces,"face_cards":realize_face_cards,"low_ranks":realize_low_ranks,"jacks":realize_jacks,"no_face_cards":realize_no_face_cards,"hearts":realize_hearts,"spades":realize_spades,"clubs":realize_clubs,"diamonds":realize_diamonds,"lucky":realize_lucky,"glass":realize_glass,"stone":realize_stone,"gold_economy":realize_gold_economy}
def realize_rank_state_family(dev: BondDevelopment,state: Any)->BondDevelopment:
    fn=RANK_STATE_REALIZERS.get(dev.bond_id);return fn(dev,state) if fn else enrich_development(dev)
