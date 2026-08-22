from __future__ import annotations
from dataclasses import replace
from games.balatro.bonds.mechanical_roles import enrich_development
from games.balatro.bonds.model import BondRank,BondRealization

def _name(v):
 raw=v if isinstance(v,str) else getattr(v,"name",None) or v.__class__.__name__;return "".join(c for c in str(raw).lower() if c.isalnum())
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
def realize_deck_thinning(d,s):
 j=list(getattr(s,"jokers",()) or ());deck=_cards(s,"owned_deck","deck");reduction=max(0,52-len(deck)) if deck else int(getattr(s,"permanent_cards_removed",0) or 0);erosion=_has(j,"erosion") and reduction>0
 first_discard=bool(getattr(s,"first_discard_available",int(getattr(s,"discards_used_this_round",0) or 0)==0));first_hand=bool(getattr(s,"first_hand_available",int(getattr(s,"hands_played_this_round",0) or 0)==0));explicit_discard=any(hasattr(s,n) for n in ("cards_to_discard","selected_cards"));explicit_play=any(hasattr(s,n) for n in ("cards_to_play","scoring_cards","played_cards","current_played_cards"));sd=_cards(s,"cards_to_discard","selected_cards");sp=_cards(s,"cards_to_play","selected_cards");hand=_cards(s,"hand","current_hand","cards_in_hand");trading=_has(j,"tradingcard") and first_discard and ((len(sd)==1) if explicit_discard else True);six_pool=sp if explicit_play and sp else hand;six=_has(j,"sixthsense") and first_hand and ((len(sp)==1 and not _debuffed(sp[0]) and not _stone(sp[0]) and str(getattr(sp[0],"rank","") or "")=="6") if explicit_play and sp else True);active=erosion or trading or six or (reduction>0 and d.rank>=BondRank.R2);return _finish(d,active,reduction>=12 and (erosion or trading or six))
def realize_deck_growth(d,s):
 j=list(getattr(s,"jokers",()) or ());deck=_cards(s,"owned_deck","deck");growth=max(0,len(deck)-52) if deck else int(getattr(s,"permanent_cards_added",0) or 0);hologram=_has(j,"hologram") and growth>0;pending=getattr(s,"blind_selection_pending",None);cert=_has(j,"certificate") and (bool(pending) if pending is not None else True);marble=_has(j,"marblejoker") and (bool(pending) if pending is not None else True);first=bool(getattr(s,"first_hand_available",int(getattr(s,"hands_played_this_round",0) or 0)==0));explicit=any(hasattr(s,n) for n in ("cards_to_play","scoring_cards","played_cards","current_played_cards"));sp=_cards(s,"cards_to_play","selected_cards");dna=_has(j,"dna") and first and ((len(sp)==1 and not _debuffed(sp[0])) if explicit and sp else True);active=hologram or cert or marble or dna or (growth>0 and d.rank>=BondRank.R2);return _finish(d,active,growth>=12 and (hologram or cert or marble or dna))
def realize_discard(d,s):
 j=list(getattr(s,"jokers",()) or ());left=int(getattr(s,"discards_left",getattr(s,"discards_remaining",0)) or 0)
 if left<=0:return _finish(d,False)
 explicit=any(hasattr(s,n) for n in ("discarded_cards","current_discard_cards","cards_to_discard"));cards=_cards(s,"discarded_cards","current_discard_cards","cards_to_discard")
 if not explicit:return _finish(d,_has(j,"yorick","castle","mailinrebate","facelessjoker","hittheroad"))
 if not cards:return _finish(d,False)
 live=[c for c in cards if not _debuffed(c)];par=_has(j,"pareidolia");faces=len(live) if par else sum(1 for c in live if not _stone(c) and str(getattr(c,"rank","") or "").upper() in {"J","Q","K"});jacks=sum(1 for c in live if not _stone(c) and str(getattr(c,"rank","") or "").upper()=="J");rank=str(getattr(s,"mail_in_rebate_rank",getattr(s,"rebate_rank","")) or "").upper();reb=bool(rank) and any(not _stone(c) and str(getattr(c,"rank","") or "").upper()==rank for c in live);suit=str(getattr(s,"castle_suit",getattr(s,"castle_target_suit","")) or "").lower();castle=bool(suit) and any(not _stone(c) and (str(getattr(c,"suit","") or "").lower()==suit or str(getattr(c,"enhancement","") or "").lower()=="wild") for c in live);src=sum((_has(j,"yorick"),_has(j,"facelessjoker") and faces>=3,_has(j,"hittheroad") and jacks>0,_has(j,"mailinrebate") and reb,_has(j,"castle") and castle));return _finish(d,src>0,src>=2)
CONTRACT_COMPAT_REALIZERS={"deck_thinning":realize_deck_thinning,"deck_growth":realize_deck_growth,"discard":realize_discard}
