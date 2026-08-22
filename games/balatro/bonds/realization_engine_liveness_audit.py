from __future__ import annotations
from dataclasses import replace
from typing import Any
from games.balatro.bonds.mechanical_roles import enrich_development
from games.balatro.bonds.model import BondDevelopment,BondRank,BondRealization

def _name(v):
 raw=v if isinstance(v,str) else getattr(v,"name",None) or v.__class__.__name__;return "".join(c for c in str(raw).lower() if c.isalnum())
def _jokers(s):return list(getattr(s,"jokers",()) or ())
def _has(vals,*tokens):
 names={_name(v) for v in vals};return any(any(t in n for n in names) for t in tokens)
def _cards(s,*names):
 for n in names:
  if hasattr(s,n):return list(getattr(s,n,None) or ())
 return []
def _debuffed(c):return bool(getattr(c,"debuffed",False) or getattr(c,"is_debuffed",False))
def _stone(c):return bool(getattr(c,"is_stone",False)) or str(getattr(c,"enhancement","") or "").lower()=="stone"
def _finish(d,a,strong=False):
 d=enrich_development(d)
 if not d.unlocked or d.rank in (BondRank.LOCKED,BondRank.R0):return replace(d,realization=BondRealization.DORMANT)
 if not a:return replace(d,realization=BondRealization.PARTIAL)
 return replace(d,realization=BondRealization.MATURE if strong and d.rank>=BondRank.R4 else BondRealization.ACTIVE)
def _scoring(s):return bool(_cards(s,"scoring_cards","cards_to_play","played_cards","current_played_cards"))
def _round_end(s):
 h=getattr(s,"hands_left",None);return bool(getattr(s,"round_end_pending",False) or getattr(s,"last_hand_played",False) or (h is not None and int(h)==0))
def _has_window(s):return any(hasattr(s,n) for n in ("scoring_cards","cards_to_play","played_cards","current_played_cards","round_end_pending","last_hand_played","hands_left","blind_selection_pending"))
def realize_cash_live(d,s):
 j=_jokers(s);money=int(getattr(s,"money",0) or 0);hand=[c for c in _cards(s,"hand","current_hand","cards_in_hand") if not _debuffed(c)];deck=_cards(s,"owned_deck","deck");par=_has(j,"pareidolia");faces=bool(hand) if par else any(not _stone(c) and str(getattr(c,"rank","") or "").upper() in {"J","Q","K"} for c in hand);nines=any(not _stone(c) and str(getattr(c,"rank","") or "").upper()=="9" for c in deck);hist=getattr(s,"unique_planets_used",getattr(s,"satellite_planets_used",None));sat_ok=hist is None or int(hist or 0)>0
 if not _has_window(s):
  src=sum((_has(j,"goldenjoker","rocket"),_has(j,"tothemoon") and money>=5,_has(j,"cloud9") and nines,_has(j,"satellite") and sat_ok,_has(j,"reservedparking") and faces));active=(_has(j,"bull","bootstraps") and money>=25) or src>0;return _finish(d,active,src>=2 or (_has(j,"bull","bootstraps") and money>=75))
 scoring=_scoring(s);end=_round_end(s);src=sum((_has(j,"bull") and scoring,_has(j,"bootstraps") and scoring and money>=5,_has(j,"reservedparking") and scoring and faces,_has(j,"goldenjoker","rocket") and end,_has(j,"tothemoon") and end and money>=5,_has(j,"cloud9") and end and nines,_has(j,"satellite") and end and sat_ok));return _finish(d,src>0,src>=2)
def realize_no_discard_live(d,s):
 j=_jokers(s);used=int(getattr(s,"discards_used_this_round",0) or 0);owned=sum(1 for t in ("greenjoker","burglar","delayedgratification","ramen","banner") if _has(j,t))
 if not _has_window(s):return _finish(d,owned>0 and used==0,owned>=2 and used==0)
 scoring=_scoring(s);end=_round_end(s);pending=bool(getattr(s,"blind_selection_pending",False));left=int(getattr(s,"discards_left",getattr(s,"discards_remaining",0)) or 0);src=sum((_has(j,"greenjoker") and scoring,_has(j,"burglar") and pending,_has(j,"delayedgratification") and end and used==0,_has(j,"ramen") and scoring,_has(j,"banner") and scoring and left>0));return _finish(d,src>0,src>=2)
ENGINE_LIVENESS_AUDIT_REALIZERS={"cash":realize_cash_live,"no_discard":realize_no_discard_live}
