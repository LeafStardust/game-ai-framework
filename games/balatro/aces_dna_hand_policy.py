from __future__ import annotations

"""DNA/Aces candidate evidence beneath canonical D1 arbitration.

DNA's first-hand single-card copy and Ace development are useful setup evidence,
but they do not own a second PLAY selector. This installer augments only the
strategy-fit evidence consumed by ``StrategyAwareLiveHandActionPolicy``. Canonical
clear probability, exactness, pace, round resources, and score-equivalence remain
above this signal.
"""

from games.balatro.actions import PLAY_CARDS
from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.build.profile import BalatroBuildProfiler
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


DNA_LINKED_RANK_FIT = 2.50
DNA_ACE_FIT = 2.00
ACE_DEVELOPMENT_FIT = 1.00


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


def _candidate_priority(candidate) -> tuple[int, float, float]:
    commitment = getattr(candidate, "commitment", 0)
    try:
        commitment_value = int(commitment)
    except (TypeError, ValueError):
        commitment_value = 0
    return (
        commitment_value,
        float(getattr(candidate, "confidence", 0.0) or 0.0),
        float(getattr(candidate, "strength", 0.0) or 0.0),
    )


def _strategy_dna_rank_targets(state) -> tuple[str, ...]:
    """Return concrete rank requirements from the strongest strategy containing DNA."""
    if not _owns(state, "dnajoker"):
        return ()
    try:
        _developments, composition = evaluate_bond_composition(state)
        linked = tuple(
            item
            for item in tuple(getattr(composition, "strategy_candidates", ()) or ())
            if any(_normalize(source) == "dna" for source in getattr(item, "sources", ()) or ())
        )
        if not linked:
            return ()
        candidate = max(linked, key=_candidate_priority)
        strategy_sources = {
            _normalize(source)
            for source in getattr(candidate, "sources", ()) or ()
            if _normalize(source) != "dna"
        }
        profile = BalatroBuildProfiler().profile(state)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return ()

    ranks: list[str] = []
    for descriptor in profile.descriptors(kind="JOKER"):
        if _normalize(descriptor.source) not in strategy_sources:
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
            notes.append(
                f"DNA first-hand duplication supports linked strategy rank {rank}"
            )

        if (
            aces
            and _owns(state, "scholarjoker")
            and _aces_bond_active(policy, state)
        ):
            value += DNA_ACE_FIT
            notes.append("DNA + Scholar first-hand duplication supports developed Aces engine")

    if aces and _aces_bond_active(policy, state):
        value += ACE_DEVELOPMENT_FIT
        notes.append(f"Aces engine prefers Ace-bearing PLAY ({len(aces)} Ace card(s))")

    if value <= 0.0:
        return 0.0, ()
    return value, tuple(notes)


def install_aces_dna_hand_policy() -> None:
    if getattr(
        StrategyAwareLiveHandActionPolicy,
        "_aces_dna_hand_policy_installed",
        False,
    ):
        return

    original_strategy_fit = StrategyAwareLiveHandActionPolicy._strategy_fit

    def strategy_fit(self, state, action):
        base, rationale = original_strategy_fit(self, state, action)
        dna_value, dna_notes = _dna_aces_fit(self, state, action)
        if dna_value <= 0.0:
            return base, rationale
        return (
            base + dna_value,
            (
                *rationale,
                *dna_notes,
                f"DNA/Aces candidate evidence={dna_value:+.3f}; canonical D1 survival ordering remains authoritative",
            ),
        )

    StrategyAwareLiveHandActionPolicy._strategy_fit = strategy_fit
    StrategyAwareLiveHandActionPolicy._aces_dna_hand_policy_installed = True
