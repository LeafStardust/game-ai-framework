from __future__ import annotations

from dataclasses import replace
from typing import Any

from games.balatro.bonds.mechanical_roles import enrich_development
from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization


def _name(value: Any) -> str:
    raw = value if isinstance(value, str) else getattr(value, "name", None) or value.__class__.__name__
    return "".join(ch for ch in str(raw).lower() if ch.isalnum())


def _has(values, *tokens: str) -> bool:
    names = {_name(v) for v in values}
    return any(any(token in name for name in names) for token in tokens)


def _cards(state: Any, *names: str) -> list[Any]:
    for name in names:
        value = getattr(state, name, None)
        if value is not None:
            return list(value or ())
    return []


def _finish(dev: BondDevelopment, active: bool, strong: bool = False) -> BondDevelopment:
    dev = enrich_development(dev)
    if not dev.unlocked or dev.rank in (BondRank.LOCKED, BondRank.R0):
        return replace(dev, realization=BondRealization.DORMANT)
    if not active:
        return replace(dev, realization=BondRealization.PARTIAL)
    if strong and dev.rank >= BondRank.R4:
        return replace(dev, realization=BondRealization.MATURE)
    return replace(dev, realization=BondRealization.ACTIVE)


def _known_hand_type(state: Any) -> str:
    for field in ("current_hand_type", "selected_hand_type", "best_hand_type", "hand_type"):
        value = getattr(state, field, None)
        if value:
            return str(value).upper().replace(" ", "_")
    return ""


def realize_tarot_triggered(dev: BondDevelopment, state: Any) -> BondDevelopment:
    jokers = list(getattr(state, "jokers", ()) or ())
    vouchers = list(getattr(state, "vouchers", ()) or ())
    consumables = _cards(state, "consumables", "consumable_cards")
    scoring_raw = getattr(state, "scoring_cards", None)
    scoring = list(scoring_raw or ()) if scoring_raw is not None else _cards(state, "cards_to_play", "selected_cards", "played_cards")

    tarot_in_hand = any("tarot" in _name(c) or str(getattr(c, "set", "")).lower() == "tarot" for c in consumables)
    shop_infrastructure = _has(vouchers, "tarotmerchant", "tarottycoon")

    blind_pending = bool(getattr(state, "blind_selection_pending", False))
    cartomancer = _has(jokers, "cartomancer") and blind_pending

    money = int(getattr(state, "money", 0) or 0)
    vagabond = _has(jokers, "vagabond") and money <= 4 and bool(scoring)

    booster_open = bool(
        getattr(state, "booster_pack_open", False)
        or getattr(state, "booster_open", False)
        or getattr(state, "booster_pack_pending", False)
    )
    hallucination = _has(jokers, "hallucination") and booster_open

    tarot_used = int(getattr(state, "tarot_cards_used", getattr(state, "tarots_used", 0)) or 0)
    fortune_teller = _has(jokers, "fortuneteller") and tarot_used > 0

    hand_type = _known_hand_type(state)
    straight = hand_type in {"STRAIGHT", "STRAIGHT_FLUSH"}
    ace_in_scoring = any(str(getattr(c, "rank", "") or "").upper() == "A" for c in scoring)
    superposition = _has(jokers, "superposition") and straight and ace_in_scoring

    eight_scoring = any(str(getattr(c, "rank", "") or "").upper() in {"8", "EIGHT"} for c in scoring)
    eight_ball = _has(jokers, "8ball", "eightball") and eight_scoring

    sources = sum(
        (
            tarot_in_hand,
            shop_infrastructure,
            cartomancer,
            vagabond,
            hallucination,
            fortune_teller,
            superposition,
            eight_ball,
        )
    )
    return _finish(dev, sources > 0, sources >= 2)


TRIGGERED_ENGINE_OVERRIDES = {"tarot": realize_tarot_triggered}
