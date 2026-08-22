from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Iterable

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization


class MotifState(IntEnum):
    ABSENT = 0
    POTENTIAL = 1
    ACTIVE = 2
    MATURE = 3


@dataclass(frozen=True)
class MotifEvaluation:
    motif_id: str
    state: MotifState
    relevant_bonds: tuple[str, ...]
    present_components: tuple[str, ...]
    missing_components: tuple[str, ...]
    prescriptions: tuple[str, ...]


def _name(value: Any) -> str:
    raw = value if isinstance(value, str) else getattr(value, "name", None) or value.__class__.__name__
    return "".join(ch for ch in str(raw).lower() if ch.isalnum())


def _has(values: Iterable[Any], *tokens: str) -> bool:
    names = {_name(v) for v in values}
    return any(any(token in name for name in names) for token in tokens)


def _deck(state: Any) -> list[Any]:
    owned = getattr(state, "owned_deck", None)
    if owned is not None:
        return list(owned)
    return list(getattr(state, "deck", ()) or ())


def _dev_map(developments: Iterable[BondDevelopment]) -> dict[str, BondDevelopment]:
    return {dev.bond_id: dev for dev in developments}


def evaluate_baron_mime_steel(state: Any, developments: Iterable[BondDevelopment]) -> MotifEvaluation:
    """Recognize the canonical Baron-Mime-Steel held-card composition.

    The motif is intentionally role/package-specific. Blackboard can develop Held
    Cards but cannot substitute for Baron's King payoff; generic held-card rank
    therefore does not activate this motif by itself.
    """
    devs = _dev_map(developments)
    jokers = list(getattr(state, "jokers", ()) or ())
    deck = _deck(state)

    has_baron = _has(jokers, "baron")
    has_mime = _has(jokers, "mime")
    kings = sum(1 for c in deck if str(getattr(c, "rank", "") or "").upper() == "K")
    steel = sum(1 for c in deck if str(getattr(c, "enhancement", "") or "").lower() == "steel")

    present: list[str] = []
    missing: list[str] = []
    for ok, label in ((has_baron, "BARON"), (has_mime, "MIME"), (kings >= 4, "KING_INFRASTRUCTURE"), (steel >= 2, "STEEL_INFRASTRUCTURE")):
        (present if ok else missing).append(label)

    held = devs.get("held_cards")
    retrigger = devs.get("held_retrigger")
    steel_dev = devs.get("steel")
    kings_dev = devs.get("kings")

    if len(present) < 2:
        state_value = MotifState.ABSENT
    elif missing:
        state_value = MotifState.POTENTIAL
    else:
        active = all(
            dev is not None and dev.realization >= BondRealization.ACTIVE
            for dev in (held, retrigger, steel_dev, kings_dev)
        )
        if active and all(dev is not None and dev.rank >= BondRank.R4 for dev in (held, retrigger, steel_dev, kings_dev)):
            state_value = MotifState.MATURE
        elif active:
            state_value = MotifState.ACTIVE
        else:
            state_value = MotifState.POTENTIAL

    return MotifEvaluation(
        motif_id="baron_mime_steel",
        state=state_value,
        relevant_bonds=("held_cards", "held_retrigger", "steel", "kings"),
        present_components=tuple(present),
        missing_components=tuple(missing),
        prescriptions=(
            "prefer_kings_and_steel_creation",
            "preserve_held_kings_and_steel",
            "prefer_hand_size_when_survival_allows",
            "avoid_playing_engine_cards_without_clear_need",
            "value_red_seal_steel_and_copy_effects_highly",
        ),
    )


MOTIF_EVALUATORS = {
    "baron_mime_steel": evaluate_baron_mime_steel,
}


def evaluate_motifs(state: Any, developments: Iterable[BondDevelopment]) -> tuple[MotifEvaluation, ...]:
    return tuple(fn(state, developments) for fn in MOTIF_EVALUATORS.values())
