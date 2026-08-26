from __future__ import annotations

"""Bounded visible-shop planning for canonical Bond-derived Joker pairs.

D2 normally evaluates each visible Joker against the current roster. That is the
right default, but it cannot see a pair whose second component becomes worth buying
only after the first visible component is acquired. The historical short-horizon
planner encoded named Joker pairs, which duplicates strategy knowledge outside the
canonical Currency-Wars-style Bond/composition system.

This adapter adds one generic two-checkpoint exception without a combo table:

* neither visible Joker may already be an actionable D2 purchase;
* the first component must already be a mechanically eligible D2 ADD option and may
  fail only the ordinary standalone purchase-advantage threshold;
* after projecting that exact first purchase and its cash/slot consequences, the
  second component must become a real D2 BUY;
* the second component's D2 build value must strictly improve because the first was
  added, proving that the sequence is a mechanical/composition interaction rather
  than two unrelated speculative buys;
* both incremental steps are normalized through the existing D14 ShopUtilityScale;
* the combined plan must beat the action D14 would otherwise execute.

Only one purchase is emitted per checkpoint. The second purchase is committed only
while it remains visible, affordable, and freshly admitted by D2 after authoritative
re-observation. No hidden shop contents, RNG state, future draw order, or named Joker
combination is consulted.
"""

from dataclasses import replace

from games.balatro.actions import BUY_JOKER, BalatroAction
from games.balatro.joker_edition import joker_has_negative_edition
from games.balatro.joker_policy import BUY, HOLD
from games.balatro.shop_arbiter import (
    BuildAwareShopArbiter,
    ShopArbiterDecision,
    _ExecutableJokerDecision,
)


_EPSILON = 1e-12


def _identity(item: object) -> tuple[object | None, str, str, int | None]:
    live_id = getattr(item, "live_id", None)
    center = str(getattr(item, "center", "") or "")
    label = str(
        getattr(item, "label", None)
        or getattr(item, "name", None)
        or type(item).__name__
    )
    area_index = getattr(item, "area_index", None)
    try:
        area_index = int(area_index) if area_index is not None else None
    except (TypeError, ValueError):
        area_index = None
    return live_id, center, label, area_index


def _matches(item: object, identity: tuple[object | None, str, str, int | None]) -> bool:
    live_id, center, label, area_index = identity
    item_live_id, item_center, item_label, item_area_index = _identity(item)
    if live_id is not None and item_live_id == live_id:
        return True
    if center and item_center == center:
        return True
    if area_index is not None and item_area_index == area_index and item_label == label:
        return True
    return bool(label and item_label == label)


def _project_add(state, candidate, money_after: int):
    projected = state.copy()
    projected.money = int(money_after)
    projected.jokers = list(getattr(projected, "jokers", ()) or ())
    if joker_has_negative_edition(candidate):
        projected.joker_slots = int(getattr(projected, "joker_slots", 0) or 0) + 1
    projected.jokers.append(candidate)
    return projected


def _standalone_add_option(decision):
    if decision.action != HOLD or len(tuple(decision.options or ())) != 1:
        return None
    option = decision.options[0]
    if option.mode != BUY or not option.eligible:
        return None
    return option


def _executable(candidate, decision, candidate_index: int):
    return _ExecutableJokerDecision(
        action=BalatroAction(BUY_JOKER, target=candidate),
        source="JOKER_BUY",
        total=float(decision.selected.total_advantage),
        candidate=candidate,
        decision=decision,
        candidate_index=int(candidate_index),
    )


def install_bond_visible_shop_bundle_policy() -> None:
    if getattr(BuildAwareShopArbiter, "_bond_visible_shop_bundle_installed", False):
        return

    original_decide = BuildAwareShopArbiter.decide

    def decide(self, state, visible_actions, *, reroll_cost: int | None):
        pending = getattr(self, "_pending_bond_visible_pair", None)
        if pending is not None:
            self._pending_bond_visible_pair = None
            candidate = next(
                (
                    item
                    for item in tuple(getattr(state, "shop_jokers", ()) or ())
                    if _matches(item, pending["second_identity"])
                ),
                None,
            )
            if candidate is not None:
                policy = self._joker_policy_for_state(state)
                decision = policy.decide(state, candidate)
                if decision.action == BUY and decision.selected is not None:
                    candidate_index = next(
                        (
                            index
                            for index, item in enumerate(tuple(getattr(state, "shop_jokers", ()) or ()))
                            if item is candidate
                        ),
                        0,
                    )
                    executable = _executable(candidate, decision, candidate_index)
                    utility = self.utility_scale.joker_gain(state, executable)
                    hold = float(self.shop_policy.hold_bias)
                    return ShopArbiterDecision(
                        action=executable.action,
                        source="JOKER_BOND_PAIR_COMPLETE",
                        total=hold + float(utility.gain),
                        hold_baseline=hold,
                        normalized_gain=float(utility.gain),
                        joker=decision,
                        rationale=(
                            "complete canonical visible-Joker pair after authoritative re-observation",
                            f"pair first component={pending['first_label']}",
                            f"pair second component={_identity(candidate)[2]}",
                            "fresh D2 still admits the second component; committed pair is therefore not orphaned",
                            f"fresh D14 second-step normalized gain={float(utility.gain):.3f}",
                            *tuple(decision.rationale),
                            *tuple(utility.notes),
                        ),
                    )

        baseline = original_decide(
            self,
            state,
            visible_actions,
            reroll_cost=reroll_cost,
        )

        shop = tuple(getattr(state, "shop_jokers", ()) or ())
        if len(shop) < 2:
            return baseline

        policy = self._joker_policy_for_state(state)
        standalone = tuple(policy.decide(state, candidate) for candidate in shop)
        # If either component is already actionable, ordinary D2/D14 can choose it
        # directly. Pair planning exists only for the one-at-a-time blind spot.
        nonactionable = tuple(
            index
            for index, decision in enumerate(standalone)
            if decision.action == HOLD
        )
        if len(nonactionable) < 2:
            return baseline

        best = None
        for first_index in nonactionable:
            first = shop[first_index]
            first_decision = standalone[first_index]
            first_option = _standalone_add_option(first_decision)
            if first_option is None:
                continue

            first_selected = replace(
                first_decision,
                action=BUY,
                selected=first_option,
                rationale=(
                    *tuple(first_decision.rationale),
                    "temporarily admitted only as the first step of a verified visible two-Joker Bond plan",
                ),
            )
            first_executable = _executable(first, first_selected, first_index)
            first_utility = self.utility_scale.joker_gain(state, first_executable)
            projected = _project_add(
                state,
                first,
                int(first_option.economics.money_after),
            )

            for second_index in nonactionable:
                if second_index == first_index:
                    continue
                second = shop[second_index]
                second_before = standalone[second_index]
                before_option = _standalone_add_option(second_before)
                before_build_gain = (
                    float(before_option.build_gain)
                    if before_option is not None
                    else max(
                        (
                            float(option.build_gain)
                            for option in tuple(second_before.options or ())
                            if option.mode == BUY
                        ),
                        default=float("-inf"),
                    )
                )

                second_after = policy.decide(projected, second)
                if second_after.action != BUY or second_after.selected is None:
                    continue
                if (
                    float(second_after.selected.build_gain)
                    <= before_build_gain + _EPSILON
                ):
                    continue

                second_executable = _executable(
                    second,
                    second_after,
                    second_index,
                )
                second_utility = self.utility_scale.joker_gain(
                    projected,
                    second_executable,
                )
                combined_gain = (
                    float(first_utility.gain) + float(second_utility.gain)
                )
                if combined_gain <= float(baseline.normalized_gain) + _EPSILON:
                    continue

                candidate = (
                    combined_gain,
                    float(second_after.selected.build_gain) - before_build_gain,
                    -first_index,
                    -second_index,
                    first,
                    second,
                    first_selected,
                    second_after,
                    first_utility,
                    second_utility,
                )
                if best is None or candidate[:4] > best[:4]:
                    best = candidate

        if best is None:
            return baseline

        (
            combined_gain,
            interaction_gain,
            _,
            _,
            first,
            second,
            first_decision,
            second_decision,
            first_utility,
            second_utility,
        ) = best
        self._pending_bond_visible_pair = {
            "first_label": _identity(first)[2],
            "second_identity": _identity(second),
        }
        hold = float(self.shop_policy.hold_bias)
        return ShopArbiterDecision(
            action=BalatroAction(BUY_JOKER, target=first),
            source="JOKER_BOND_PAIR_START",
            total=hold + float(combined_gain),
            hold_baseline=hold,
            normalized_gain=float(combined_gain),
            joker=first_decision,
            reroll=baseline.reroll,
            rationale=(
                "canonical two-visible-Joker plan beats the ordinary D14 action",
                f"first component={_identity(first)[2]}",
                f"second component={_identity(second)[2]}",
                f"second D2 build gain improves by {float(interaction_gain):.3f} only after the first component",
                f"first-step D14 normalized gain={float(first_utility.gain):.3f}",
                f"second-step D14 normalized gain={float(second_utility.gain):.3f}",
                f"combined verified plan gain={float(combined_gain):.3f}",
                f"replaced D14 action={baseline.source} gain={float(baseline.normalized_gain):.3f}",
                "no named Joker pair or hidden future shop information is used",
                "execute one purchase, re-observe, then require fresh D2 admission before the committed second purchase",
                *tuple(first_utility.notes),
                *tuple(second_utility.notes),
            ),
        )

    BuildAwareShopArbiter.decide = decide
    BuildAwareShopArbiter._bond_visible_shop_bundle_installed = True
