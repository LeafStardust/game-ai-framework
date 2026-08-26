from __future__ import annotations

"""Make D2's mechanical build term use the cash state that exists after purchase.

The transition planner evaluates Joker marginals before D2 knows purchase price/sell
credit. For cash-sensitive builds this can be materially wrong: Bull, Bootstraps,
and candidates that amplify them were probed using money that will be spent before
the acquired Joker ever scores.

D2 already owns transaction economics. Once ``money_after`` is known, recompute the
candidate marginal on that resulting cash state. Replacement keeps the incumbent's
marginal on the actual pre-transaction baseline while the candidate is measured on
the post-sale/buy baseline. Resource/interest/reserve/slot costs remain separate and
are not converted into chips or Mult here.
"""

import copy

from games.balatro import joker_policy as joker_policy_module
from games.balatro.joker import Joker
from games.balatro.joker_edition import joker_edition_universal_value
from games.balatro.joker_policy import (
    BUY,
    REPLACE,
    JokerAcquisitionOption,
    JokerAcquisitionPolicy,
)


def _candidate_value_after_money(policy, state, candidate, money_after: int) -> float:
    projected = copy.deepcopy(state)
    projected.money = int(money_after)
    return float(policy.transition_planner.evaluator.evaluate(projected, candidate).total_gain)


def install_post_transaction_joker_value_policy() -> None:
    if getattr(JokerAcquisitionPolicy, "_post_transaction_joker_value_installed", False):
        return

    original_add = JokerAcquisitionPolicy._score_add
    original_replacement = JokerAcquisitionPolicy._score_replacement

    def score_add(self, state, candidate, build_gain, *, strategic_conflict=False):
        if not isinstance(candidate, Joker):
            return original_add(
                self,
                state,
                candidate,
                build_gain,
                strategic_conflict=strategic_conflict,
            )

        economics = self._economics(state, candidate, incumbent=None, replacement=False)
        if economics.money_after < 0:
            return original_add(
                self,
                state,
                candidate,
                build_gain,
                strategic_conflict=strategic_conflict,
            )

        raw_post_transaction_gain = _candidate_value_after_money(
            self,
            state,
            candidate,
            economics.money_after,
        )
        bond_bonus, bond_notes = joker_policy_module._bond_transition_bonus(
            state,
            candidate,
        )
        resulting_build_gain = raw_post_transaction_gain + bond_bonus
        eligible = (
            not strategic_conflict
            and (
                resulting_build_gain > self.thresholds.minimum_purchase_build_gain
                or joker_edition_universal_value(candidate) > 0.0
            )
        )
        total = resulting_build_gain + economics.total_adjustment
        return JokerAcquisitionOption(
            BUY,
            resulting_build_gain,
            total,
            economics,
            eligible,
            rationale=(
                f"post-transaction whole-build candidate gain={raw_post_transaction_gain:.3f}",
                f"candidate scoring cash=${int(state.money)}->${economics.money_after}",
                *bond_notes,
                f"whole-build gain including Bond projection={resulting_build_gain:.3f}",
                f"net spend=${economics.net_spend}",
                f"money after=${economics.money_after}",
                f"economic adjustment={economics.total_adjustment:.3f}",
            ),
        )

    def score_replacement(self, state, candidate, replacement):
        if not isinstance(candidate, Joker):
            return original_replacement(self, state, candidate, replacement)

        index = int(replacement.replace_index)
        if index < 0 or index >= len(state.jokers):
            return original_replacement(self, state, candidate, replacement)
        incumbent = state.jokers[index]
        economics = self._economics(
            state,
            candidate,
            incumbent=incumbent,
            replacement=True,
        )
        if economics.money_after < 0:
            return original_replacement(self, state, candidate, replacement)

        baseline = copy.deepcopy(state)
        removed = baseline.jokers.pop(index)
        incumbent_gain = float(
            self.transition_planner.evaluator.evaluate(baseline, removed).total_gain
        )
        candidate_state = copy.deepcopy(baseline)
        candidate_state.money = int(economics.money_after)
        candidate_gain = float(
            self.transition_planner.evaluator.evaluate(candidate_state, candidate).total_gain
        )
        raw_build_delta = candidate_gain - incumbent_gain
        bond_bonus, bond_notes = joker_policy_module._bond_transition_bonus(
            state,
            candidate,
            replace_index=index,
        )
        resulting_build_gain = raw_build_delta + bond_bonus
        eligible = (
            bool(getattr(replacement, "eligible", True))
            and getattr(replacement, "blocked_reason", None) is None
            and raw_build_delta > self.thresholds.minimum_replacement_build_delta
            and resulting_build_gain > self.thresholds.minimum_replacement_build_delta
        )
        total = resulting_build_gain + economics.total_adjustment
        return JokerAcquisitionOption(
            REPLACE,
            resulting_build_gain,
            total,
            economics,
            eligible,
            replace_index=index,
            replace_joker=type(incumbent).__name__,
            rationale=(
                *replacement.rationale,
                f"actual incumbent whole-build marginal at current cash={incumbent_gain:.3f}",
                f"candidate whole-build marginal at money_after=${economics.money_after}: {candidate_gain:.3f}",
                f"post-transaction raw replacement delta={raw_build_delta:.3f}",
                *bond_notes,
                f"sell credit=${economics.sell_credit}",
                f"net spend=${economics.net_spend}",
                f"money after=${economics.money_after}",
                f"economic adjustment={economics.total_adjustment:.3f}",
            ),
        )

    JokerAcquisitionPolicy._score_add = score_add
    JokerAcquisitionPolicy._score_replacement = score_replacement
    JokerAcquisitionPolicy._post_transaction_joker_value_installed = True
