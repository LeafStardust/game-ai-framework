from __future__ import annotations

from dataclasses import replace
from typing import Any

from games.balatro.bonds.mechanical_roles import enrich_development
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization


def _name(value: Any) -> str:
    raw = value if isinstance(value, str) else getattr(value, "name", None) or value.__class__.__name__
    return "".join(ch for ch in str(raw).lower() if ch.isalnum())

def _cards(state: Any, *names: str) -> list[Any]:
    for name in names:
        value = getattr(state, name, None)
        if value is not None:return list(value or ())
    return []
def _jokers(state: Any) -> list[Any]:return list(getattr(state, "jokers", ()) or ())
def _stone(card: Any) -> bool:return bool(getattr(card, "is_stone", False)) or str(getattr(card, "enhancement", "") or "").lower() == "stone"
def _debuffed(card:Any)->bool:return bool(getattr(card,"debuffed",False) or getattr(card,"is_debuffed",False))
def _eternal(joker: Any) -> bool:
    if bool(getattr(joker, "eternal", False) or getattr(joker, "is_eternal", False)):return True
    sticker = str(getattr(joker, "sticker", getattr(joker, "stake_sticker", "")) or "").lower();return "eternal" in sticker
def _finish(dev: BondDevelopment, active: bool, strong: bool = False) -> BondDevelopment:
    dev = enrich_development(dev)
    if not dev.unlocked or dev.rank in (BondRank.LOCKED, BondRank.R0):return replace(dev, realization=BondRealization.DORMANT)
    if not active:return replace(dev, realization=BondRealization.PARTIAL)
    if strong and dev.rank >= BondRank.R4:return replace(dev, realization=BondRealization.MATURE)
    return replace(dev, realization=BondRealization.ACTIVE)

def realize_joker_sacrifice_ordered(dev: BondDevelopment, state: Any) -> BondDevelopment:
    jokers = _jokers(state);dagger_index = next((i for i, joker in enumerate(jokers) if "ceremonialdagger" in _name(joker)), None);dagger_target = jokers[dagger_index + 1] if dagger_index is not None and dagger_index + 1 < len(jokers) else None;dagger_live = dagger_target is not None and not _eternal(dagger_target)
    madness = any("madness" in _name(joker) for joker in jokers);pending = bool(getattr(state, "blind_selection_pending", True));blind = ""
    for field in ("selected_blind_type", "current_blind_type", "blind_type", "blind_kind"):
        value = getattr(state, field, None)
        if value:blind = _name(value);break
    madness_can_trigger = pending and "boss" not in blind;active = dagger_live or (madness and madness_can_trigger);return _finish(dev, active, active and int(getattr(state, "jokers_destroyed", 0) or 0) >= 6)

def realize_card_destruction_scoring(dev: BondDevelopment, state: Any) -> BondDevelopment:
    jokers=_jokers(state);names={_name(joker) for joker in jokers};first_discard=bool(getattr(state,"first_discard_available",int(getattr(state,"discards_used_this_round",0) or 0)==0));first_hand=bool(getattr(state,"first_hand_available",int(getattr(state,"hands_played_this_round",0) or 0)==0));selected_discard=_cards(state,"selected_cards","cards_to_discard");selected_play=_cards(state,"cards_to_play","selected_cards")
    trading=any("tradingcard" in name for name in names) and first_discard and len(selected_discard)==1
    sixth=any("sixthsense" in name for name in names) and first_hand and len(selected_play)==1 and not _debuffed(selected_play[0]) and not _stone(selected_play[0]) and str(getattr(selected_play[0],"rank","") or "")=="6"
    scoring_raw=getattr(state,"scoring_cards",None);glass_pool=list(scoring_raw or ()) if scoring_raw is not None else _cards(state,"cards_to_play","selected_cards","hand","current_hand");glass=any("glassjoker" in name for name in names) and any(not _debuffed(card) and str(getattr(card,"enhancement","") or "").lower()=="glass" for card in glass_pool);canio=any("canio" in name for name in names) and int(getattr(state,"cards_destroyed",0) or 0)>0;active=trading or sixth or glass or canio;return _finish(dev,active,sum((trading,sixth,glass,canio))>=2)

def realize_vampire_ordered(dev: BondDevelopment, state: Any) -> BondDevelopment:
    jokers=_jokers(state);vampire_index=next((i for i,joker in enumerate(jokers) if "vampire" in _name(joker)),None)
    if vampire_index is None:return _finish(dev,False)
    scoring_raw=getattr(state,"scoring_cards",None)
    if scoring_raw is not None:scoring=list(scoring_raw or ());feed_cards=scoring
    else:scoring=_cards(state,"played_cards","current_played_cards");feed_cards=scoring or _cards(state,"hand","current_hand","cards_in_hand")
    feed=sum(1 for card in feed_cards if not _debuffed(card) and str(getattr(card,"enhancement","") or "").strip());midas_index=next((i for i,joker in enumerate(jokers) if "midasmask" in _name(joker)),None);midas_before_vampire=midas_index is not None and midas_index<vampire_index;pareidolia=any("pareidolia" in _name(joker) for joker in jokers);face_pool=scoring if scoring_raw is not None else (scoring or _cards(state,"hand","current_hand","cards_in_hand"));interactive=[card for card in face_pool if not _debuffed(card)];face_available=bool(interactive) if pareidolia else any(not _stone(card) and str(getattr(card,"rank","") or "").upper() in {"J","Q","K"} for card in interactive);same_hand_midas_feed=midas_before_vampire and face_available;active=feed>0 or same_hand_midas_feed;strong=feed>=2 or (same_hand_midas_feed and int(getattr(state,"vampire_enhancements_consumed",0) or 0)>=15);return _finish(dev,active,strong)

ENGINE_AUDIT_REALIZERS={"joker_sacrifice":realize_joker_sacrifice_ordered,"card_destruction":realize_card_destruction_scoring,"vampire":realize_vampire_ordered}
