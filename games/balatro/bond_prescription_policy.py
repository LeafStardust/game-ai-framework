from __future__ import annotations

from dataclasses import replace
from typing import Any

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.motifs import MotifState
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore
from games.balatro.planets import PLANET_CARDS
from games.balatro.shop_utility_scale import ShopNormalizedUtility, ShopUtilityScale


_MAX_PACK_BONUS = 2.50
_MAX_SHOP_BONUS = 1.25

_PLANET_HAND_BY_NAME = {
    planet.name: planet.hand_type
    for planet in PLANET_CARDS.values()
}


def _name(value: Any) -> str:
    raw = (
        value
        if isinstance(value, str)
        else getattr(value, "name", None)
        or getattr(value, "label", None)
        or type(value).__name__
    )
    return str(raw)


def _active_motif_ids(state: Any) -> frozenset[str]:
    try:
        _, composition = evaluate_bond_composition(state)
    except (AttributeError, TypeError, ValueError):
        return frozenset()
    return frozenset(
        motif.motif_id
        for motif in composition.motifs
        if motif.state >= MotifState.ACTIVE
    )


def _burnt_target_hand(state: Any) -> str | None:
    try:
        developments, _ = evaluate_bond_composition(state)
    except (AttributeError, TypeError, ValueError):
        return None
    for development in developments:
        if development.bond_id == "burnt":
            target = getattr(development, "target", None)
            return str(target).upper() if target else None
    return None


def _rank(card: Any) -> str:
    value = str(getattr(card, "rank", "") or "").upper()
    aliases = {"KING": "K", "QUEEN": "Q", "JACK": "J", "ACE": "A"}
    return aliases.get(value, value)


def _enhancement(card: Any) -> str:
    return str(getattr(card, "enhancement", "") or "").lower()


def _seal(card: Any) -> str:
    return str(getattr(card, "seal", "") or "").upper()


def _choice_cards(action: Any) -> tuple[Any, ...]:
    return tuple(getattr(action, "cards", ()) or ())


def prescription_bonus(
    state: Any,
    *,
    kind: str,
    label: str,
    cards: tuple[Any, ...] = (),
    playing_card: Any | None = None,
) -> tuple[float, tuple[str, ...]]:
    """Return bounded motif-prescription value for an already-safe public option.

    This function never decides legality or autonomous safety. Callers must apply it
    only after their existing child policy has admitted/scored the option.
    """

    motifs = _active_motif_ids(state)
    if not motifs:
        return 0.0, ()

    kind = str(kind).upper()
    label = str(label)
    bonus = 0.0
    notes: list[str] = []

    def add(value: float, reason: str) -> None:
        nonlocal bonus
        bonus += float(value)
        notes.append(reason)

    # Baron/Mime/Steel: create Steel, create Red Seals, preserve/upgrade Kings and
    # reward already-composed King/Steel/Red-Seal playing cards.
    if "baron_mime_steel" in motifs:
        if kind == "TAROT" and label == "The Chariot":
            add(1.25, "Baron-Mime-Steel prescription: prefer Steel creation")
        if kind == "SPECTRAL" and label == "Deja Vu":
            add(1.10, "Baron-Mime-Steel prescription: prefer Red Seal creation")
        if playing_card is not None:
            if _rank(playing_card) == "K":
                add(0.70, "Baron-Mime-Steel prescription: preserve/acquire Kings")
            if _enhancement(playing_card) == "steel":
                add(0.90, "Baron-Mime-Steel prescription: acquire Steel cards")
            if _seal(playing_card) == "RED":
                add(0.70, "Baron-Mime-Steel prescription: acquire Red Seal cards")
        if cards and any(_rank(card) == "K" for card in cards):
            if label in {"The Chariot", "Deja Vu"}:
                add(0.50, "Baron-Mime-Steel prescription: target a King engine card")

    # Photograph + Hanging Chad: face-card scoring is the engine and Red Seal face
    # cards are especially compatible with repeated played-card triggers.
    if "photograph_hanging_chad" in motifs:
        if playing_card is not None and _rank(playing_card) in {"J", "Q", "K"}:
            add(0.65, "Photograph-Chad prescription: preserve/acquire face cards")
        if kind == "SPECTRAL" and label == "Deja Vu":
            add(0.75, "Photograph-Chad prescription: prefer Red Seal retrigger support")
        if cards and any(_rank(card) in {"J", "Q", "K"} for card in cards) and label == "Deja Vu":
            add(0.45, "Photograph-Chad prescription: place Red Seal on a face card")

    # Vampire + Midas: face cards are renewable feedstock; enhanced cards are fuel.
    if "vampire_midas" in motifs and playing_card is not None:
        if _rank(playing_card) in {"J", "Q", "K"}:
            add(0.60, "Vampire-Midas prescription: prefer renewable face-card feed")
        if _enhancement(playing_card):
            add(0.35, "Vampire-Midas prescription: enhanced card provides Vampire feedstock")

    # Burnt target leveling: target-hand Planets and Blue Seals are direct scaling
    # support. The exact target comes from the Burnt Bond evaluator, not a hardcoded
    # default hand.
    if "burnt_target_level" in motifs:
        target_hand = _burnt_target_hand(state)
        if kind == "PLANET" and target_hand and _PLANET_HAND_BY_NAME.get(label) == target_hand:
            add(1.50, f"Burnt prescription: Planet reinforces target hand {target_hand}")
        if kind == "SPECTRAL" and label == "Trance":
            add(0.80, "Burnt prescription: prefer Blue Seal leveling support")
        if playing_card is not None and _seal(playing_card) == "BLUE":
            add(0.65, "Burnt prescription: acquire Blue Seal support")

    # Hack low-rank retrigger engine: 2-5 are the trigger body and Red Seal stacks
    # another played-card retrigger on the same cards.
    if "low_rank_hack_retrigger" in motifs:
        if playing_card is not None and _rank(playing_card) in {"2", "3", "4", "5"}:
            add(0.70, "Hack prescription: preserve/acquire ranks 2-5")
        if kind == "SPECTRAL" and label == "Deja Vu":
            add(0.80, "Hack prescription: prefer Red Seal retrigger support")
        if cards and any(_rank(card) in {"2", "3", "4", "5"} for card in cards) and label == "Deja Vu":
            add(0.45, "Hack prescription: place Red Seal on a 2-5 trigger card")

    if bonus <= 0.0:
        return 0.0, ()
    return min(_MAX_PACK_BONUS, bonus), tuple(notes)


def _pack_choice_semantics(action: Any) -> tuple[str, str, Any | None]:
    choice = getattr(action, "target", None)
    if choice is None:
        return "", "", None
    kind = str(getattr(choice, "kind", "") or "").upper()
    label = str(getattr(choice, "label", "") or "")
    playing_card = None
    if kind == "PLAYING_CARD":
        data = getattr(choice, "data", {}) or {}
        class CardView:
            pass
        playing_card = CardView()
        playing_card.rank = data.get("rank") or data.get("value") or ""
        playing_card.enhancement = data.get("enhancement") or data.get("ability_name") or ""
        playing_card.seal = data.get("seal") or ""
    return kind, label, playing_card


def install_bond_prescription_policy() -> None:
    """Install motif prescriptions beneath existing pack/shop safety authorities."""

    if not getattr(BalatroPackPolicy, "_bond_prescription_policy_installed", False):
        original_score_action = BalatroPackPolicy.score_action

        def score_action(self, state, action):
            scored = original_score_action(self, state, action)
            # Negative/zero results include unsupported/deferred/unavailable choices;
            # prescriptions must never make those autonomous-safe.
            if scored.total <= 0.0:
                return scored
            kind, label, playing_card = _pack_choice_semantics(scored.action)
            if not kind:
                return scored
            bonus, notes = prescription_bonus(
                state,
                kind=kind,
                label=label,
                cards=_choice_cards(scored.action),
                playing_card=playing_card,
            )
            if bonus <= 0.0:
                return scored
            return PackActionScore(
                scored.action,
                float(scored.total) + bonus,
                (
                    *scored.notes,
                    f"canonical Bond prescription bonus={bonus:.3f}",
                    *notes,
                    "prescription authority cannot admit unsupported or unsafe pack choices",
                ),
            )

        BalatroPackPolicy.score_action = score_action
        BalatroPackPolicy._bond_prescription_policy_installed = True

    if not getattr(ShopUtilityScale, "_bond_prescription_policy_installed", False):
        original_consumable_gain = ShopUtilityScale.consumable_gain

        def consumable_gain(self, state, executable):
            utility = original_consumable_gain(self, state, executable)
            # D4 admission remains authoritative. Only already-positive admitted
            # utility can receive motif-prescription preference.
            if utility.gain <= 0.0:
                return utility
            candidate = getattr(executable, "candidate", None)
            if candidate is None:
                return utility
            kind = "PLANET" if hasattr(candidate, "hand_type") else (
                "SPECTRAL" if candidate.__class__.__module__.endswith("spectrals") else "TAROT"
            )
            bonus, notes = prescription_bonus(
                state,
                kind=kind,
                label=_name(candidate),
            )
            if bonus <= 0.0:
                return utility
            bounded = min(_MAX_SHOP_BONUS, bonus)
            return replace(
                utility,
                gain=float(utility.gain) + bounded,
                notes=(
                    *utility.notes,
                    f"canonical Bond prescription shop bonus={bounded:.3f}",
                    *notes,
                    "D4 admission and resource guards remain authoritative",
                ),
            )

        ShopUtilityScale.consumable_gain = consumable_gain
        ShopUtilityScale._bond_prescription_policy_installed = True
