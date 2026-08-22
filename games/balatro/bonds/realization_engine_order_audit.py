from __future__ import annotations
from dataclasses import replace
from typing import Any
from games.balatro.bonds.mechanical_roles import enrich_development
from games.balatro.bonds.model import BondDevelopment,BondRank,BondRealization

def _name(v):
 raw=v if isinstance(v,str) else getattr(v,"name",None) or v.__class__.__name__;return "".join(c for c in str(raw).lower() if c.isalnum())
def _cards(s,*names):
 for n in names:
  if hasattr(s,n):return list(getattr(s,n,None) or ())
 return []
def _jokers(s):return list(getattr(s,"jokers",()) or ())
def _stone(c):return bool(getattr(c,"is_stone",False)) or str(getattr(c,"enhancement","") or "").lower()=="stone"
def _debuffed(c):return bool(getattr(c,"debuffed",False) or getattr(c,"is_debuffed",False))
def _eternal(j):return bool(getattr(j,"eternal",False) or getattr(j,"is_eternal",False)) or "eternal" in str(getattr(j,"sticker",getattr(j,"stake_sticker","")) or "").lower()
def _finish(d,a,strong=False):
 d=enrich_development(d)
 if not d.unlocked or d.rank in (BondRank.LOCKED,BondRank.R0):return replace(d,realization=BondRealization.DORMANT)
 if not a:return replace(d,realization=BondRealization.PARTIAL)
 return replace(d,realization=BondRealization.MATURE if strong and d.rank>=BondRank.R4 else BondRealization.ACTIVE)
def _face(c,par=False):return (not _debuffed(c)) and (par or (not _stone(c) and str(getattr(c,"rank","") or "").upper() in {"J","Q","K"}))
def realize_joker_sacrifice_ordered(d,s):
 j=_jokers(s);pending=bool(getattr(s,"blind_selection_pending",False));i=next((i for i,x in enumerate(j) if "ceremonialdagger" in _name(x)),None);target=j[i+1] if i is not None and i+1<len(j) else None;dagger=pending and target is not None and not _eternal(target);blind=""
 for f in ("selected_blind_type","current_blind_type","blind_type","blind_kind"):
  v=getattr(s,f,None)
  if v:blind=_name(v);break
 madness=any("madness" in _name(x) for x in j) and pending and "boss" not in blind;a=dagger or madness;return _finish(d,a,a and int(getattr(s,"jokers_destroyed",0) or 0)>=6)
def _canio_live(s,j):
 if not any("canio" in _name(x) for x in j):return False
 v=getattr(s,"face_cards_destroyed",getattr(s,"canio_face_cards_destroyed",getattr(s,"canio_triggers",None)))
 if v is not None:return int(v or 0)>0
 destroyed=_cards(s,"destroyed_cards","cards_destroyed_this_event","recently_destroyed_cards");par=any("pareidolia" in _name(x) for x in j);return any(_face(c,par) for c in destroyed)
def realize_card_destruction_scoring(d,s):
 j=_jokers(s);names={_name(x) for x in j};hand=_cards(s,"hand","current_hand","cards_in_hand");fd=bool(getattr(s,"first_discard_available",int(getattr(s,"discards_used_this_round",0) or 0)==0));fh=bool(getattr(s,"first_hand_available",int(getattr(s,"hands_played_this_round",0) or 0)==0));has_discard_window=any(hasattr(s,n) for n in ("cards_to_discard","selected_cards"));has_play_window=any(hasattr(s,n) for n in ("cards_to_play","scoring_cards","played_cards","current_played_cards"));sd=_cards(s,"cards_to_discard","selected_cards");sp=_cards(s,"cards_to_play","selected_cards");trading=any("tradingcard" in n for n in names) and fd and ((len(sd)==1) if has_discard_window else bool(hand));six=any("sixthsense" in n for n in names) and fh and ((len(sp)==1 and not _debuffed(sp[0]) and not _stone(sp[0]) and str(getattr(sp[0],"rank","") or "")=="6") if has_play_window and sp else any(not _debuffed(c) and not _stone(c) and str(getattr(c,"rank","") or "")=="6" for c in hand));pool=_cards(s,"scoring_cards","cards_to_play","played_cards","current_played_cards") or hand;glass=any("glassjoker" in n for n in names) and any(not _debuffed(c) and str(getattr(c,"enhancement","") or "").lower()=="glass" for c in pool);canio=_canio_live(s,j);a=trading or six or glass or canio;return _finish(d,a,sum((trading,six,glass,canio))>=2)
def realize_vampire_ordered(d,s):
 j=_jokers(s);vi=next((i for i,x in enumerate(j) if "vampire" in _name(x)),None)
 if vi is None:return _finish(d,False)
 sc=_cards(s,"scoring_cards","played_cards","current_played_cards");hand=_cards(s,"hand","current_hand","cards_in_hand");deck=_cards(s,"owned_deck","deck");feed_pool=sc or hand or deck;feed=sum(1 for c in feed_pool if not _debuffed(c) and str(getattr(c,"enhancement","") or "").strip());mi=next((i for i,x in enumerate(j) if "midasmask" in _name(x)),None);before=mi is not None and mi<vi;par=any("pareidolia" in _name(x) for x in j);pool=sc or hand or deck;renew=before and any(_face(c,par) for c in pool);a=feed>0 or renew;return _finish(d,a,feed>=2 or (renew and int(getattr(s,"vampire_enhancements_consumed",0) or 0)>=15))
ENGINE_AUDIT_REALIZERS={"joker_sacrifice":realize_joker_sacrifice_ordered,"card_destruction":realize_card_destruction_scoring,"vampire":realize_vampire_ordered}
