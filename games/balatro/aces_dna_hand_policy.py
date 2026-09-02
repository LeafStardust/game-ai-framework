from __future__ import annotations

"""DNA/Aces candidate evidence beneath canonical D1 arbitration.

DNA's first-hand single-card copy and Ace development are useful setup evidence,
but they do not own a second PLAY selector. This module exposes the pure strategy-fit
evidence consumed natively by ``StrategyAwareLiveHandActionPolicy``.

Pure legacy selection helpers remain callable for deterministic regression tests,
but are not installed into production arbitration.
"""

from games.balatro.actions import PLAY_CARDS
from games.balatro.build.profile import BalatroBuildProfiler


DNA_LINKED_RANK_FIT = 2.50
DNA_ACE_FIT = 2.00
ACE_DEVELOPMENT_FIT = 1.00
DNA_SAFE_CLEAR_PROBABILITY = 0.90


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _joker_token(joker: object) -> str:
    for value in (
        type(joker).__name__,
        getattr(joker, "name", ""),
        getattr(joker, "label", ""),
        getattr(joker, "ability_name", ""),
    ):
        token = _normalize(value)
        if token and token not in {"simplenamespace", "object"}:
            return token if token.endswith("joker") else token + "joker"
    return ""


def _owns(state, token: str) -> bool:
    return any(_joker_token(joker) == token for joker in getattr(state, "jokers", ()) or ())


def _first_hand(state) -> bool:
    counts = getattr(state, "round_hand_play_counts", None)
    if not isinstance(counts, dict):
        return False
    return not any(int(value or 0) > 0 for value in counts.values())


def _aces_bond_active(policy, state) -> bool:
    intents = policy._hand_bond_intents(state)
    return any(
        str(target).upper() in {"PAIR", "THREE_OF_A_KIND", "FOUR_OF_A_KIND", "FIVE_OF_A_KIND"}
        and "ace" in str(source).lower()
        for target, _weight, source in intents
    )


def _ace_cards(action):
    return tuple(
        card
        for card in getattr(action, "cards", ()) or ()
        if str(getattr(card, "rank", "")).upper() in {"A", "ACE"}
    )


def _card_future_key(card) -> tuple[float, ...]:
    edition = str(getattr(card, "edition", "") or "")
    seal = str(getattr(card, "seal", "") or "")
    enhancement = str(getattr(card, "enhancement", "") or "")
    return (
        1.0 if edition else 0.0,
        1.0 if seal else 0.0,
        1.0 if enhancement else 0.0,
        float(getattr(card, "permanent_bonus", 0) or 0),
    )


def _selected_clear_probability(decision) -> float:
    selected = getattr(decision, "selected_plan", None)
    try:
        return float(getattr(selected.value, "clear_probability", 0.0) or 0.0)
    except (AttributeError, TypeError, ValueError):
        return 0.0


def _clear_probability_tolerance(decision) -> float:
    try:
        return float(
            getattr(
                getattr(decision, "thresholds", None),
                "safe_clear_probability_tolerance",
                0.0,
            )
            or 0.0
        )
    except (TypeError, ValueError):
        return 0.0


def _dna_survival_safe(plan, decision) -> bool:
    probability = float(getattr(plan.value, "clear_probability", 0.0) or 0.0)
    if probability < DNA_SAFE_CLEAR_PROBABILITY:
        return False
    return probability + _clear_probability_tolerance(decision) >= _selected_clear_probability(decision)


def _safe_dna_rank_plan(plans, ranks: tuple[str, ...], decision):
    """Legacy pure selector retained for deterministic compatibility tests."""
    targets = {str(rank).upper() for rank in ranks}
    if not targets:
        return None
    candidates = []
    for plan in plans:
        if plan.action.name != PLAY_CARDS or len(plan.action.cards) != 1:
            continue
        card = plan.action.cards[0]
        rank = str(getattr(card, "rank", "")).upper()
        if rank == "ACE":
            rank = "A"
        if rank not in targets or not _dna_survival_safe(plan, decision):
            continue
        candidates.append(plan)
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda plan: (
            float(plan.value.clear_probability),
            _card_future_key(plan.action.cards[0]),
            float(plan.value.expected_score),
            float(plan.value.expected_hands_remaining),
        ),
    )


def _strategy_dna_rank_targets(state) -> tuple[str, ...]:
    """Return rank requirements mechanically linked to owned Jokers alongside DNA.

    DNA no longer consults retired named-strategy candidates or commitment states.
    The only relevant evidence is public Joker mechanics: if another owned Joker
    explicitly requires, scales with, or amplifies a rank, duplicating that rank is
    useful DNA setup evidence.
    """
    if not _owns(state, "dnajoker"):
        return ()
    try:
        profile = BalatroBuildProfiler().profile(state)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return ()

    ranks: list[str] = []
    for descriptor in profile.descriptors(kind="JOKER"):
        if _normalize(descriptor.source) == "dna":
            continue
        features = set(descriptor.requires) | set(descriptor.scales_with) | set(descriptor.amplifies)
        for feature in features:
            text = str(feature)
            if "rank:" not in text.lower():
                continue
            rank = text.split(":")[-1].strip().upper()
            if rank == "ACE":
                rank = "A"
            if rank:
                ranks.append(rank)
    return tuple(dict.fromkeys(ranks))


def _dna_aces_fit(policy, state, action) -> tuple[float, tuple[str, ...]]:
    if action.name != PLAY_CARDS:
        return 0.0, ()

    cards = tuple(getattr(action, "cards", ()) or ())
    aces = _ace_cards(action)
    value = 0.0
    notes: list[str] = []

    first_hand_dna = _owns(state, "dnajoker") and _first_hand(state)
    if first_hand_dna and len(cards) == 1:
        rank = str(getattr(cards[0], "rank", "") or "").upper()
        if rank == "ACE":
            rank = "A"
        targets = _strategy_dna_rank_targets(state)
        if rank and rank in set(targets):
            value += DNA_LINKED_RANK_FIT
            notes.append(f"DNA first-hand duplication supports linked mechanical rank {rank}")

        if aces and _owns(state, "scholarjoker") and _aces_bond_active(policy, state):
            value += DNA_ACE_FIT
            notes.append("DNA + Scholar first-hand duplication supports developed Aces engine")

    if aces and _aces_bond_active(policy, state):
        value += ACE_DEVELOPMENT_FIT
        notes.append(f"Aces engine prefers Ace-bearing PLAY ({len(aces)} Ace card(s))")

    if value <= 0.0:
        return 0.0, ()
    return value, tuple(notes)
