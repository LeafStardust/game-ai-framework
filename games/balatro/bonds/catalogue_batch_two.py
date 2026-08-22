from __future__ import annotations
from typing import Any, Iterable
from games.balatro.bonds.model import BondContribution,BondDevelopment,BondRank,BondRealization

def _name(value:Any)->str:
 raw=value if isinstance(value,str) else getattr(value,"name",None) or value.__class__.__name__; return "".join(ch for ch in str(raw).lower() if ch.isalnum())
def _contains(values:Iterable[Any],*tokens:str)->bool:
 names={_name(v) for v in values}; return any(any(t in n for n in names) for t in tokens)
def _deck(state:Any)->list[Any]:
 owned=getattr(state,"owned_deck",None); return list(owned) if owned is not None else list(getattr(state,"deck",()) or ())
def _band(value:int,bands:tuple[tuple[int,float],...])->float:
 out=0.0
 for threshold,score in bands:
  if value>=threshold:out=score
  else:break
 return out
def _level(state:Any,hand:str)->int:return int((getattr(state,"hand_levels",{}) or {}).get(hand,1) or 1)
def _level_score(level:int)->float:return _band(level,((2,1.0),(4,3.0),(7,5.0),(11,7.0)))
def _rank(total:float,thresholds:dict[BondRank,float])->tuple[BondRank,float|None]:
 rank=BondRank.R0
 for c in (BondRank.R1,BondRank.R2,BondRank.R3,BondRank.R4,BondRank.R5):
  if total>=thresholds[c]:rank=c
  else:return rank,thresholds[c]
 return BondRank.R5,None
def _finish(bond_id:str,parts:list[BondContribution],thresholds:dict[BondRank,float],*,target:str|None=None)->BondDevelopment:
 total=sum(p.value for p in parts); rank,nxt=_rank(total,thresholds); return BondDevelopment(bond_id=bond_id,unlocked=True,contribution=total,rank=rank,next_rank_threshold=nxt,contributions=tuple(parts),target=target,realization=BondRealization.DORMANT if rank==BondRank.R0 else BondRealization.PARTIAL)
def _joker_parts(jokers:list[Any],specs:tuple[tuple[str,float,tuple[str,...]],...])->list[BondContribution]:return [BondContribution(label,value) for label,value,tokens in specs if _contains(jokers,*tokens)]
HAND_THRESHOLDS={BondRank.R1:4.0,BondRank.R2:8.0,BondRank.R3:13.0,BondRank.R4:19.0,BondRank.R5:26.0}
def _hand_bond(state:Any,bond_id:str,hand:str,specs:tuple[tuple[str,float,tuple[str,...]],...])->BondDevelopment:
 parts=_joker_parts(list(getattr(state,"jokers",()) or ()),specs); score=_level_score(_level(state,hand));
 if score:parts.append(BondContribution(f"{hand} permanent hand level",score))
 return _finish(bond_id,parts,HAND_THRESHOLDS,target=hand)
TWO_PAIR_THRESHOLDS=HAND_THRESHOLDS; TWO_PAIR_POLICIES={BondRank.R1:("recognize_two_pair_specialization",),BondRank.R2:("prefer_two_pair_consistency",),BondRank.R3:("actively_shape_scoring_around_two_pair",),BondRank.R4:("eligible_as_power_engine",),BondRank.R5:("capstone_two_pair_commitment",)}
def evaluate_two_pair_bond(state:Any)->BondDevelopment:return _hand_bond(state,"two_pair","TWO_PAIR",(("Spare Trousers",7.0,("sparetrousers",)),("Square Joker",3.0,("squarejoker",)),("Jolly Joker",2.0,("jollyjoker",)),("Sly Joker",2.0,("slyjoker",))))
THREE_KIND_THRESHOLDS=HAND_THRESHOLDS; THREE_KIND_POLICIES={BondRank.R1:("recognize_three_kind_specialization",),BondRank.R2:("prefer_rank_concentration",),BondRank.R3:("actively_shape_scoring_around_three_kind",),BondRank.R4:("eligible_as_power_engine",),BondRank.R5:("capstone_three_kind_commitment",)}
def evaluate_three_kind_bond(state:Any)->BondDevelopment:return _hand_bond(state,"three_kind","THREE_OF_A_KIND",(("The Trio",6.0,("thetrio",)),("Zany Joker",4.0,("zanyjoker",)),("Wily Joker",4.0,("wilyjoker",))))
FOUR_KIND_THRESHOLDS=HAND_THRESHOLDS; FOUR_KIND_POLICIES={BondRank.R1:("recognize_four_kind_specialization",),BondRank.R2:("prefer_deep_rank_concentration",),BondRank.R3:("actively_shape_deck_around_four_kind",),BondRank.R4:("eligible_as_power_engine",),BondRank.R5:("capstone_four_kind_commitment",)}
def evaluate_four_kind_bond(state:Any)->BondDevelopment:return _hand_bond(state,"four_kind","FOUR_OF_A_KIND",(("The Family",7.0,("thefamily",)),("Mad Joker",4.0,("madjoker",)),("Clever Joker",4.0,("cleverjoker",))))
STRAIGHT_THRESHOLDS=HAND_THRESHOLDS; STRAIGHT_POLICIES={BondRank.R1:("recognize_straight_specialization",),BondRank.R2:("prefer_straight_consistency",),BondRank.R3:("actively_shape_rank_spread_for_straights",),BondRank.R4:("eligible_as_power_engine",),BondRank.R5:("capstone_straight_commitment",)}
def evaluate_straight_bond(state:Any)->BondDevelopment:return _hand_bond(state,"straight","STRAIGHT",(("The Order",6.0,("theorder",)),("Crazy Joker",4.0,("crazyjoker",)),("Devious Joker",4.0,("deviousjoker",)),("Shortcut",5.0,("shortcut",)),("Four Fingers",3.0,("fourfingers",)),("Runner",4.0,("runner",)),("Superposition",2.0,("superposition",))))
FLUSH_THRESHOLDS=HAND_THRESHOLDS; FLUSH_POLICIES={BondRank.R1:("recognize_flush_specialization",),BondRank.R2:("prefer_suit_concentration",),BondRank.R3:("actively_shape_deck_toward_flush_consistency",),BondRank.R4:("eligible_as_power_engine",),BondRank.R5:("capstone_flush_commitment",)}
def evaluate_flush_bond(state:Any)->BondDevelopment:
 jokers=list(getattr(state,"jokers",()) or ());parts=_joker_parts(jokers,(("The Tribe",6.0,("thetribe",)),("Droll Joker",4.0,("drolljoker",)),("Crafty Joker",4.0,("craftyjoker",)),("Smeared Joker",5.0,("smearedjoker",)),("Four Fingers",3.0,("fourfingers",))))
 score=_level_score(_level(state,"FLUSH"));
 if score:parts.append(BondContribution("FLUSH permanent hand level",score))
 smeared=_contains(jokers,"smearedjoker","smeared");suits={}
 for c in _deck(state):
  enhancement=str(getattr(c,"enhancement","") or "").lower()
  if bool(getattr(c,"is_stone",False)) or enhancement=="stone":continue
  suit=str(getattr(c,"suit","") or "").lower()
  if enhancement=="wild":effective=("red","black") if smeared else ("hearts","diamonds","spades","clubs")
  elif smeared and suit in {"hearts","diamonds"}:effective=("red",)
  elif smeared and suit in {"spades","clubs"}:effective=("black",)
  else:effective=(suit,) if suit else ()
  for key in effective:suits[key]=suits.get(key,0)+1
 density=_band(max(suits.values(),default=0),((16,1.0),(20,3.0),(24,5.0),(30,7.0)))
 if density:parts.append(BondContribution("Dominant suit density",density))
 return _finish("flush",parts,FLUSH_THRESHOLDS,target="FLUSH")
PLAYED_RETRIGGER_THRESHOLDS={BondRank.R1:4.0,BondRank.R2:8.0,BondRank.R3:14.0,BondRank.R4:21.0,BondRank.R5:29.0}; PLAYED_RETRIGGER_POLICIES={BondRank.R1:("recognize_played_card_retrigger_value",),BondRank.R2:("prefer_retriggerable_scoring_cards",),BondRank.R3:("actively_shape_scoring_cards_for_retriggers",),BondRank.R4:("eligible_as_power_engine_support",),BondRank.R5:("capstone_played_retrigger_commitment",)}
def evaluate_played_retrigger_bond(state:Any)->BondDevelopment:
 parts=_joker_parts(list(getattr(state,"jokers",()) or ()),(("Sock and Buskin",6.0,("sockandbuskin",)),("Hack",6.0,("hackjoker","hack")),("Hanging Chad",6.0,("hangingchad",)),("Dusk",4.0,("duskjoker","dusk"))));red=sum(1 for c in _deck(state) if str(getattr(c,"seal","") or "").lower()=="red");score=_band(red,((1,1.0),(2,3.0),(4,5.0),(7,7.0)))
 if score:parts.append(BondContribution("Red Seal played-card infrastructure",score))
 return _finish("played_retrigger",parts,PLAYED_RETRIGGER_THRESHOLDS)
STONE_THRESHOLDS={BondRank.R1:4.0,BondRank.R2:8.0,BondRank.R3:13.0,BondRank.R4:19.0,BondRank.R5:26.0};STONE_POLICIES={BondRank.R1:("recognize_stone_card_value",),BondRank.R2:("prefer_stone_creation_when_compatible",),BondRank.R3:("actively_shape_deck_around_stone_density",),BondRank.R4:("eligible_as_power_engine_support",),BondRank.R5:("capstone_stone_commitment",)}
def evaluate_stone_bond(state:Any)->BondDevelopment:
 parts=_joker_parts(list(getattr(state,"jokers",()) or ()),(("Stone Joker",6.0,("stonejoker",)),("Marble Joker",5.0,("marblejoker",))));n=sum(1 for c in _deck(state) if str(getattr(c,"enhancement","") or "").lower()=="stone");score=_band(n,((1,1.0),(3,3.0),(6,6.0),(10,9.0)))
 if score:parts.append(BondContribution("Stone card density",score))
 return _finish("stone",parts,STONE_THRESHOLDS)
GOLD_ECONOMY_THRESHOLDS={BondRank.R1:4.0,BondRank.R2:8.0,BondRank.R3:13.0,BondRank.R4:19.0,BondRank.R5:26.0};GOLD_ECONOMY_POLICIES={BondRank.R1:("recognize_gold_card_economy",),BondRank.R2:("prefer_gold_creation_when_economy_matters",),BondRank.R3:("preserve_gold_cards_for_end_round_value",),BondRank.R4:("eligible_as_economy_engine",),BondRank.R5:("capstone_gold_economy_commitment",)}
def evaluate_gold_economy_bond(state:Any)->BondDevelopment:
 parts=_joker_parts(list(getattr(state,"jokers",()) or ()),(("Golden Ticket",5.0,("goldenticket",)),("Midas Mask",5.0,("midasmask",)),("Reserved Parking",2.0,("reservedparking",))));n=sum(1 for c in _deck(state) if str(getattr(c,"enhancement","") or "").lower()=="gold");score=_band(n,((1,1.0),(3,3.0),(6,6.0),(10,9.0)))
 if score:parts.append(BondContribution("Gold card density",score))
 return _finish("gold_economy",parts,GOLD_ECONOMY_THRESHOLDS)
DECK_THINNING_THRESHOLDS={BondRank.R1:4.0,BondRank.R2:8.0,BondRank.R3:13.0,BondRank.R4:19.0,BondRank.R5:26.0};DECK_THINNING_POLICIES={BondRank.R1:("recognize_deck_thinning_value",),BondRank.R2:("prefer_targeted_removal_of_low_value_cards",),BondRank.R3:("actively_improve_draw_density_through_removal",),BondRank.R4:("strongly_protect_concentrated_deck_shape",),BondRank.R5:("capstone_deck_thinning_commitment",)}
def evaluate_deck_thinning_bond(state:Any)->BondDevelopment:
 parts=_joker_parts(list(getattr(state,"jokers",()) or ()),(("Erosion",7.0,("erosionjoker","erosion")),("Trading Card",5.0,("tradingcard",)),("Sixth Sense",4.0,("sixthsense",))));reduction=max(0,52-len(_deck(state)));score=_band(reduction,((4,1.0),(8,3.0),(12,5.0),(18,7.0)))
 if score:parts.append(BondContribution("Permanent deck reduction",score))
 return _finish("deck_thinning",parts,DECK_THINNING_THRESHOLDS)
DECK_GROWTH_THRESHOLDS={BondRank.R1:4.0,BondRank.R2:8.0,BondRank.R3:13.0,BondRank.R4:19.0,BondRank.R5:26.0};DECK_GROWTH_POLICIES={BondRank.R1:("recognize_deck_growth_value",),BondRank.R2:("prefer_high_quality_additions_over_raw_bloat",),BondRank.R3:("actively_shape_added_cards_toward_build",),BondRank.R4:("eligible_as_growth_engine",),BondRank.R5:("capstone_deck_growth_commitment",)}
def evaluate_deck_growth_bond(state:Any)->BondDevelopment:
 parts=_joker_parts(list(getattr(state,"jokers",()) or ()),(("Certificate",5.0,("certificate",)),("DNA",6.0,("dnajoker","dna")),("Marble Joker",3.0,("marblejoker",)),("Hologram",4.0,("hologramjoker","hologram"))));growth=max(0,len(_deck(state))-52);score=_band(growth,((4,1.0),(8,3.0),(12,5.0),(18,7.0)))
 if score:parts.append(BondContribution("Permanent deck growth",score))
 return _finish("deck_growth",parts,DECK_GROWTH_THRESHOLDS)
BATCH_TWO_EVALUATORS={"two_pair":evaluate_two_pair_bond,"three_kind":evaluate_three_kind_bond,"four_kind":evaluate_four_kind_bond,"straight":evaluate_straight_bond,"flush":evaluate_flush_bond,"played_retrigger":evaluate_played_retrigger_bond,"stone":evaluate_stone_bond,"gold_economy":evaluate_gold_economy_bond,"deck_thinning":evaluate_deck_thinning_bond,"deck_growth":evaluate_deck_growth_bond}
