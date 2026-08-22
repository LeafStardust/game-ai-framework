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


REALIZATION_STRENGTH = {
    BondRealization.DORMANT: 0,
    BondRealization.PARTIAL: 1,
    BondRealization.ACTIVE: 2,
    BondRealization.MATURE: 3,
}


@dataclass(frozen=True)
class MotifEvaluation:
    motif_id: str
    state: MotifState
    relevant_bonds: tuple[str, ...]
    present_components: tuple[str, ...]
    missing_components: tuple[str, ...]
    prescriptions: tuple[str, ...]

    @property
    def missing_count(self) -> int:
        return len(self.missing_components)


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


def _active(dev: BondDevelopment | None) -> bool:
    return dev is not None and REALIZATION_STRENGTH[dev.realization] >= REALIZATION_STRENGTH[BondRealization.ACTIVE]


def _mature(dev: BondDevelopment | None) -> bool:
    return dev is not None and dev.rank >= BondRank.R4 and _active(dev)


def _package_state(present_count: int, missing: list[str], related: Iterable[BondDevelopment | None]) -> MotifState:
    related = tuple(related)
    if present_count < 2:
        return MotifState.ABSENT
    if missing:
        return MotifState.POTENTIAL
    if all(_mature(dev) for dev in related):
        return MotifState.MATURE
    if all(_active(dev) for dev in related):
        return MotifState.ACTIVE
    return MotifState.POTENTIAL


def _baron_mime_steel_state(
    present_count: int,
    missing: list[str],
    devs: dict[str, BondDevelopment],
) -> MotifState:
    """Resolve Baron/Mime/Steel without contradicting its own component contract.

    Two Steel cards are intentionally enough to complete this super-additive motif,
    even though the standalone Steel Bond does not itself reach R1 at two cards.
    ACTIVE therefore requires the core functional Bonds (held cards, held retrigger,
    Kings) to be active plus the explicit Steel-infrastructure component. MATURE is
    stricter and requires the standalone Steel Bond to mature as well.
    """
    if present_count < 2:
        return MotifState.ABSENT
    if missing:
        return MotifState.POTENTIAL

    core = tuple(devs.get(b) for b in ("held_cards", "held_retrigger", "kings"))
    steel = devs.get("steel")
    if all(_mature(dev) for dev in core) and _mature(steel):
        return MotifState.MATURE
    if all(_active(dev) for dev in core):
        return MotifState.ACTIVE
    return MotifState.POTENTIAL


def evaluate_baron_mime_steel(state: Any, developments: Iterable[BondDevelopment]) -> MotifEvaluation:
    devs = _dev_map(developments)
    jokers = list(getattr(state, "jokers", ()) or ())
    deck = _deck(state)
    checks = (
        (_has(jokers, "baron"), "BARON"),
        (_has(jokers, "mime"), "MIME"),
        (sum(1 for c in deck if str(getattr(c, "rank", "") or "").upper() == "K") >= 4, "KING_INFRASTRUCTURE"),
        (sum(1 for c in deck if str(getattr(c, "enhancement", "") or "").lower() == "steel") >= 2, "STEEL_INFRASTRUCTURE"),
    )
    present = [label for ok, label in checks if ok]
    missing = [label for ok, label in checks if not ok]
    state_value = _baron_mime_steel_state(len(present), missing, devs)
    return MotifEvaluation(
        "baron_mime_steel",
        state_value,
        ("held_cards", "held_retrigger", "steel", "kings"),
        tuple(present),
        tuple(missing),
        (
            "prefer_kings_and_steel_creation",
            "preserve_held_kings_and_steel",
            "prefer_hand_size_when_survival_allows",
            "avoid_playing_engine_cards_without_clear_need",
            "value_red_seal_steel_and_copy_effects_highly",
        ),
    )


def evaluate_photo_chad(state: Any, developments: Iterable[BondDevelopment]) -> MotifEvaluation:
    devs = _dev_map(developments)
    jokers = list(getattr(state, "jokers", ()) or ())
    deck = _deck(state)
    face = sum(1 for c in deck if str(getattr(c, "rank", "") or "").upper() in {"J", "Q", "K"})
    checks = (
        (_has(jokers, "photograph"), "PHOTOGRAPH"),
        (_has(jokers, "hangingchad"), "HANGING_CHAD"),
        (face >= 8, "FACE_CARD_INFRASTRUCTURE"),
    )
    present = [l for ok, l in checks if ok]
    missing = [l for ok, l in checks if not ok]
    related = tuple(devs.get(b) for b in ("face_cards", "played_retrigger"))
    return MotifEvaluation(
        "photograph_hanging_chad",
        _package_state(len(present), missing, related),
        ("face_cards", "played_retrigger"),
        tuple(present),
        tuple(missing),
        (
            "lead_with_strong_face_scoring_card",
            "preserve_face_card_density",
            "value_red_seal_face_cards_and_copy_effects",
            "avoid_wasting_first_scoring_card_slot",
        ),
    )


def evaluate_vampire_midas(state: Any, developments: Iterable[BondDevelopment]) -> MotifEvaluation:
    devs = _dev_map(developments)
    jokers = list(getattr(state, "jokers", ()) or ())
    deck = _deck(state)
    enhanced = sum(1 for c in deck if str(getattr(c, "enhancement", "") or "").strip())
    checks = (
        (_has(jokers, "vampire"), "VAMPIRE"),
        (_has(jokers, "midasmask"), "MIDAS_MASK"),
        (enhanced >= 3, "ENHANCEMENT_FEEDSTOCK"),
    )
    present = [l for ok, l in checks if ok]
    missing = [l for ok, l in checks if not ok]
    related = (devs.get("vampire"),)
    return MotifEvaluation(
        "vampire_midas",
        _package_state(len(present), missing, related),
        ("vampire",),
        tuple(present),
        tuple(missing),
        (
            "prefer_face_cards_as_renewable_vampire_feed",
            "cycle_midas_created_gold_into_vampire",
            "avoid_preserving_enhancements_needed_only_as_feed",
            "protect_vampire_scaler",
        ),
    )


def evaluate_burnt_target_level(state: Any, developments: Iterable[BondDevelopment]) -> MotifEvaluation:
    devs = _dev_map(developments)
    jokers = list(getattr(state, "jokers", ()) or ())
    burnt = devs.get("burnt")
    target = (burnt.target if burnt is not None else None) or "HIGH_CARD"
    levels = getattr(state, "hand_levels", {}) or {}
    level = int(levels.get(target, 1) or 1)
    support = _has(jokers, "spacejoker", "blueprint", "brainstorm") or _has(
        list(getattr(state, "vouchers", ()) or ()), "telescope"
    )
    checks = (
        (_has(jokers, "burntjoker"), "BURNT_JOKER"),
        (level >= 4, "TARGET_HAND_LEVEL"),
        (support, "LEVELING_SUPPORT"),
    )
    present = [l for ok, l in checks if ok]
    missing = [l for ok, l in checks if not ok]
    state_value = _package_state(len(present), missing, (burnt,))
    return MotifEvaluation(
        "burnt_target_level",
        state_value,
        tuple(b for b in ("burnt", str(target).lower()) if b in devs),
        tuple(present),
        tuple(missing),
        (
            "use_first_discard_to_level_target_hand",
            "prefer_target_hand_planets_and_blue_seals",
            "preserve_discard_access",
            "play_target_hand_as_primary_scoring_shape",
        ),
    )


def evaluate_low_rank_hack_retrigger(state: Any, developments: Iterable[BondDevelopment]) -> MotifEvaluation:
    devs = _dev_map(developments)
    jokers = list(getattr(state, "jokers", ()) or ())
    deck = _deck(state)
    low = sum(1 for c in deck if str(getattr(c, "rank", "") or "") in {"2", "3", "4", "5"})
    checks = (
        (_has(jokers, "hack"), "HACK"),
        (low >= 12, "LOW_RANK_INFRASTRUCTURE"),
    )
    present = [l for ok, l in checks if ok]
    missing = [l for ok, l in checks if not ok]
    related = tuple(devs.get(b) for b in ("low_ranks", "played_retrigger"))
    return MotifEvaluation(
        "low_rank_hack_retrigger",
        _package_state(len(present), missing, related),
        ("low_ranks", "played_retrigger"),
        tuple(present),
        tuple(missing),
        (
            "prefer_scoring_2_to_5_cards",
            "value_red_seal_low_cards_highly",
            "preserve_low_rank_density",
            "combine_with_on_score_enhancements_when_safe",
        ),
    )


MOTIF_EVALUATORS = {
    "baron_mime_steel": evaluate_baron_mime_steel,
    "photograph_hanging_chad": evaluate_photo_chad,
    "vampire_midas": evaluate_vampire_midas,
    "burnt_target_level": evaluate_burnt_target_level,
    "low_rank_hack_retrigger": evaluate_low_rank_hack_retrigger,
}


def evaluate_motifs(state: Any, developments: Iterable[BondDevelopment]) -> tuple[MotifEvaluation, ...]:
    devs = tuple(developments)
    return tuple(fn(state, devs) for fn in MOTIF_EVALUATORS.values())
