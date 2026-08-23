from __future__ import annotations

"""Add candidate-strategy formation value to D2's canonical Bond transition bonus.

The original transition projection rewards Bond rank/progress and composition
coherence. Strategy pinning can occur before those ranks move, so this adapter adds
bounded value only when the projected public state forms, strengthens, or advances
a canonical pinned strategy.
"""

import copy

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.strategy_semantics import StrategyCommitment


_MAX_TOTAL_BOND_BONUS = 4.0


def _candidate(composition, strategy_id):
    if not strategy_id:
        return None
    return next(
        (
            candidate
            for candidate in getattr(composition, "strategy_candidates", ()) or ()
            if candidate.strategy_id == strategy_id
        ),
        None,
    )


def _strategy_transition_gain(before, after) -> tuple[float, tuple[str, ...]]:
    before_id = getattr(before, "pinned_strategy_id", None)
    after_id = getattr(after, "pinned_strategy_id", None)
    before_candidate = _candidate(before, before_id)
    after_candidate = _candidate(after, after_id)
    if after_candidate is None or not after_candidate.pinned:
        return 0.0, ()

    gain = 0.0
    notes: list[str] = []
    if before_candidate is None:
        gain += 1.50
        notes.append(
            f"candidate forms pinned strategy {after_candidate.strategy_id} "
            f"({after_candidate.commitment.name}, confidence={after_candidate.confidence:.3f})"
        )
    elif after_candidate.strategy_id == before_candidate.strategy_id:
        commitment_delta = max(
            0,
            int(after_candidate.commitment) - int(before_candidate.commitment),
        )
        if commitment_delta:
            amount = min(1.0, 0.50 * commitment_delta)
            gain += amount
            notes.append(
                f"pinned strategy commitment advances {before_candidate.commitment.name}->{after_candidate.commitment.name}"
            )
        strength_delta = max(0.0, float(after_candidate.strength) - float(before_candidate.strength))
        if strength_delta > 0.0:
            amount = min(0.75, strength_delta / 10.0)
            gain += amount
            notes.append(
                f"pinned strategy strength improves by {strength_delta:.3f} (+{amount:.3f})"
            )
    elif float(after_candidate.strength) > float(before_candidate.strength):
        amount = min(1.25, (float(after_candidate.strength) - float(before_candidate.strength)) / 8.0)
        if amount > 0.0:
            gain += amount
            notes.append(
                f"candidate pivots to stronger pinned strategy {before_candidate.strategy_id}->{after_candidate.strategy_id} (+{amount:.3f})"
            )

    return min(1.75, gain), tuple(notes)


def install_pinned_strategy_transition_policy() -> None:
    import games.balatro.joker_policy as joker_policy

    if getattr(joker_policy, "_pinned_strategy_transition_installed", False):
        return
    original = joker_policy._bond_transition_bonus

    def transition_bonus(state, candidate, *, replace_index=None):
        base, notes = original(state, candidate, replace_index=replace_index)
        if base >= _MAX_TOTAL_BOND_BONUS:
            return base, notes
        try:
            _, before = evaluate_bond_composition(state)
            projected = copy.copy(state)
            projected.jokers = list(getattr(state, "jokers", ()) or ())
            if replace_index is None:
                projected.jokers.append(candidate)
            else:
                index = int(replace_index)
                if index < 0 or index >= len(projected.jokers):
                    return base, notes
                projected.jokers[index] = candidate
            _, after = evaluate_bond_composition(projected)
        except (AttributeError, TypeError, ValueError, RuntimeError):
            return base, notes

        strategy_gain, strategy_notes = _strategy_transition_gain(before, after)
        if strategy_gain <= 0.0:
            return base, notes
        total = min(_MAX_TOTAL_BOND_BONUS, float(base) + strategy_gain)
        return total, (
            *notes,
            f"canonical pinned-strategy transition value={strategy_gain:.3f}",
            *strategy_notes,
        )

    joker_policy._bond_transition_bonus = transition_bonus
    joker_policy._pinned_strategy_transition_installed = True
