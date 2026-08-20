from __future__ import annotations

"""Balatro v1.0.0 live-optimization contract.

This release layer contains corrections derived from the 2026-08-20 five-attempt
Red/White review.  The rules are deliberately narrow and public-state only:

* Clearance Sale is bought before other paid shop development when it is already
  an admitted purchase, because delaying the permanent discount is dominated.
* A D2 Joker replacement is a two-checkpoint *committed transaction*: sell,
  re-observe, then buy the exact visible Joker that justified the sale.
* A dominant strategy at the normal commit threshold is committed regardless of
  Ante.  Early Antes may still explore secondary routes with spare capacity, but
  they may not destroy an aligned component of the strong dominant route.
* Superposition is Bronze, not Silver, for Straight.

No rule uses hidden RNG state or future shop/draw ordering.
"""

from dataclasses import replace

from games.balatro.actions import BUY_JOKER, BUY_VOUCHER, BalatroAction
from games.balatro.strategy import (
    BRONZE,
    COMMITTED,
    GOLD,
    MATURE,
    SILVER,
    BalatroStrategyTracker,
    StrategyDefinition,
)
from games.balatro.strategy_value import StrategyAwareJokerBuildTransitionPlanner
from games.balatro.shop_arbiter import BuildAwareShopArbiter, ShopArbiterDecision


_POSITIVE_TIERS = frozenset({GOLD, SILVER, BRONZE})


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _item_label(item: object) -> str:
    return str(
        getattr(item, "label", None)
        or getattr(item, "name", None)
        or getattr(item, "center", None)
        or type(item).__name__
    )


def _item_identity(item: object) -> tuple[object | None, str, str]:
    return (
        getattr(item, "live_id", None),
        _normalize(getattr(item, "center", "")),
        _normalize(_item_label(item)),
    )


def _matches_identity(item: object, identity: tuple[object | None, str, str]) -> bool:
    live_id, center, label = identity
    item_live_id, item_center, item_label = _item_identity(item)
    if live_id is not None and item_live_id == live_id:
        return True
    if center and item_center == center:
        return True
    return bool(label and item_label == label)


def _price(item: object) -> int:
    value = getattr(item, "price", getattr(item, "cost", 0))
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _free_joker_slots(state) -> int:
    return max(
        0,
        int(getattr(state, "joker_slots", 5) or 5)
        - len(getattr(state, "jokers", ()) or ()),
    )


def install_v1_0_0_policy() -> None:
    if getattr(BuildAwareShopArbiter, "_v1_0_0_policy_installed", False):
        return

    # ------------------------------------------------------------------
    # Relationship correction: Superposition supports Straight, but it is
    # not a defining/scoring engine and must not contribute Silver evidence.
    # ------------------------------------------------------------------
    original_relationship_for = StrategyDefinition.relationship_for

    def relationship_for(self, item, *, kind: str):
        if (
            self.strategy_id == "straight"
            and str(kind).upper() == "JOKER"
            and "superposition" in {
                _normalize(type(item).__name__),
                _normalize(getattr(item, "name", "")),
                _normalize(getattr(item, "label", "")),
                _normalize(getattr(item, "center", "")),
            }
        ):
            return BRONZE
        return original_relationship_for(self, item, kind=kind)

    StrategyDefinition.relationship_for = relationship_for

    # ------------------------------------------------------------------
    # Score-based commitment.  The catalogue relationship scores determine
    # whether a route reaches the commit threshold; Ante only controls how
    # freely secondary routes may be explored after that point.
    # ------------------------------------------------------------------
    original_observe = BalatroStrategyTracker.observe

    def observe(self, state):
        resolution = original_observe(self, state)
        dominant = resolution.assessment(resolution.dominant_strategy_id)
        if dominant is None or resolution.active_status == MATURE:
            return resolution
        commit_floor = self._number(self._config(state), "commit_threshold", 9.0)
        if float(dominant.score) < commit_floor:
            return resolution
        return replace(
            resolution,
            active_status=COMMITTED,
            active_strategy_id=dominant.strategy_id,
            highlighted_strategy_id=dominant.strategy_id,
            committed_strategy_id=dominant.strategy_id,
            rationale=(
                *resolution.rationale,
                f"v1.0.0 score-based commitment: dominant score={dominant.score:.3f} >= commit threshold={commit_floor:.3f}",
                "early Ante may explore secondary strategies only when doing so does not sabotage the committed dominant route",
            ),
        )

    BalatroStrategyTracker.observe = observe

    # ------------------------------------------------------------------
    # Strong-route replacement protection.  Secondary/pivot exploration can
    # occupy a free slot, but a candidate that is not positive for the strong
    # dominant route may not evict one of that route's aligned components.
    # ------------------------------------------------------------------
    original_transition_plan = StrategyAwareJokerBuildTransitionPlanner.plan

    def transition_plan(self, state, candidate):
        transition = original_transition_plan(self, state, candidate)
        if not transition.alternatives:
            return transition

        tracker = self.evaluator.strategy_tracker
        resolution = tracker.observe(state)
        dominant = resolution.assessment(resolution.dominant_strategy_id)
        if dominant is None:
            return transition
        commit_floor = tracker._number(tracker._config(state), "commit_threshold", 9.0)
        if float(dominant.score) < commit_floor:
            return transition

        dominant_id = dominant.strategy_id
        candidate_relationship = tracker._relationships_for(candidate, kind="JOKER").get(
            dominant_id
        )
        if candidate_relationship in _POSITIVE_TIERS:
            return transition

        guarded = []
        changed = False
        for option in transition.alternatives:
            index = int(option.replace_index)
            incumbent = state.jokers[index]
            incumbent_relationship = tracker._relationships_for(
                incumbent, kind="JOKER"
            ).get(dominant_id)
            if incumbent_relationship not in _POSITIVE_TIERS:
                guarded.append(option)
                continue
            changed = True
            guarded.append(
                replace(
                    option,
                    eligible=False,
                    blocked_reason=(
                        option.blocked_reason
                        or "strong dominant strategy component cannot be displaced by an off-primary candidate"
                    ),
                    rationale=(
                        *option.rationale,
                        f"v1.0.0 dominant-route protection: {dominant.name} score={dominant.score:.3f}",
                        f"incumbent is {incumbent_relationship} for the dominant route; candidate is not positive for that route",
                        "secondary/pivot exploration may use spare capacity but cannot sabotage first-place strategy infrastructure",
                    ),
                )
            )

        if not changed:
            return transition
        alternatives = tuple(
            sorted(guarded, key=lambda option: (-float(option.build_delta), int(option.replace_index)))
        )
        eligible = tuple(option for option in alternatives if option.eligible)
        replacement = eligible[0] if eligible else None
        if replacement is not None and float(replacement.build_delta) <= self.minimum_replacement_delta:
            replacement = None
        return replace(
            transition,
            action="REPLACE" if replacement is not None else "HOLD",
            replacement=replacement,
            alternatives=alternatives,
            rationale=(
                *transition.rationale,
                "v1.0.0 strong-dominant replacement guard applied",
            ),
        )

    StrategyAwareJokerBuildTransitionPlanner.plan = transition_plan

    # ------------------------------------------------------------------
    # Shop transaction ordering/state.  This state belongs to the arbiter
    # instance and therefore survives the required post-sale re-observation.
    # ------------------------------------------------------------------
    original_decide = BuildAwareShopArbiter.decide

    def decide(self, state, visible_actions, *, reroll_cost: int | None):
        hold = float(self.shop_policy.hold_bias)

        # Complete an already-authorized Joker replacement before doing anything
        # else.  The sell was justified only by this exact visible candidate.
        pending = getattr(self, "_v1_0_0_pending_replacement", None)
        if pending is not None:
            target = next(
                (
                    joker
                    for joker in getattr(state, "shop_jokers", ()) or ()
                    if _matches_identity(joker, pending["identity"])
                ),
                None,
            )
            if (
                target is not None
                and _free_joker_slots(state) > 0
                and int(getattr(state, "money", 0) or 0) >= _price(target)
            ):
                self._v1_0_0_pending_replacement = None
                gain = max(0.001, float(pending.get("normalized_gain", 0.001)))
                return ShopArbiterDecision(
                    action=BalatroAction(BUY_JOKER, target=target),
                    source="JOKER_BUY",
                    total=hold + gain,
                    hold_baseline=hold,
                    normalized_gain=gain,
                    rationale=(
                        "v1.0.0 committed Joker replacement transaction",
                        f"complete purchase of {_item_label(target)} before packs, rerolls, vouchers, or END_SHOP",
                        "the preceding sale is not allowed to become an orphan sale after a fresh shop replan",
                    ),
                )
            # The target genuinely disappeared or became illegal/unaffordable.
            # Release the transaction rather than looping forever.
            self._v1_0_0_pending_replacement = None

        # Clearance Sale is a permanent discount.  If the deterministic voucher
        # policy already admits it at this state, taking other paid shop actions
        # before it is dominated because those actions could have been cheaper.
        clearance_action = next(
            (
                action
                for action in visible_actions
                if action.name == BUY_VOUCHER
                and _normalize(_item_label(action.target)) == "clearancesale"
            ),
            None,
        )
        if clearance_action is not None:
            ranked = self.shop_policy.rank_actions(state, [clearance_action])
            if ranked and float(ranked[0].total) > hold:
                score = ranked[0]
                return ShopArbiterDecision(
                    action=clearance_action,
                    source="DETERMINISTIC",
                    total=float(score.total),
                    hold_baseline=hold,
                    normalized_gain=max(0.0, float(score.total) - hold),
                    deterministic=score,
                    rationale=(
                        "v1.0.0 shop ordering: admitted Clearance Sale precedes other paid development",
                        "buying the permanent discount first reduces the cost of later shop purchases in the same and future shops",
                        *score.notes,
                    ),
                )

        result = original_decide(
            self,
            state,
            visible_actions,
            reroll_cost=reroll_cost,
        )
        if result.source == "JOKER_REPLACE_SELL" and result.joker is not None:
            candidate_name = str(result.joker.candidate)
            candidate = next(
                (
                    joker
                    for joker in getattr(state, "shop_jokers", ()) or ()
                    if type(joker).__name__ == candidate_name
                ),
                None,
            )
            if candidate is not None:
                self._v1_0_0_pending_replacement = {
                    "identity": _item_identity(candidate),
                    "normalized_gain": float(result.normalized_gain),
                }
        return result

    BuildAwareShopArbiter.decide = decide
    BuildAwareShopArbiter._v1_0_0_policy_installed = True
