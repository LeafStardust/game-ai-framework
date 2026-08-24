from __future__ import annotations

"""D1 execution guards for realized no-discard and hand-repetition engines.

These are strategy-execution constraints beneath survival authority.  A realized
engine must influence actual hand choice; it is not sufficient for Bonds/diagnostics
to recognize the engine while D1 repeatedly destroys or ignores it.
"""

from dataclasses import replace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.bonds.diagnostics import bond_strategy_diagnostics
from games.balatro.live.hand_action_policy import PACE_PLAY
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _joker_token(joker: object) -> str:
    value = (
        getattr(joker, "label", None)
        or getattr(joker, "name", None)
        or getattr(joker, "ability_name", None)
        or type(joker).__name__
    )
    token = _normalize(value)
    return token if token.endswith("joker") else token + "joker"


def _realized_bond(state, bond_id: str) -> bool:
    try:
        diagnostics = bond_strategy_diagnostics(state)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return False
    for payload in diagnostics.get("relevant_bonds", ()) or ():
        if str(payload.get("bond_id")) != bond_id:
            continue
        return str(payload.get("realization", "")).upper() in {"ACTIVE", "MATURE"}
    return False


def realized_banner_delayed_no_discard(state) -> bool:
    """Compatibility helper retained for existing tests/callers."""
    owned = {_joker_token(joker) for joker in getattr(state, "jokers", ()) or ()}
    return {"bannerjoker", "delayedgratificationjoker"}.issubset(owned)


def _realized_no_discard_engine(state) -> bool:
    if not _realized_bond(state, "no_discard"):
        return False
    owned = {_joker_token(joker) for joker in getattr(state, "jokers", ()) or ()}
    # These Jokers directly lose value when D1 discards. Banner is intentionally
    # included only when the canonical no_discard Bond is realized; ownership alone
    # does not ban survival-driven discards.
    return bool(
        owned
        & {
            "greenjoker",
            "delayedgratificationjoker",
            "bannerjoker",
        }
    )


def _safe_pace_play(policy, state, plans, decision):
    """Return the best play already meeting D1's own pace target, if one exists."""
    pace_target = float(getattr(decision, "pace_target", 0.0) or 0.0)
    if pace_target <= 0.0:
        return None

    candidates = []
    for plan in plans:
        if plan.action.name != PLAY_CARDS:
            continue
        score = float(policy.evaluator.project_play(state, plan.action).expected_hand_score)
        if score + policy.EPSILON >= pace_target:
            candidates.append((score, plan))
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            policy._strategy_fit(state, item[1].action)[0],
            item[0],
            policy._within_type_key(item[1]),
        ),
    )


def _hand_key(policy, plan) -> str:
    return _normalize(policy._hand_evaluator.evaluate(list(plan.action.cards)).value)


def _played_this_round(state) -> set[str]:
    counts = getattr(state, "round_hand_play_counts", None)
    if not isinstance(counts, dict):
        counts = getattr(state, "hand_play_counts_this_round", None)
    if not isinstance(counts, dict):
        return set()
    return {_normalize(name) for name, count in counts.items() if int(count or 0) > 0}


def _safe_repeat_play(policy, state, plans, decision):
    """Return a safe pace-qualified repeat even when baseline D1 chose DISCARD.

    Repetition engines such as Card Sharp are execution contracts, not merely
    scoring labels. If a previously played hand is already available on a line that
    is within D1's clear-probability tolerance and meets the current pace target,
    discarding instead would unnecessarily abandon realized engine value.
    """
    if not _realized_bond(state, "hand_repetition"):
        return None
    repeated = _played_this_round(state)
    if not repeated:
        return None

    selected = getattr(decision, "selected_plan", None)
    selected_probability = float(
        getattr(getattr(selected, "value", None), "clear_probability", 0.0) or 0.0
    )
    tolerance = float(
        getattr(getattr(decision, "thresholds", None), "safe_clear_probability_tolerance", 0.0)
        or 0.0
    )
    pace_target = float(getattr(decision, "pace_target", 0.0) or 0.0)
    candidates = []
    for plan in plans:
        if plan.action.name != PLAY_CARDS or _hand_key(policy, plan) not in repeated:
            continue
        probability = float(getattr(plan.value, "clear_probability", 0.0) or 0.0)
        if probability + tolerance + policy.EPSILON < selected_probability:
            continue
        score = float(policy.evaluator.project_play(state, plan.action).expected_hand_score)
        if pace_target > 0.0 and score + policy.EPSILON < pace_target:
            continue
        candidates.append((probability, score, plan))
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            item[0],
            policy._strategy_fit(state, item[2].action)[0],
            item[1],
            policy._within_type_key(item[2]),
        ),
    )


def install_latest_batch_no_discard_policy() -> None:
    if getattr(
        StrategyAwareLiveHandActionPolicy,
        "_latest_batch_no_discard_policy_installed",
        False,
    ):
        return

    original_decide = StrategyAwareLiveHandActionPolicy.decide

    def decide(self, state, plans, **kwargs):
        plans = tuple(plans)
        decision = original_decide(self, state, plans, **kwargs)

        # Realized no-discard engines should not be destroyed for convenience.  A
        # discard remains legal when no currently playable hand satisfies D1 pace.
        if decision.action.name == DISCARD_CARDS and _realized_no_discard_engine(state):
            safe = _safe_pace_play(self, state, plans, decision)
            if safe is not None:
                score, plan = safe
                pace_target = float(getattr(decision, "pace_target", 0.0) or 0.0)
                pace_ratio = score / pace_target if pace_target > 0.0 else float("inf")
                decision = replace(
                    decision,
                    mode=PACE_PLAY,
                    action=plan.action,
                    selected_plan=plan,
                    selected_immediate_score=score,
                    selected_pace_ratio=pace_ratio,
                    selected_fallback_value=None,
                    confidence=max(float(getattr(decision, "confidence", 0.0) or 0.0), 0.90),
                    rationale=(
                        "realized no_discard engine: preserve discard-sensitive value when a play already meets D1 pace",
                        f"selected play projects {score:.3f} against pace target {pace_target:.3f}",
                        "survival remains authoritative when no current play meets pace",
                        *decision.rationale,
                    ),
                )

        # Card Sharp / generic repetition strategies need actual repeated hands, not
        # merely a diagnostic hand_repetition label.  A safe repeated play may
        # replace either a different play or an unnecessary discard.
        repeat = _safe_repeat_play(self, state, plans, decision)
        if repeat is not None:
            probability, score, plan = repeat
            if getattr(decision.action, "cards", None) != getattr(plan.action, "cards", None):
                pace_target = float(getattr(decision, "pace_target", 0.0) or 0.0)
                pace_ratio = score / pace_target if pace_target > 0.0 else float("inf")
                decision = replace(
                    decision,
                    mode=PACE_PLAY,
                    action=plan.action,
                    selected_plan=plan,
                    selected_immediate_score=score,
                    selected_pace_ratio=pace_ratio,
                    selected_fallback_value=None,
                    confidence=max(float(getattr(decision, "confidence", 0.0) or 0.0), probability),
                    rationale=(
                        "realized hand_repetition engine: prefer a previously played hand on a survival-equivalent pace-qualified line",
                        f"repeat-line clear probability={probability:.3f}",
                        *decision.rationale,
                    ),
                )
        return decision

    StrategyAwareLiveHandActionPolicy.decide = decide
    StrategyAwareLiveHandActionPolicy._latest_batch_no_discard_policy_installed = True
