from __future__ import annotations

"""Let pinned candidate engines steer already-safe acquisition choices.

Pinned strategy authority is deliberately bounded beneath pack/shop legality. Known
motif prescriptions and generic unmet behavior features may guide an already-valid
choice before the engine is fully realized, but they cannot admit an unsupported or
unsafe action.
"""

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.build.joker_scenarios import ScenarioJokerBehaviorAnalyzer
from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore


_MAX_GENERIC_PACK_GOAL_BONUS = 1.25
_PER_GENERIC_PACK_GOAL = 0.45


def _pinned_candidate(state):
    try:
        _, composition = evaluate_bond_composition(state)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return None
    pinned_id = getattr(composition, "pinned_strategy_id", None)
    if not pinned_id:
        return None
    return next(
        (
            candidate
            for candidate in getattr(composition, "strategy_candidates", ()) or ()
            if candidate.strategy_id == pinned_id and candidate.pinned
        ),
        None,
    )


def _pinned_goals(state) -> tuple[str, ...]:
    candidate = _pinned_candidate(state)
    if candidate is None:
        return ()
    return tuple(
        str(prescription).split(":", 1)[1]
        for prescription in candidate.prescriptions
        if str(prescription).startswith("seek_feature:")
    )


def _card_features(data: dict) -> frozenset[str]:
    value = data.get("value") if isinstance(data.get("value"), dict) else data
    rank = value.get("rank") if isinstance(value, dict) else None
    suit = value.get("suit") if isinstance(value, dict) else None
    enhancement = data.get("enhancement") or data.get("ability_name")
    seal = data.get("seal")
    features: set[str] = set()
    if rank:
        rank = str(rank)
        aliases = {"King": "K", "Queen": "Q", "Jack": "J", "Ace": "A", "T": "10"}
        rank = aliases.get(rank, rank)
        features.update((f"rank:{rank}", f"held:rank:{rank}"))
    if suit:
        features.update((f"suit:{suit}", f"held:suit:{suit}"))
    if enhancement:
        token = str(enhancement).replace(" Card", "")
        features.update((f"enhancement:{token}", f"held:enhancement:{token}"))
        if token in {"Steel", "Gold"}:
            features.add("held:effect")
    if seal:
        features.update((f"seal:{seal}", f"held:seal:{seal}"))
    return frozenset(features)


def _choice_features(action) -> frozenset[str]:
    choice = getattr(action, "target", None)
    if choice is None:
        return frozenset()
    kind = str(getattr(choice, "kind", "") or "").upper()
    data = getattr(choice, "data", None)
    if not isinstance(data, dict):
        return frozenset()
    if kind == "PLAYING_CARD":
        return _card_features(data)
    if kind == "JOKER":
        joker = LiveJokerFactory().create(data)
        if joker is None:
            return frozenset()
        try:
            descriptor = ScenarioJokerBehaviorAnalyzer().describe(joker)
        except (AttributeError, TypeError, ValueError):
            return frozenset()
        return frozenset(set(descriptor.produces) | set(descriptor.transforms))
    return frozenset()


def _generic_pack_goal_bonus(state, action) -> tuple[float, tuple[str, ...]]:
    goals = set(_pinned_goals(state))
    if not goals:
        return 0.0, ()
    matched = sorted(goals.intersection(_choice_features(action)))
    if not matched:
        return 0.0, ()
    bonus = min(
        _MAX_GENERIC_PACK_GOAL_BONUS,
        _PER_GENERIC_PACK_GOAL * len(matched),
    )
    return bonus, (
        f"pinned strategy pack-goal bonus={bonus:.3f}",
        "matched unmet features=" + ", ".join(matched),
    )


def install_pinned_strategy_execution_policy() -> None:
    import games.balatro.bond_prescription_policy as prescriptions

    if getattr(prescriptions, "_pinned_strategy_execution_installed", False):
        return

    original_motif_ids = prescriptions._active_motif_ids

    def strategy_motif_ids(state):
        result = set(original_motif_ids(state))
        candidate = _pinned_candidate(state)
        if candidate is not None:
            result.update(candidate.motif_ids)
        return frozenset(result)

    prescriptions._active_motif_ids = strategy_motif_ids

    # This wraps the already-installed canonical motif prescription scorer. It only
    # augments choices whose lower-level pack scorer returned positive value.
    original_score_action = BalatroPackPolicy.score_action

    def score_action(self, state, action):
        scored = original_score_action(self, state, action)
        if float(scored.total) <= 0.0:
            return scored
        bonus, notes = _generic_pack_goal_bonus(state, scored.action)
        if bonus <= 0.0:
            return scored
        return PackActionScore(
            scored.action,
            float(scored.total) + bonus,
            (
                *scored.notes,
                *notes,
                "generic pinned strategy goals cannot override pack legality/safety",
            ),
        )

    BalatroPackPolicy.score_action = score_action
    prescriptions._pinned_strategy_execution_installed = True
