from __future__ import annotations

"""Canonical strategic adjustment for already-positive pack selections.

The base pack policy remains authoritative for legality, literal value, stochastic
expectations, target selection, and Skip. This wrapper only projects persistent
build changes for playing-card and Planet picks and adds a conservative canonical
``StrategyDelta`` term. The historical StrategyPlan/Bond-goal matcher has been
removed; the installer name and a small set of pure helper functions remain
temporarily for package/test compatibility until the Phase K cleanup gate.
"""

from games.balatro.bonds.strategy_delta import strategy_delta_from_states
from games.balatro.card import BalatroCard
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore
from games.balatro.planets import PLANET_CARDS


_PACK_STRATEGY_WEIGHT = 0.10
def _token(value) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _choice(action):
    choice = getattr(action, "target", None)
    if choice is None:
        return "", "", {}
    return (
        str(getattr(choice, "kind", "") or "").upper(),
        str(getattr(choice, "label", "") or ""),
        dict(getattr(choice, "data", {}) or {}),
    )


def _normalize_enhancement(value: object) -> str | None:
    token = _token(value)
    aliases = {
        "bonus": "Bonus",
        "bonuscard": "Bonus",
        "mbonus": "Bonus",
        "mult": "Mult",
        "multcard": "Mult",
        "mmult": "Mult",
        "wild": "Wild",
        "wildcard": "Wild",
        "mwild": "Wild",
        "glass": "Glass",
        "glasscard": "Glass",
        "mglass": "Glass",
        "steel": "Steel",
        "steelcard": "Steel",
        "msteel": "Steel",
        "stone": "Stone",
        "stonecard": "Stone",
        "mstone": "Stone",
        "gold": "Gold",
        "goldcard": "Gold",
        "mgold": "Gold",
        "lucky": "Lucky",
        "luckycard": "Lucky",
        "mlucky": "Lucky",
    }
    return aliases.get(token)


def _normalize_seal(value: object) -> str | None:
    token = _token(value)
    return {
        "gold": "Gold",
        "goldseal": "Gold",
        "red": "Red",
        "redseal": "Red",
        "blue": "Blue",
        "blueseal": "Blue",
        "purple": "Purple",
        "purpleseal": "Purple",
    }.get(token)


def _playing_card_from_choice(data: dict) -> BalatroCard | None:
    value = data.get("value") or {}
    rank = value.get("rank") if isinstance(value, dict) else None
    suit = value.get("suit") if isinstance(value, dict) else None
    rank = rank or data.get("rank")
    suit = suit or data.get("suit")
    if rank is None or suit is None:
        return None
    return BalatroCard(
        str(rank),
        str(suit),
        enhancement=_normalize_enhancement(
            data.get("enhancement") or data.get("ability_name")
        ),
        edition=(str(data.get("edition")).title() if data.get("edition") else None),
        seal=_normalize_seal(data.get("seal")),
        live_id=data.get("live_id"),
    )


def _planet_hand(label: str) -> str | None:
    target = _token(label)
    for planet in PLANET_CARDS.values():
        if _token(planet.name) == target:
            return str(planet.hand_type).upper()
    return None


def _project_pack_choice(state, action):
    kind, label, data = _choice(action)
    copy_method = getattr(state, "copy", None)
    if not callable(copy_method):
        return None
    projected = copy_method()

    if kind == "PLAYING_CARD":
        card = _playing_card_from_choice(data)
        if card is None:
            return None
        if getattr(projected, "owned_deck", None) is not None:
            projected.owned_deck = list(projected.owned_deck)
            projected.owned_deck.append(card)
        else:
            projected.deck = list(getattr(projected, "deck", ()) or ())
            projected.deck.append(card)
        return projected

    if kind == "PLANET":
        hand_type = _planet_hand(label)
        if hand_type is None:
            return None
        projected.hand_levels = dict(getattr(projected, "hand_levels", {}) or {})
        projected.hand_levels[hand_type] = int(projected.hand_levels.get(hand_type, 1) or 1) + 1
        return projected

    return None


def _strategy_adjustment(state, action) -> tuple[float, tuple[str, ...]]:
    projected = _project_pack_choice(state, action)
    if projected is None:
        return 0.0, ()
    try:
        delta = strategy_delta_from_states(state, projected)
    except (AttributeError, KeyError, TypeError, ValueError):
        return 0.0, ()
    weighted = _PACK_STRATEGY_WEIGHT * float(delta.value)
    if abs(weighted) <= 1e-12:
        return 0.0, ()
    return weighted, (
        f"canonical StrategyDelta={delta.value:+.3f}",
        f"raw BuildValue delta={delta.raw_delta:+.3f}",
        f"transition inertia={delta.transition_cost:.3f}",
        f"pack strategy weight={_PACK_STRATEGY_WEIGHT:.3f}",
        f"weighted strategic adjustment={weighted:+.3f}",
    )


def install_pack_strategy_delta_policy() -> None:
    """Install canonical projected StrategyDelta for persistent pack choices."""
    if getattr(BalatroPackPolicy, "_pack_strategy_delta_policy_installed", False):
        return
    original = BalatroPackPolicy.score_action

    def score_action(self, state, action):
        scored = original(self, state, action)
        # Strategy cannot make an illegal/deferred/non-positive pack option admissible.
        if scored.total <= 0.0:
            return scored
        adjustment, notes = _strategy_adjustment(state, scored.action)
        if not notes:
            return scored
        return PackActionScore(
            scored.action,
            float(scored.total) + adjustment,
            (
                *scored.notes,
                *notes,
                "base pack admission and literal mechanics remain authoritative",
            ),
        )

    BalatroPackPolicy.score_action = score_action
    BalatroPackPolicy._pack_strategy_delta_policy_installed = True
