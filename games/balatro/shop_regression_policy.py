from __future__ import annotations

"""Targeted D2 safeguards for shop regressions observed in live Red/White runs."""

from dataclasses import replace

from games.balatro.joker_policy import (
    BUY,
    HOLD,
    JokerAcquisitionDecision,
    JokerAcquisitionPolicy,
)


BASEBALL_MIN_UNCOMMON_SUPPORT = 2
BURNT_ENGINE_BASE_BONUS = 6.0


def baseball_uncommon_support(state) -> int:
    """Count owned Uncommon Jokers that Baseball Card can actually amplify."""
    return sum(
        1
        for joker in tuple(getattr(state, "jokers", ()) or ())
        if str(getattr(joker, "rarity", "") or "").upper() == "UNCOMMON"
    )


def burnt_engine_bonus(state) -> float:
    """Persistent value for Burnt Joker's guaranteed first-discard hand level.

    The generic deterministic scoring probe cannot observe future round-level
    progression, so D2 otherwise compares Baseball's immediate XMult against
    effectively none of Burnt Joker's engine value. Keep the bonus bounded and
    decrease it as fewer antes remain.
    """
    ante = max(1, int(getattr(state, "ante", 1) or 1))
    return max(2.5, BURNT_ENGINE_BASE_BONUS - 0.5 * max(0, ante - 1))


def _hold_decision(policy, candidate, rationale: tuple[str, ...]):
    return JokerAcquisitionDecision(
        action=HOLD,
        candidate=type(candidate).__name__,
        selected=None,
        options=(),
        thresholds=policy.thresholds,
        rationale=rationale,
    )


def install_shop_regression_policy() -> None:
    if getattr(JokerAcquisitionPolicy, "_shop_regression_policy_installed", False):
        return

    original_decide = JokerAcquisitionPolicy.decide

    def decide(self, state, candidate):
        candidate_name = type(candidate).__name__

        # Baseball Card is a payoff Joker, not a speculative engine starter. One
        # Uncommon produces only a single 1.5x trigger and was enough for the generic
        # score probe to dwarf persistent engines such as Burnt Joker. Require an
        # established Uncommon core before spending money/slot equity on Baseball.
        if candidate_name == "BaseballCardJoker":
            support = baseball_uncommon_support(state)
            if support < BASEBALL_MIN_UNCOMMON_SUPPORT:
                return _hold_decision(
                    self,
                    candidate,
                    (
                        f"Baseball Card support={support} Uncommon Joker(s); require at least {BASEBALL_MIN_UNCOMMON_SUPPORT}",
                        "do not treat Baseball Card as an engine starter; preserve cash/slot for stronger active scaling",
                    ),
                )

        decision = original_decide(self, state, candidate)

        # Burnt Joker's first-discard hand level compounds for every remaining
        # round, but the ordinary score probe only measures immediate scored hands.
        # Add the missing persistent engine term to D2 rather than pretending the
        # card has zero build value at purchase time.
        if candidate_name == "BurntJoker" and decision.action == HOLD and decision.options:
            option = decision.options[0]
            bonus = burnt_engine_bonus(state)
            upgraded = replace(
                option,
                build_gain=float(option.build_gain) + bonus,
                total_advantage=float(option.total_advantage) + bonus,
                eligible=bool(option.economics.money_after >= 0),
                rationale=(
                    *option.rationale,
                    f"Burnt Joker persistent first-discard hand-level engine bonus={bonus:.3f}",
                ),
            )
            if (
                upgraded.eligible
                and upgraded.total_advantage > self.thresholds.minimum_purchase_advantage
            ):
                return JokerAcquisitionDecision(
                    action=BUY,
                    candidate=decision.candidate,
                    selected=upgraded,
                    options=(upgraded, *decision.options[1:]),
                    thresholds=decision.thresholds,
                    rationale=(
                        f"Burnt Joker engine-adjusted buy advantage={upgraded.total_advantage:.3f} exceeds threshold={self.thresholds.minimum_purchase_advantage:.3f}",
                        *decision.rationale,
                    ),
                )

        # Negative Jokers remain buyable at a full ordinary roster. Their edition
        # is slot-neutral; bridge capacity validation owns the matching execution
        # rule and must not be approximated here by converting a valid BUY to HOLD.
        return decision

    JokerAcquisitionPolicy.decide = decide
    JokerAcquisitionPolicy._shop_regression_policy_installed = True
