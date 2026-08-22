from __future__ import annotations
from dataclasses import replace
from typing import Any,Iterable
from games.balatro.bonds.mechanical_roles import enrich_development
from games.balatro.bonds.model import BondDevelopment,BondRank,BondRealization

def _cards(s,*names):
 for n in names:
  if hasattr(s,n):return list(getattr(s,n,None) or ())
 return []
def _jokers(s):return list(getattr(s,"jokers",()) or ())
def _name(v):
 raw=v if isinstance(v,str) else getattr(v,"name",None) or v.__class__.__name__;return "".join(c for c in str(raw).lower() if c.isalnum())
def _has(vals,*tokens):
 names={_name(v) for v in vals};return any(any(t in n for n in names) for t in tokens)
def _rank(c):return str(getattr(c,"rank","") or "").upper()
def _suit(c):return str(getattr(c,"suit","") or "").lower()
def _enh(c):return str(getattr(c,"enhancement","") or "").lower()
def _stone(c):return _enh(c)=="stone" or bool(getattr(c,"is_stone",False))
def _debuffed(c):return bool(getattr(c,"debuffed",False) or getattr(c,"is_debuffed",False))
def _live(c):return not _debuffed(c)
def _floor(d):return BondRealization.DORMANT if not d.unlocked or d.rank in (BondRank.LOCKED,BondRank.R0) else BondRealization.PARTIAL
def _finish(d,a,strong=False):
 d=enrich_development(d)
 if _floor(d)==BondRealization.DORMANT:return replace(d,realization=BondRealization.DORMANT)
 return replace(d,realization=BondRealization.MATURE if a and strong and d.rank>=BondRank.R4 else BondRealization.ACTIVE if a else BondRealization.PARTIAL)
def _played(s):return _cards(s,"scoring_cards","played_cards","current_played_cards")
def realize_aces(d,s):
 p=_played(s);j=_jokers(s);pay=_has(j,"scholar","fibonacci");m=sum(1 for c in p if _live(c) and not _stone(c) and _rank(c)=="A");return _finish(d,bool(m and pay),m>=3 and pay)
def realize_face_cards(d,s):
 p=_played(s);j=_jokers(s);par=_has(j,"pareidolia");m=sum(1 for c in p if _live(c) and (par or (not _stone(c) and _rank(c) in {"J","Q","K"})));pay=_has(j,"pareidolia","sockandbuskin","photograph","scaryface","smileyface","businesscard");return _finish(d,bool(m and pay),m>=3 and pay)
def realize_low_ranks(d,s):
 p=_played(s);j=_jokers(s);m=0
 for c in p:
  if _debuffed(c) or _stone(c):continue
  r=_rank(c);tr=(_has(j,"hack") and r in {"2","3","4","5"}) or (_has(j,"weejoker") and r=="2") or (_has(j,"fibonacci") and r in {"2","3","5","8","A"}) or (_has(j,"evensteven") and r in {"2","4","6","8","10","T"}) or (_has(j,"walkietalkie") and r in {"4","10","T"})
  if tr:m+=1
 return _finish(d,m>0,m>=3)
def realize_jacks(d,s):
 cards=_cards(s,"discarded_cards","current_discard_cards");n=sum(1 for c in cards if _live(c) and not _stone(c) and _rank(c)=="J");pay=_has(_jokers(s),"hittheroad");return _finish(d,bool(n and pay),n>=3 and pay)
def realize_no_face_cards(d,s):
 p=_played(s)
 if not p:return _finish(d,False)
 j=_jokers(s);interactive=[c for c in p if _live(c)];par=_has(j,"pareidolia");safe=(len(interactive)==0) if par else all(_stone(c) or _rank(c) not in {"J","Q","K"} for c in interactive);st=int(getattr(s,"ride_the_bus_streak",0) or 0);pay=_has(j,"ridethebus");return _finish(d,pay and safe,pay and safe and st>=8)
def _realize_suit(d,s,suit,*payoffs):
 p=_played(s);j=_jokers(s);sm=_has(j,"smearedjoker","smeared");comp={suit}
 if sm:comp={"hearts","diamonds"} if suit in {"hearts","diamonds"} else {"spades","clubs"}
 n=sum(1 for c in p if _live(c) and not _stone(c) and (_suit(c) in comp or _enh(c)=="wild"));pay=_has(j,*payoffs);return _finish(d,bool(n and pay),n>=4 and pay)
def realize_hearts(d,s):return _realize_suit(d,s,"hearts","bloodstone","lustyjoker")
def realize_spades(d,s):return _realize_suit(d,s,"spades","arrowhead","wrathfuljoker")
def realize_clubs(d,s):return _realize_suit(d,s,"clubs","onyxagate","gluttonousjoker")
def realize_diamonds(d,s):return _realize_suit(d,s,"diamonds","roughgem","greedyjoker")
def realize_lucky(d,s):
 p=_played(s);n=sum(1 for c in p if _live(c) and _enh(c)=="lucky");pay=_has(_jokers(s),"luckycat","oopsall6s");return _finish(d,n>0,n>=3 or (n>=2 and pay))
def realize_glass(d,s):
 p=_played(s);n=sum(1 for c in p if _live(c) and _enh(c)=="glass");pay=_has(_jokers(s),"glassjoker");return _finish(d,n>0,n>=2 and pay)
def realize_stone(d,s):
 p=_played(s);n=sum(1 for c in p if _live(c) and _stone(c));pay=_has(_jokers(s),"stonejoker","marblejoker");return _finish(d,n>0,n>=3 and pay)
def realize_gold_economy(d,s):
 j=_jokers(s);held=[c for c in _cards(s,"hand","current_hand","cards_in_hand") if _live(c)];played=[c for c in _played(s) if _live(c)];par=_has(j,"pareidolia");hg=sum(1 for c in held if _enh(c)=="gold");pg=sum(1 for c in played if _enh(c)=="gold");pf=len(played) if par else sum(1 for c in played if not _stone(c) and _rank(c) in {"J","Q","K"});hf=len(held) if par else sum(1 for c in held if not _stone(c) and _rank(c) in {"J","Q","K"});intrinsic=hg>0;ticket=_has(j,"goldenticket") and pg>0;midas=_has(j,"midasmask") and pf>0;parking=_has(j,"reservedparking") and hf>0;sources=sum((intrinsic,ticket,midas,parking));return _finish(d,sources>0,sources>=2 or hg>=3)
RANK_STATE_REALIZERS={"aces":realize_aces,"face_cards":realize_face_cards,"low_ranks":realize_low_ranks,"jacks":realize_jacks,"no_face_cards":realize_no_face_cards,"hearts":realize_hearts,"spades":realize_spades,"clubs":realize_clubs,"diamonds":realize_diamonds,"lucky":realize_lucky,"glass":realize_glass,"stone":realize_stone,"gold_economy":realize_gold_economy}
def realize_rank_state_family(d,s):
 fn=RANK_STATE_REALIZERS.get(d.bond_id);return fn(d,s) if fn else enrich_development(d)
