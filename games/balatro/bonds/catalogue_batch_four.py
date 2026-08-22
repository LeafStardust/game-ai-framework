from __future__ import annotations
from typing import Any,Iterable
from games.balatro.bonds.model import BondContribution,BondDevelopment,BondRank,BondRealization

def _name(value:Any)->str:
 raw=value if isinstance(value,str) else getattr(value,"name",None) or value.__class__.__name__;return "".join(ch for ch in str(raw).lower() if ch.isalnum())
def _contains(values:Iterable[Any],*tokens:str)->bool:
 names={_name(v) for v in values};return any(any(t in n for n in names) for t in tokens)
def _deck(state:Any)->list[Any]:
 owned=getattr(state,"owned_deck",None);return list(owned) if owned is not None else list(getattr(state,"deck",()) or ())
def _band(value:int,bands:tuple[tuple[int,float],...])->float:
 out=0.0
 for threshold,score in bands:
  if value>=threshold:out=score
  else:break
 return out
def _rank(total:float,thresholds:dict[BondRank,float])->tuple[BondRank,float|None]:
 rank=BondRank.R0
 for c in (BondRank.R1,BondRank.R2,BondRank.R3,BondRank.R4,BondRank.R5):
  if total>=thresholds[c]:rank=c
  else:return rank,thresholds[c]
 return BondRank.R5,None
def _finish(bond_id:str,parts:list[BondContribution],thresholds:dict[BondRank,float],*,target:str|None=None)->BondDevelopment:
 total=sum(p.value for p in parts);rank,nxt=_rank(total,thresholds);return BondDevelopment(bond_id=bond_id,unlocked=True,contribution=total,rank=rank,next_rank_threshold=nxt,contributions=tuple(parts),target=target,realization=BondRealization.DORMANT if rank==BondRank.R0 else BondRealization.PARTIAL)
def _joker_parts(jokers:list[Any],specs:tuple[tuple[str,float,tuple[str,...]],...])->list[BondContribution]:return [BondContribution(label,value) for label,value,tokens in specs if _contains(jokers,*tokens)]
RANK_THRESHOLDS={BondRank.R1:4.0,BondRank.R2:9.0,BondRank.R3:15.0,BondRank.R4:22.0,BondRank.R5:30.0};CONSUMABLE_THRESHOLDS=dict(RANK_THRESHOLDS)
def _rank_density(state:Any,ranks:set[str])->float:return _band(sum(1 for c in _deck(state) if str(getattr(c,"rank","") or "").upper() in ranks),((4,1.0),(6,3.0),(9,5.0),(13,7.0),(18,9.0)))
def _rank_bond(state:Any,bond_id:str,ranks:set[str],specs:tuple[tuple[str,float,tuple[str,...]],...])->BondDevelopment:
 parts=_joker_parts(list(getattr(state,"jokers",()) or ()),specs);density=_rank_density(state,ranks)
 if density:parts.append(BondContribution(f"{bond_id} rank density",density))
 return _finish(bond_id,parts,RANK_THRESHOLDS,target="/".join(sorted(ranks)))
KINGS_THRESHOLDS=RANK_THRESHOLDS;KINGS_POLICIES={BondRank.R1:("recognize_king_payoff",),BondRank.R2:("prefer_king_density_and_preservation",),BondRank.R3:("actively_shape_deck_toward_kings",),BondRank.R4:("eligible_as_power_engine_support",),BondRank.R5:("capstone_king_commitment",)}
def evaluate_kings_bond(state:Any)->BondDevelopment:return _rank_bond(state,"kings",{"K"},(("Baron",7.0,("baronjoker","baron")),("Triboulet",6.0,("triboulet",))))
QUEENS_THRESHOLDS=RANK_THRESHOLDS;QUEENS_POLICIES={BondRank.R1:("recognize_queen_payoff",),BondRank.R2:("prefer_queen_density_and_preservation",),BondRank.R3:("actively_shape_deck_toward_queens",),BondRank.R4:("eligible_as_power_engine_support",),BondRank.R5:("capstone_queen_commitment",)}
def evaluate_queens_bond(state:Any)->BondDevelopment:return _rank_bond(state,"queens",{"Q"},(("Shoot the Moon",6.0,("shootthemoon",)),("Triboulet",5.0,("triboulet",))))
JACKS_THRESHOLDS=RANK_THRESHOLDS;JACKS_POLICIES={BondRank.R1:("recognize_jack_payoff",),BondRank.R2:("prefer_jack_density_when_supported",),BondRank.R3:("actively_shape_deck_toward_jacks",),BondRank.R4:("eligible_as_power_engine_support",),BondRank.R5:("capstone_jack_commitment",)}
def evaluate_jacks_bond(state:Any)->BondDevelopment:return _rank_bond(state,"jacks",{"J"},(("Hit the Road",7.0,("hittheroad",)),))
TAROT_THRESHOLDS=CONSUMABLE_THRESHOLDS;TAROT_POLICIES={BondRank.R1:("recognize_tarot_generation_and_use",),BondRank.R2:("prefer_tarot_access_when_deck_shaping_is_useful",),BondRank.R3:("actively_use_tarots_to_shape_combined_build",),BondRank.R4:("eligible_as_deck_shaping_resource_engine",),BondRank.R5:("capstone_tarot_infrastructure",)}
def evaluate_tarot_bond(state:Any)->BondDevelopment:
 jokers=list(getattr(state,"jokers",()) or ());vouchers=list(getattr(state,"vouchers",()) or ());parts=_joker_parts(jokers,(("Cartomancer",6.0,("cartomancer",)),("Vagabond",5.0,("vagabond",)),("Hallucination",4.0,("hallucination",)),("Fortune Teller",4.0,("fortuneteller",)),("Superposition",2.0,("superposition",))))
 if _contains(vouchers,"tarotmerchant"):parts.append(BondContribution("Tarot Merchant",4.0))
 if _contains(vouchers,"tarottycoon"):parts.append(BondContribution("Tarot Tycoon",6.0))
 return _finish("tarot",parts,TAROT_THRESHOLDS)
PLANET_THRESHOLDS=CONSUMABLE_THRESHOLDS;PLANET_POLICIES={BondRank.R1:("recognize_planet_generation_and_hand_leveling",),BondRank.R2:("prefer_planet_access_for_relevant_hand_bonds",),BondRank.R3:("actively_reinforce_selected_hand_specialization",),BondRank.R4:("eligible_as_hand_level_resource_engine",),BondRank.R5:("capstone_planet_infrastructure",)}
def evaluate_planet_bond(state:Any)->BondDevelopment:
 jokers=list(getattr(state,"jokers",()) or ());vouchers=list(getattr(state,"vouchers",()) or ());parts=_joker_parts(jokers,(("Constellation",6.0,("constellation",)),("Astronomer",4.0,("astronomer",)),("Space Joker",3.0,("spacejoker",))))
 if _contains(vouchers,"telescope"):parts.append(BondContribution("Telescope",5.0))
 if _contains(vouchers,"planetmerchant"):parts.append(BondContribution("Planet Merchant",4.0))
 if _contains(vouchers,"planettycoon"):parts.append(BondContribution("Planet Tycoon",6.0))
 blue=sum(1 for c in _deck(state) if str(getattr(c,"seal","") or "").lower()=="blue");score=_band(blue,((1,1.0),(2,3.0),(4,5.0),(7,7.0)))
 if score:parts.append(BondContribution("Blue Seal Planet infrastructure",score))
 return _finish("planet",parts,PLANET_THRESHOLDS)
BATCH_FOUR_EVALUATORS={"kings":evaluate_kings_bond,"queens":evaluate_queens_bond,"jacks":evaluate_jacks_bond,"tarot":evaluate_tarot_bond,"planet":evaluate_planet_bond}
