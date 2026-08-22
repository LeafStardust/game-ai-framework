from __future__ import annotations
from dataclasses import replace
from typing import Any
from games.balatro.bonds.mechanical_roles import enrich_development
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization

def _name(value:Any)->str:
 raw=value if isinstance(value,str) else getattr(value,"name",None) or value.__class__.__name__;return "".join(ch for ch in str(raw).lower() if ch.isalnum())
def _cards(state:Any,*names:str)->list[Any]:
 for name in names:
  value=getattr(state,name,None)
  if value is not None:return list(value or ())
 return []
def _jokers(state):return list(getattr(state,"jokers",()) or ())
def _stone(card):return bool(getattr(card,"is_stone",False)) or str(getattr(card,"enhancement","") or "").lower()=="stone"
def _debuffed(card):return bool(getattr(card,"debuffed",False) or getattr(card,"is_debuffed",False))
def _eternal(joker):
 if bool(getattr(joker,"eternal",False) or getattr(joker,"is_eternal",False)):return True
 return "eternal" in str(getattr(joker,"sticker",getattr(joker,"stake_sticker","")) or "").lower()
def _finish(dev,active,strong=False):
 dev=enrich_development(dev)
 if not dev.unlocked or dev.rank in (BondRank.LOCKED,BondRank.R0):return replace(dev,realization=BondRealization.DORMANT)
 if not active:return replace(dev,realization=BondRealization.PARTIAL)
 return replace(dev,realization=BondRealization.MATURE if strong and dev.rank>=BondRank.R4 else BondRealization.ACTIVE)
def _face(card,pareidolia=False):
 if _debuffed(card):return False
 if pareidolia:return True
 return not _stone(card) and str(getattr(card,"rank","") or "").upper() in {"J","Q","K"}
def realize_joker_sacrifice_ordered(dev,state):
 jokers=_jokers(state);pending=bool(getattr(state,"blind_selection_pending",False));i=next((i for i,j in enumerate(jokers) if "ceremonialdagger" in _name(j)),None);target=jokers[i+1] if i is not None and i+1<len(jokers) else None;dagger=pending and target is not None and not _eternal(target);madness=any("madness" in _name(j) for j in jokers);blind=""
 for f in ("selected_blind_type","current_blind_type","blind_type","blind_kind"):
  v=getattr(state,f,None)
  if v:blind=_name(v);break
 mad=madness and pending and "boss" not in blind;active=dagger or mad;return _finish(dev,active,active and int(getattr(state,"jokers_destroyed",0) or 0)>=6)
def _canio_live(state,jokers):
 if not any("canio" in _name(j) for j in jokers):return False
 explicit=getattr(state,"face_cards_destroyed",getattr(state,"canio_face_cards_destroyed",getattr(state,"canio_triggers",None)))
 if explicit is not None:return int(explicit or 0)>0
 destroyed=_cards(state,"destroyed_cards","cards_destroyed_this_event","recently_destroyed_cards")
 if destroyed:
  par=any("pareidolia" in _name(j) for j in jokers);return any(_face(c,par) for c in destroyed)
 return False
def realize_card_destruction_scoring(dev,state):
 jokers=_jokers(state);names={_name(j) for j in jokers};fd=bool(getattr(state,"first_discard_available",int(getattr(state,"discards_used_this_round",0) or 0)==0));fh=bool(getattr(state,"first_hand_available",int(getattr(state,"hands_played_this_round",0) or 0)==0));sd=_cards(state,"cards_to_discard","selected_cards");sp=_cards(state,"cards_to_play","selected_cards");trading=any("tradingcard" in n for n in names) and fd and len(sd)==1;six=any("sixthsense" in n for n in names) and fh and len(sp)==1 and not _debuffed(sp[0]) and not _stone(sp[0]) and str(getattr(sp[0],"rank","") or "")=="6";raw=getattr(state,"scoring_cards",None);pool=list(raw or ()) if raw is not None else _cards(state,"cards_to_play","selected_cards","hand","current_hand");glass=any("glassjoker" in n for n in names) and any(not _debuffed(c) and str(getattr(c,"enhancement","") or "").lower()=="glass" for c in pool);canio=_canio_live(state,jokers);active=trading or six or glass or canio;return _finish(dev,active,sum((trading,six,glass,canio))>=2)
def realize_vampire_ordered(dev,state):
 jokers=_jokers(state);vi=next((i for i,j in enumerate(jokers) if "vampire" in _name(j)),None)
 if vi is None:return _finish(dev,False)
 raw=getattr(state,"scoring_cards",None)
 if raw is not None:sc=list(raw or ());feed_cards=sc
 else:sc=_cards(state,"played_cards","current_played_cards");feed_cards=sc or _cards(state,"hand","current_hand","cards_in_hand")
 feed=sum(1 for c in feed_cards if not _debuffed(c) and str(getattr(c,"enhancement","") or "").strip());mi=next((i for i,j in enumerate(jokers) if "midasmask" in _name(j)),None);before=mi is not None and mi<vi;par=any("pareidolia" in _name(j) for j in jokers);pool=sc if raw is not None else (sc or _cards(state,"hand","current_hand","cards_in_hand"));face=any(_face(c,par) for c in pool);renew=before and face;active=feed>0 or renew;strong=feed>=2 or (renew and int(getattr(state,"vampire_enhancements_consumed",0) or 0)>=15);return _finish(dev,active,strong)
ENGINE_AUDIT_REALIZERS={"joker_sacrifice":realize_joker_sacrifice_ordered,"card_destruction":realize_card_destruction_scoring,"vampire":realize_vampire_ordered}
