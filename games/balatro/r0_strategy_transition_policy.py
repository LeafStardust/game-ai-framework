from __future__ import annotations

"""Give early FORMING/R0 strategy evidence bounded D2 acquisition influence.

The canonical composer can recognize a FORMING StrategyPlan from the first defining
motif core before any relevant Bond reaches R1. Historically D2's transition bonus
only rewarded a newly formed strategy once it was already PINNED, so this legitimate
R0/FORMING evidence could be visible in composition logs while having zero effect on
acquisition.

Add only a completion-proportional tie-breaking contribution, capped below the
existing first-R1 foothold budget and far below PINNED formation. This is structural
recognition, not score: survival, literal Joker value, shop economics, and D14 remain
authoritative.
"""

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.strategy_semantics import StrategyCommitment
from games.balatro import joker_policy as joker_policy_module


MAX_FORMING_R0_BONUS = 0.50
FORMING_COMPLETION_WEIGHT = 0.50


def install_r0_strategy_transition_policy() -> None:
    if getattr(joker_policy_module, "_r0_strategy_transition_installed", False):
        return

    original = joker_policy_module._bond_transition_bonus

    def bond_transition_bonus(state, candidate, *, replace_index=None):
        base_value, base_notes = original(
            state,
            candidate,
            replace_index=replace_index,
        )

        try:
            _, before = evaluate_bond_composition(state)
            projected = state.copy()
            projected.jokers = list(getattr(state, "jokers", ()) or ())
            if replace_index is None:
                projected.jokers.append(candidate)
            else:
                if replace_index < 0 or replace_index >= len(projected.jokers):
                    return base_value, base_notes
                projected.jokers[replace_index] = candidate
            _, after = evaluate_bond_composition(projected)
        except (AttributeError, IndexError, TypeError, ValueError, RuntimeError):
            return base_value, base_notes

        after_plan = getattr(after, "strategy_plan", None)
        if after_plan is None:
            return base_value, base_notes
        if getattr(after_plan, "commitment", None) != StrategyCommitment.FORMING:
            return base_value, base_notes

        after_id = str(getattr(after_plan, "strategy_id", "") or "")
        before_plan = getattr(before, "strategy_plan", None)
        before_id = str(getattr(before_plan, "strategy_id", "") or "") if before_plan is not None else ""
        if not after_id or before_id == after_id:
            return base_value, base_notes

        completion = max(0.0, min(1.0, float(getattr(after_plan, "completion", 0.0) or 0.0)))
        forming_bonus = min(
            MAX_FORMING_R0_BONUS,
            FORMING_COMPLETION_WEIGHT * completion,
        )
        if forming_bonus <= 0.0:
            return base_value, base_notes

        combined = max(-4.0, min(4.0, float(base_value) + forming_bonus))
        return combined, (
            *tuple(base_notes),
            f"FORMING/R0 strategy evidence={after_id} completion={completion:.3f}",
            f"bounded FORMING/R0 acquisition influence=+{forming_bonus:.3f}",
            "FORMING evidence remains subordinate to literal score, survival, economics, and D14",
        )

    joker_policy_module._bond_transition_bonus = bond_transition_bonus
    joker_policy_module._r0_strategy_transition_installed = True
