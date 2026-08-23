from __future__ import annotations
from dataclasses import replace
from typing import Any,Iterable
from games.balatro.bonds.mechanical_roles import enrich_development
from games.balatro.bonds.model import BondDevelopment,BondRank,BondRealization

def _name(value):
 raw=value if isinstance(value,str) else getattr(value,"name",None) or value.__class__.__name__;return "".join(ch for ch in str(raw).lower() if ch.isalnum())
def _has(values,*tokens):
 names={_name(v) for v in values};return any(any(t in n for n in names) for t in tokens)
def _cards(state,*names):
 for n in names:
  if hasattr(state,n):return list(getattr(state,n,None) or ())
 return []
def _jokers(state):return list(getattr(state,"jokers",()) or ())
def _stone(c):return bool(getattr(c,"is_stone",False)) or str(getattr(c,"enhancement","") or "").lower()=="stone"
def _debuffed(c):return bool(getattr(c,"debuffed",False) or getattr(c,"is_debuffed",False))
def _finish(dev,active,strong=False):
 dev=enrich_development(dev)
 if not dev.unlocked or dev.rank in (BondRank.LOCKED,BondRank.R0):return replace(dev,realization=BondRealization.DORMANT)
 if not active:return replace(dev,realization=BondRealization.PARTIAL)
 return replace(dev,realization=BondRealization.MATURE if strong and dev.rank>=BondRank.R4 else BondRealization.ACTIVE)
def realize_burnt(dev,state):
 left=int(getattr(state,"discards_left",getattr(state,"discards_remaining",0)) or 0);used=int(getattr(state,"discards_used_this_round",0) or 0);first=bool(getattr(state,"first_discard_available",left>0 and used==0));target=dev.target or str(getattr(state,"target_hand","HIGH_CARD") or "HIGH_CARD");return _finish(dev,first and bool(target),first and bool(target) and dev.rank>=BondRank.R4)
def realize_cash(dev,state):
 money=int(getattr(state,"money",0) or 0);j=_jokers(state);hand=_cards(state,"hand","current_hand","cards_in_hand");deck_known=hasattr(state,"owned_deck") or hasattr(state,"deck");deck=_cards(state,"owned_deck","deck");par=_has(j,"pareidolia");pay=_has(j,"bull","bootstraps");un=_has(j,"rocket","goldenjoker");interest=_has(j,"tothemoon") and money>=5;faces=bool(hand) if par else any(not _debuffed(c) and not _stone(c) and str(getattr(c,"rank","") or "").upper() in {"J","Q","K"} for c in hand);parking=_has(j,"reservedparking") and faces;cloud=_has(j,"cloud9") and ((not deck_known) or any(not _stone(c) and str(getattr(c,"rank","") or "").upper()=="9" for c in deck));hist=getattr(state,"unique_planets_used",getattr(state,"satellite_planets_used",None));sat=_has(j,"satellite") and (hist is None or int(hist or 0)>0);src=sum((un,interest,parking,cloud,sat));return _finish(dev,(pay and money>=25) or src>0,(pay and money>=75) or src>=2 or (src>0 and money>=50))
def realize_no_discard(dev,state):
 j=_jokers(state);n=sum(1 for t in ("greenjoker","burglar","delayedgratification","ramen","banner") if _has(j,t));d=int(getattr(state,"discards_used_this_round",0) or 0);return _finish(dev,n>0 and d==0,n>=2 and d==0)
def realize_tarot(dev,state):return _finish(dev,False)
def realize_planet(dev,state):return _finish(dev,False)
def realize_discard(dev,state):
 j=_jokers(state);left=int(getattr(state,"discards_left",getattr(state,"discards_remaining",0)) or 0)
 if left<=0:return _finish(dev,False)
 explicit=any(hasattr(state,n) for n in ("discarded_cards","current_discard_cards","cards_to_discard"));d=_cards(state,"discarded_cards","current_discard_cards","cards_to_discard")
 if not explicit:return _finish(dev,_has(j,"yorick","castle","mailinrebate","facelessjoker","hittheroad"))
 if not d:return _finish(dev,False)
 live=[c for c in d if not _debuffed(c)];par=_has(j,"pareidolia");faces=len(live) if par else sum(1 for c in live if not _stone(c) and str(getattr(c,"rank","") or "").upper() in {"J","Q","K"});jacks=sum(1 for c in live if not _stone(c) and str(getattr(c,"rank","") or "").upper()=="J");rank=str(getattr(state,"mail_in_rebate_rank",getattr(state,"rebate_rank","")) or "").upper();reb=bool(rank) and any(not _stone(c) and str(getattr(c,"rank","") or "").upper()==rank for c in live);suit=str(getattr(state,"castle_suit",getattr(state,"castle_target_suit","")) or "").lower();castle=bool(suit) and any(not _stone(c) and (str(getattr(c,"suit","") or "").lower()==suit or str(getattr(c,"enhancement","") or "").lower()=="wild") for c in live);src=sum((_has(j,"yorick"),_has(j,"facelessjoker") and faces>=3,_has(j,"hittheroad") and jacks>0,_has(j,"mailinrebate") and reb,_has(j,"castle") and castle));return _finish(dev,src>0,src>=2)
def realize_blind_skip(dev,state):
 a=_has(_jokers(state),"throwback");n=int(getattr(state,"blinds_skipped",0) or 0);return _finish(dev,a,a and n>=5)
def realize_sell_value(dev,state):
 total=int(getattr(state,"joker_sell_value_total",0) or 0);a=_has(_jokers(state),"swashbuckler") and total>0;return _finish(dev,a,a and total>=35)
def realize_joker_sacrifice(dev,state):
 j=_jokers(state);i=next((i for i,x in enumerate(j) if "ceremonialdagger" in _name(x)),None);target=i is not None and i+1<len(j);fodder=target and (bool(getattr(state,"sacrificable_joker_available",False)) or "riffraff" in _name(j[i+1]));kind=_name(getattr(state,"blind_type",getattr(state,"blind_kind","")));boss=bool(getattr(state,"is_boss_blind",False)) or "boss" in kind;mad=_has(j,"madness");pending=bool(getattr(state,"blind_selection_pending",True));a=fodder or (mad and pending and not boss);return _finish(dev,a,a and int(getattr(state,"jokers_destroyed",0) or 0)>=6)
def realize_card_destruction(dev,state):
 j=_jokers(state);hand=_cards(state,"hand","current_hand","cards_in_hand");fd=bool(getattr(state,"first_discard_available",int(getattr(state,"discards_used_this_round",0) or 0)==0));fh=bool(getattr(state,"first_hand_available",int(getattr(state,"hands_played_this_round",0) or 0)==0));explicit_discard=any(hasattr(state,n) for n in ("cards_to_discard","selected_cards"));explicit_play=any(hasattr(state,n) for n in ("cards_to_play","scoring_cards","played_cards","current_played_cards"));sd=_cards(state,"cards_to_discard","selected_cards");sp=_cards(state,"cards_to_play","selected_cards");tr=_has(j,"tradingcard") and fd and ((len(sd)==1) if explicit_discard else bool(hand));six_pool=sp if explicit_play and sp else hand;six=_has(j,"sixthsense") and fh and (len(sp)==1 and not _debuffed(sp[0]) and not _stone(sp[0]) and str(getattr(sp[0],"rank","") or "")=="6" if explicit_play and sp else any(not _debuffed(c) and not _stone(c) and str(getattr(c,"rank","") or "")=="6" for c in six_pool));raw=getattr(state,"scoring_cards",None);pool=list(raw or ()) if raw is not None else (_cards(state,"played_cards","current_played_cards") or hand);glass=_has(j,"glassjoker") and any(not _debuffed(c) and str(getattr(c,"enhancement","") or "").lower()=="glass" for c in pool);canio=_has(j,"canio") and int(getattr(state,"face_cards_destroyed",getattr(state,"canio_face_cards_destroyed",getattr(state,"canio_triggers",0))) or 0)>0;a=tr or six or glass or canio;return _finish(dev,a,sum((tr,six,glass,canio))>=2)
def realize_hand_repetition(dev,state):
 j=_jokers(state);cur=str(getattr(state,"current_hand_type",getattr(state,"last_hand_type","")) or "").upper().replace(" ","_");counts=getattr(state,"round_hand_play_counts",None);counts=(counts if isinstance(counts,dict) and counts else getattr(state,"hand_play_counts",{}) or {});norm={str(k).upper().replace(" ","_"):int(v or 0) for k,v in counts.items()};prev=str(getattr(state,"previous_hand_type","") or "").upper().replace(" ","_");played_cards=_cards(state,"scoring_cards","played_cards","current_played_cards");explicit_play=any(hasattr(state,n) for n in ("scoring_cards","played_cards","current_played_cards"));prior=norm.get(cur,0) if cur else 0
 if explicit_play and played_cards and norm:prior=max(0,prior-1)
 repeated=bool(cur) and (prior>0 if norm else cur==prev);cardsharp=_has(j,"cardsharp") and repeated;supernova=_has(j,"supernova") and bool(cur) and (bool(played_cards) if explicit_play else True);a=cardsharp or supernova;return _finish(dev,a,a and norm.get(cur,0)>=18)
def realize_enhanced_cards(dev,state):
 if not _has(_jokers(state),"driverslicense"):return _finish(dev,False)
 n=sum(1 for c in _cards(state,"owned_deck","deck") if str(getattr(c,"enhancement","") or "").strip());return _finish(dev,n>=16,n>=16)
def realize_vampire(dev,state):
 j=_jokers(state);vi=next((i for i,x in enumerate(j) if "vampire" in _name(x)),None)
 if vi is None:return _finish(dev,False)
 hand=_cards(state,"hand","current_hand","cards_in_hand");deck=_cards(state,"owned_deck","deck");has_scoring=hasattr(state,"scoring_cards");sc=_cards(state,"scoring_cards") if has_scoring else _cards(state,"played_cards","current_played_cards");mi=next((i for i,x in enumerate(j) if "midasmask" in _name(x)),None);par=_has(j,"pareidolia")
 if has_scoring:
  feed=sum(1 for c in sc if not _debuffed(c) and str(getattr(c,"enhancement","") or "").strip())
  if sc:
   renew=mi is not None and mi<vi and any(not _debuffed(c) and (par or (not _stone(c) and str(getattr(c,"rank","") or "").upper() in {"J","Q","K"})) for c in sc)
  else:
   renew=mi is not None and any(not _debuffed(c) and (par or (not _stone(c) and str(getattr(c,"rank","") or "").upper() in {"J","Q","K"})) for c in (hand or deck))
 else:
  pool=sc or hand or deck;feed=sum(1 for c in pool if not _debuffed(c) and str(getattr(c,"enhancement","") or "").strip());renew=mi is not None and any(not _debuffed(c) and (par or (not _stone(c) and str(getattr(c,"rank","") or "").upper() in {"J","Q","K"})) for c in pool)
 a=feed>0 or renew;return _finish(dev,a,feed>=2 or (renew and int(getattr(state,"vampire_enhancements_consumed",0) or 0)>=15))
ENGINE_REALIZERS={"burnt":realize_burnt,"cash":realize_cash,"no_discard":realize_no_discard,"tarot":realize_tarot,"planet":realize_planet,"discard":realize_discard,"blind_skip":realize_blind_skip,"sell_value":realize_sell_value,"joker_sacrifice":realize_joker_sacrifice,"card_destruction":realize_card_destruction,"hand_repetition":realize_hand_repetition,"enhanced_cards":realize_enhanced_cards,"vampire":realize_vampire}
def realize_engine_family(dev,state):
 fn=ENGINE_REALIZERS.get(dev.bond_id);return enrich_development(dev) if fn is None else fn(dev,state)