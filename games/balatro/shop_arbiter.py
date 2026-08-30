from __future__ import annotations

from dataclasses import dataclass, replace

from games.balatro.actions import (
    BUY_BOOSTER,
    BUY_CONSUMABLE,
    BUY_JOKER,
    BUY_VOUCHER,
    END_SHOP,
    SELL_JOKER,
    BalatroAction,
)
from games.balatro.joker_edition import joker_has_negative_edition
from games.balatro.joker_policy import (
    BUY,
    HOLD,
    REPLACE,
    JokerAcquisitionDecision,
    JokerAcquisitionOption,
    JokerAcquisitionPolicy,
    JokerAcquisitionThresholds,
    _bond_transition_bonus,
)
from games.balatro.playbook import (
    BalatroPlaybookNotFound,
    default_balatro_playbooks,
)
from games.balatro.shop_booster_policy import (
    BoosterAcquisitionThresholds,
    BuildAwareShopBoosterPolicy,
    ShopBoosterRecommendation,
)
from games.balatro.shop_consumable_policy import (
    BUY as CONSUMABLE_BUY,
    BUY_AND_USE as CONSUMABLE_BUY_AND_USE,
    ConsumableAcquisitionDecision,
    ConsumableAcquisitionPolicy,
    ConsumableAcquisitionThresholds,
)
from games.balatro.shop_policy import BalatroShopPolicy, ShopActionScore
from games.balatro.shop_reroll_policy import (
    BuildAwareShopRerollPolicy,
    ShopRerollRecommendation,
    ShopRerollThresholds,
)
from games.balatro.shop_utility_scale import ShopNormalizedUtility, ShopUtilityScale
from games.balatro.state import BalatroState


_BOND_PAIR_EPSILON = 1e-12


@dataclass(frozen=True)
class ShopArbiterDecision:
    """Normalized parent decision over completed SHOP child layers."""

    action: BalatroAction
    source: str
    total: float
    hold_baseline: float
    normalized_gain: float
    deterministic: ShopActionScore | None = None
    joker: JokerAcquisitionDecision | None = None
    consumable: ConsumableAcquisitionDecision | None = None
    booster: ShopBoosterRecommendation | None = None
    reroll: ShopRerollRecommendation | None = None
    rationale: tuple[str, ...] = ()


@dataclass(frozen=True)
class _ExecutableJokerDecision:
    action: BalatroAction
    source: str
    total: float
    candidate: object
    decision: JokerAcquisitionDecision
    candidate_index: int


@dataclass(frozen=True)
class _ExecutableConsumableDecision:
    action: BalatroAction
    source: str
    total: float
    candidate: object
    decision: ConsumableAcquisitionDecision
    candidate_index: int


@dataclass(frozen=True)
class _ExecutableBondPairDecision:
    first: _ExecutableJokerDecision
    second_identity: tuple[object | None, str, str, int | None]
    second_label: str
    interaction_gain: float
    combined_gain: float
    first_utility: ShopNormalizedUtility
    second_utility: ShopNormalizedUtility


@dataclass(frozen=True)
class _ArbiterCandidate:
    action: BalatroAction
    source: str
    total: float
    normalized_gain: float
    priority: int
    child: object | None = None


def _joker_identity(item: object) -> tuple[object | None, str, str, int | None]:
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


def _matches_joker_identity(
    item: object,
    identity: tuple[object | None, str, str, int | None],
) -> bool:
    live_id, center, label, area_index = identity
    item_live_id, item_center, item_label, item_area_index = _joker_identity(item)
    if live_id is not None and item_live_id == live_id:
        return True
    if center and item_center == center:
        return True
    if area_index is not None and item_area_index == area_index and item_label == label:
        return True
    return bool(label and item_label == label)


class BuildAwareShopArbiter:
    """Route the SHOP phase across independently scored child decisions.

    D2 Joker acquisition/replacement, D4 consumable acquisition mode, deterministic
    voucher purchases, unopened-booster option value, reroll, and END_SHOP retain
    separate policies/thresholds. Child policies remain authoritative for admission,
    then D14 recomputes admitted options on one shared parent resource scale before
    cross-family comparison. END_SHOP is the explicit zero-gain parent baseline. The
    arbiter never inspects hidden future shop or pack contents.

    Joker replacement is deliberately a two-checkpoint transaction. D2 may select
    ``SELL_JOKER`` for the incumbent, but the arbiter never chains the follow-up
    purchase. The autonomous loop must observe the settled post-sale SHOP state and
    run D2 again; only that fresh decision may emit ``BUY_JOKER``.

    D14 also owns one bounded visible two-Joker exception for the one-at-a-time D2
    blind spot. Both components must already be visible, the first must be a legal
    standalone ADD that misses only the ordinary purchase threshold, and projecting
    it must make the second a real D2 BUY with strictly improved mechanical build
    value. The combined two-step utility competes in the same normalized D14
    candidate set; no post-arbiter strategy layer may replace the chosen action.
    """

    DETERMINISTIC_ACTIONS = frozenset({BUY_VOUCHER, END_SHOP})

    def __init__(
        self,
        *,
        shop_policy: BalatroShopPolicy | None = None,
        booster_policy: BuildAwareShopBoosterPolicy | None = None,
        reroll_policy: BuildAwareShopRerollPolicy | None = None,
        joker_policy: JokerAcquisitionPolicy | None = None,
        consumable_policy: ConsumableAcquisitionPolicy | None = None,
    ) -> None:
        self.shop_policy = shop_policy or BalatroShopPolicy()
        self.utility_scale = ShopUtilityScale(self.shop_policy)
        self.booster_policy = booster_policy
        self.reroll_policy = reroll_policy
        self.joker_policy = joker_policy
        self.consumable_policy = consumable_policy

    def decide(
        self,
        state: BalatroState,
        visible_actions: list[BalatroAction],
        *,
        reroll_cost: int | None,
    ) -> ShopArbiterDecision:
        if state.phase != "SHOP":
            raise ValueError("shop arbiter requires SHOP phase")

        pending_pair = self._pending_bond_pair_completion(state)
        if pending_pair is not None:
            return pending_pair

        hold = float(self.shop_policy.hold_bias)
        deterministic_actions = [
            action
            for action in visible_actions
            if action.name in self.DETERMINISTIC_ACTIONS
            and action.name != END_SHOP
        ]
        deterministic_ranked = self.shop_policy.rank_actions(
            state,
            deterministic_actions,
        )
        deterministic_best = (
            deterministic_ranked[0] if deterministic_ranked else None
        )

        joker_policy = self._joker_policy_for_state(state)
        standalone_joker_decisions = tuple(
            joker_policy.decide(state, candidate)
            for candidate in tuple(getattr(state, "shop_jokers", ()) or ())
        )
        joker_best = self._best_joker_decision(
            state,
            standalone=standalone_joker_decisions,
        )
        consumable_best = self._best_consumable_decision(state)
        booster_policy = self._booster_policy_for_state(state)
        reroll_policy = self._reroll_policy_for_state(state)

        booster_recommendations = tuple(
            booster_policy.recommend(state, action)
            for action in visible_actions
            if action.name == BUY_BOOSTER
        )
        admitted_boosters = tuple(
            recommendation
            for recommendation in booster_recommendations
            if recommendation.decision == "BUY"
        )
        booster_best = max(
            admitted_boosters,
            key=lambda recommendation: self.utility_scale.booster_gain(
                state,
                recommendation,
            ).gain,
            default=None,
        )

        deterministic_utility = (
            self.utility_scale.baseline_gain(deterministic_best.total, hold)
            if deterministic_best is not None
            else None
        )
        joker_utility = (
            self.utility_scale.joker_gain(state, joker_best)
            if joker_best is not None
            else None
        )
        consumable_utility = (
            self.utility_scale.consumable_gain(state, consumable_best)
            if consumable_best is not None
            else None
        )
        booster_utility = (
            self.utility_scale.booster_gain(state, booster_best)
            if booster_best is not None
            else None
        )
        bond_pair = self._best_visible_bond_pair(
            state,
            policy=joker_policy,
            standalone=standalone_joker_decisions,
        )

        visible_normalized_best = max(
            [
                0.0,
                *(
                    utility.gain
                    for utility in (
                        deterministic_utility,
                        joker_utility,
                        consumable_utility,
                        booster_utility,
                    )
                    if utility is not None
                ),
                *(tuple([bond_pair.combined_gain]) if bond_pair is not None else ()),
            ]
        )

        reroll_visible_actions = [
            action
            for action in visible_actions
            if action.name not in {BUY_JOKER, BUY_CONSUMABLE}
        ]
        reroll_visible_floor = hold + visible_normalized_best
        reroll = reroll_policy.recommend(
            state,
            reroll_visible_actions,
            reroll_cost=reroll_cost,
            visible_score_floor=reroll_visible_floor,
        )
        reroll_utility = (
            self.utility_scale.baseline_gain(reroll.reroll_score, hold)
            if reroll.decision == "REROLL"
            else None
        )

        candidates: list[_ArbiterCandidate] = [
            _ArbiterCandidate(
                action=BalatroAction(END_SHOP),
                source="END_SHOP",
                total=hold,
                normalized_gain=0.0,
                priority=5,
            )
        ]
        if deterministic_best is not None and deterministic_utility is not None:
            candidates.append(
                _ArbiterCandidate(
                    action=deterministic_best.action,
                    source="DETERMINISTIC",
                    total=float(deterministic_best.total),
                    normalized_gain=deterministic_utility.gain,
                    priority=2,
                    child=deterministic_best,
                )
            )
        if joker_best is not None and joker_utility is not None:
            candidates.append(
                _ArbiterCandidate(
                    action=joker_best.action,
                    source=joker_best.source,
                    total=float(joker_best.total),
                    normalized_gain=joker_utility.gain,
                    priority=4,
                    child=joker_best,
                )
            )
        if bond_pair is not None:
            candidates.append(
                _ArbiterCandidate(
                    action=bond_pair.first.action,
                    source="JOKER_BOND_PAIR_START",
                    total=hold + float(bond_pair.combined_gain),
                    normalized_gain=float(bond_pair.combined_gain),
                    priority=4,
                    child=bond_pair,
                )
            )
        if consumable_best is not None and consumable_utility is not None:
            candidates.append(
                _ArbiterCandidate(
                    action=consumable_best.action,
                    source=consumable_best.source,
                    total=float(consumable_best.total),
                    normalized_gain=consumable_utility.gain,
                    priority=3,
                    child=consumable_best,
                )
            )
        if booster_best is not None and booster_utility is not None:
            candidates.append(
                _ArbiterCandidate(
                    action=booster_best.action,
                    source="BOOSTER",
                    total=float(booster_best.total),
                    normalized_gain=booster_utility.gain,
                    priority=1,
                    child=booster_best,
                )
            )
        if reroll.decision == "REROLL":
            if reroll.executable_action is None:
                raise RuntimeError("REROLL recommendation is missing executable action")
            assert reroll_utility is not None
            candidates.append(
                _ArbiterCandidate(
                    action=reroll.executable_action,
                    source="REROLL",
                    total=float(reroll.reroll_score),
                    normalized_gain=reroll_utility.gain,
                    priority=6 if reroll_cost == 0 else 0,
                    child=reroll,
                )
            )

        selected = max(
            candidates,
            key=lambda candidate: (
                candidate.normalized_gain,
                candidate.priority,
            ),
        )
        source = selected.source
        action = selected.action
        total = selected.total
        normalized_gain = selected.normalized_gain
        child = selected.child
        deterministic_text = (
            f"{deterministic_best.total:.3f}"
            if deterministic_best is not None
            else "none"
        )
        consumable_text = (
            f"{consumable_best.total:.3f}"
            if consumable_best is not None
            else "none"
        )
        rationale = [
            f"arbiter source={source}",
            f"selected child score={total:.3f}",
            f"parent END_SHOP baseline={hold:.3f}",
            f"D14 normalized gain={normalized_gain:.3f}",
            f"best deterministic score={deterministic_text}",
            f"best D4 consumable advantage={consumable_text}",
            f"visible normalized floor={visible_normalized_best:.3f}",
            f"admitted boosters={len(admitted_boosters)}/{len(booster_recommendations)}",
            "D14 parent comparison uses one shared money/interest/reserve/slot resource scale after child admission",
            "child admission thresholds remain child-owned",
            "parent arbiter does not predict hidden contents",
        ]

        if source == "END_SHOP":
            return ShopArbiterDecision(
                action=action,
                source="END_SHOP",
                total=total,
                hold_baseline=hold,
                normalized_gain=0.0,
                reroll=reroll,
                rationale=tuple(rationale),
            )

        if source == "DETERMINISTIC":
            assert isinstance(child, ShopActionScore)
            rationale.extend(child.notes)
            return ShopArbiterDecision(
                action=action,
                source="DETERMINISTIC",
                total=total,
                hold_baseline=hold,
                normalized_gain=normalized_gain,
                deterministic=child,
                reroll=reroll,
                rationale=tuple(rationale),
            )

        if source in {"JOKER_BUY", "JOKER_REPLACE_SELL"}:
            assert isinstance(child, _ExecutableJokerDecision)
            selected_option = child.decision.selected
            if selected_option is None:
                raise RuntimeError("actionable D2 Joker decision is missing its selected option")
            rationale.extend(child.decision.rationale)
            rationale.extend(selected_option.rationale)
            if source == "JOKER_REPLACE_SELL":
                rationale.extend(
                    (
                        "replacement execution step=SELL",
                        "follow-up BUY is not chained",
                        "next action requires fresh authoritative observation and D2 replan",
                    )
                )
            return ShopArbiterDecision(
                action=action,
                source=source,
                total=total,
                hold_baseline=hold,
                normalized_gain=normalized_gain,
                joker=child.decision,
                reroll=reroll,
                rationale=tuple(rationale),
            )

        if source == "JOKER_BOND_PAIR_START":
            assert isinstance(child, _ExecutableBondPairDecision)
            self._pending_bond_visible_pair = {
                "first_label": _joker_identity(child.first.candidate)[2],
                "second_identity": child.second_identity,
            }
            rationale.extend(
                (
                    "canonical visible two-Joker plan admitted inside D14 candidate arbitration",
                    f"first component={_joker_identity(child.first.candidate)[2]}",
                    f"second component={child.second_label}",
                    f"second D2 build gain improves by {child.interaction_gain:.3f} only after the first component",
                    f"first-step D14 normalized gain={child.first_utility.gain:.3f}",
                    f"second-step D14 normalized gain={child.second_utility.gain:.3f}",
                    f"combined verified plan gain={child.combined_gain:.3f}",
                    "visible-pair projection reuses standalone D2 whole-build value and recomputes only bounded canonical Bond/economy delta",
                    "no nested projected Joker transition-planner call is permitted inside D14 pair search",
                    "no named Joker pair or hidden future shop information is used",
                    "execute one purchase, re-observe, then require fresh D2 admission before the committed second purchase",
                    *tuple(child.first_utility.notes),
                    *tuple(child.second_utility.notes),
                )
            )
            return ShopArbiterDecision(
                action=action,
                source=source,
                total=total,
                hold_baseline=hold,
                normalized_gain=normalized_gain,
                joker=child.first.decision,
                reroll=reroll,
                rationale=tuple(rationale),
            )

        if source in {"CONSUMABLE_BUY", "CONSUMABLE_BUY_AND_USE"}:
            assert isinstance(child, _ExecutableConsumableDecision)
            selected_option = child.decision.selected
            if selected_option is None:
                raise RuntimeError("actionable D4 consumable decision is missing its selected option")
            rationale.extend(child.decision.rationale)
            rationale.extend(selected_option.rationale)
            return ShopArbiterDecision(
                action=action,
                source=source,
                total=total,
                hold_baseline=hold,
                normalized_gain=normalized_gain,
                consumable=child.decision,
                reroll=reroll,
                rationale=tuple(rationale),
            )

        if source == "BOOSTER":
            assert isinstance(child, ShopBoosterRecommendation)
            rationale.extend(child.rationale)
            return ShopArbiterDecision(
                action=action,
                source="BOOSTER",
                total=total,
                hold_baseline=hold,
                normalized_gain=normalized_gain,
                booster=child,
                reroll=reroll,
                rationale=tuple(rationale),
            )

        assert isinstance(child, ShopRerollRecommendation)
        rationale.extend(child.rationale)
        return ShopArbiterDecision(
            action=action,
            source="REROLL",
            total=total,
            hold_baseline=hold,
            normalized_gain=normalized_gain,
            reroll=child,
            rationale=tuple(rationale),
        )

    def _pending_bond_pair_completion(
        self,
        state: BalatroState,
    ) -> ShopArbiterDecision | None:
        pending = getattr(self, "_pending_bond_visible_pair", None)
        if pending is None:
            return None
        self._pending_bond_visible_pair = None

        candidate = next(
            (
                item
                for item in tuple(getattr(state, "shop_jokers", ()) or ())
                if _matches_joker_identity(item, pending["second_identity"])
            ),
            None,
        )
        if candidate is None:
            return None

        policy = self._joker_policy_for_state(state)
        decision = policy.decide(state, candidate)
        if decision.action != BUY or decision.selected is None:
            return None

        candidate_index = next(
            (
                index
                for index, item in enumerate(tuple(getattr(state, "shop_jokers", ()) or ()))
                if item is candidate
            ),
            0,
        )
        executable = _ExecutableJokerDecision(
            action=BalatroAction(BUY_JOKER, target=candidate),
            source="JOKER_BUY",
            total=float(decision.selected.total_advantage),
            candidate=candidate,
            decision=decision,
            candidate_index=int(candidate_index),
        )
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
                f"pair second component={_joker_identity(candidate)[2]}",
                "fresh D2 still admits the second component; committed pair is therefore not orphaned",
                f"fresh D14 second-step normalized gain={float(utility.gain):.3f}",
                *tuple(decision.rationale),
                *tuple(utility.notes),
            ),
        )

    def _best_visible_bond_pair(
        self,
        state: BalatroState,
        *,
        policy: JokerAcquisitionPolicy | None = None,
        standalone: tuple[JokerAcquisitionDecision, ...] | None = None,
    ) -> _ExecutableBondPairDecision | None:
        shop = tuple(getattr(state, "shop_jokers", ()) or ())
        if len(shop) < 2:
            return None

        policy = policy or self._joker_policy_for_state(state)
        if standalone is None:
            standalone = tuple(policy.decide(state, candidate) for candidate in shop)
        nonactionable = tuple(
            index
            for index, decision in enumerate(standalone)
            if decision.action == HOLD
        )
        if len(nonactionable) < 2:
            return None

        best = None
        for first_index in nonactionable:
            first = shop[first_index]
            first_decision = standalone[first_index]
            first_option = self._standalone_add_option(first_decision)
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
            first_executable = _ExecutableJokerDecision(
                action=BalatroAction(BUY_JOKER, target=first),
                source="JOKER_BUY",
                total=float(first_selected.selected.total_advantage),
                candidate=first,
                decision=first_selected,
                candidate_index=int(first_index),
            )
            first_utility = self.utility_scale.joker_gain(state, first_executable)
            projected = self._project_joker_add(
                state,
                first,
                int(first_option.economics.money_after),
            )

            for second_index in nonactionable:
                if second_index == first_index:
                    continue
                second = shop[second_index]
                second_before = standalone[second_index]
                before_option = self._standalone_add_option(second_before)
                if before_option is None:
                    continue
                if (
                    len(tuple(getattr(projected, "jokers", ()) or ()))
                    >= int(getattr(projected, "joker_slots", 0) or 0)
                    and not joker_has_negative_edition(second)
                ):
                    continue

                before_bond_bonus, _ = _bond_transition_bonus(state, second)
                after_bond_bonus, after_bond_notes = _bond_transition_bonus(projected, second)
                interaction_gain = float(after_bond_bonus) - float(before_bond_bonus)
                if interaction_gain <= _BOND_PAIR_EPSILON:
                    continue

                projected_build_gain = float(before_option.build_gain) + interaction_gain
                economics = policy._economics(
                    projected,
                    second,
                    incumbent=None,
                    replacement=False,
                )
                eligible = (
                    economics.money_after >= 0
                    and projected_build_gain > policy.thresholds.minimum_purchase_build_gain
                )
                projected_advantage = projected_build_gain + economics.total_adjustment
                if (
                    not eligible
                    or projected_advantage <= policy.thresholds.minimum_purchase_advantage
                ):
                    continue

                second_option = JokerAcquisitionOption(
                    mode=BUY,
                    build_gain=projected_build_gain,
                    total_advantage=projected_advantage,
                    economics=economics,
                    eligible=True,
                    rationale=(
                        f"bounded visible-pair build gain={projected_build_gain:.3f}",
                        f"canonical Bond interaction delta={interaction_gain:+.3f}",
                        *tuple(after_bond_notes),
                        f"net spend=${economics.net_spend}",
                        f"money after=${economics.money_after}",
                        f"economic adjustment={economics.total_adjustment:.3f}",
                    ),
                )
                second_after = replace(
                    second_before,
                    action=BUY,
                    selected=second_option,
                    options=(second_option,),
                    rationale=(
                        *tuple(second_before.rationale),
                        "bounded visible-pair projection admitted without nested whole-build D2 replanning",
                    ),
                )
                second_executable = _ExecutableJokerDecision(
                    action=BalatroAction(BUY_JOKER, target=second),
                    source="JOKER_BUY",
                    total=float(second_after.selected.total_advantage),
                    candidate=second,
                    decision=second_after,
                    candidate_index=int(second_index),
                )
                second_utility = self.utility_scale.joker_gain(
                    projected,
                    second_executable,
                )
                combined_gain = float(first_utility.gain) + float(second_utility.gain)
                candidate = (
                    combined_gain,
                    interaction_gain,
                    -first_index,
                    -second_index,
                    _ExecutableBondPairDecision(
                        first=first_executable,
                        second_identity=_joker_identity(second),
                        second_label=_joker_identity(second)[2],
                        interaction_gain=interaction_gain,
                        combined_gain=combined_gain,
                        first_utility=first_utility,
                        second_utility=second_utility,
                    ),
                )
                if best is None or candidate[:4] > best[:4]:
                    best = candidate

        return None if best is None else best[4]

    @staticmethod
    def _standalone_add_option(decision):
        if decision.action != HOLD or len(tuple(decision.options or ())) != 1:
            return None
        option = decision.options[0]
        if option.mode != BUY or not option.eligible:
            return None
        return option

    @staticmethod
    def _project_joker_add(state: BalatroState, candidate, money_after: int) -> BalatroState:
        projected = state.copy()
        projected.money = int(money_after)
        projected.jokers = list(getattr(projected, "jokers", ()) or ())
        if joker_has_negative_edition(candidate):
            projected.joker_slots = int(getattr(projected, "joker_slots", 0) or 0) + 1
        projected.jokers.append(candidate)
        return projected

    def _best_joker_decision(
        self,
        state: BalatroState,
        *,
        standalone: tuple[JokerAcquisitionDecision, ...] | None = None,
    ) -> _ExecutableJokerDecision | None:
        policy = self._joker_policy_for_state(state)
        shop = tuple(getattr(state, "shop_jokers", ()) or ())
        if standalone is None:
            standalone = tuple(policy.decide(state, candidate) for candidate in shop)
        actionable: list[_ExecutableJokerDecision] = []

        for candidate_index, (candidate, decision) in enumerate(zip(shop, standalone)):
            selected = decision.selected
            if selected is None:
                continue

            if decision.action == BUY:
                action = BalatroAction(BUY_JOKER, target=candidate)
                source = "JOKER_BUY"
            elif decision.action == REPLACE:
                replace_index = selected.replace_index
                if replace_index is None:
                    raise RuntimeError("D2 replacement is missing an incumbent slot")
                if replace_index < 0 or replace_index >= len(state.jokers):
                    raise RuntimeError(
                        f"D2 replacement slot {replace_index} is outside the current Joker roster"
                    )
                action = BalatroAction(SELL_JOKER, target=replace_index)
                source = "JOKER_REPLACE_SELL"
            else:
                continue

            actionable.append(
                _ExecutableJokerDecision(
                    action=action,
                    source=source,
                    total=float(selected.total_advantage),
                    candidate=candidate,
                    decision=decision,
                    candidate_index=candidate_index,
                )
            )

        if not actionable:
            return None

        return max(
            actionable,
            key=lambda recommendation: (
                self.utility_scale.joker_gain(state, recommendation).gain,
                -recommendation.candidate_index,
            ),
        )

    def _best_consumable_decision(
        self,
        state: BalatroState,
    ) -> _ExecutableConsumableDecision | None:
        policy = self._consumable_policy_for_state(state)
        actionable: list[_ExecutableConsumableDecision] = []

        for candidate_index, candidate in enumerate(state.shop_consumables):
            decision = policy.decide(state, candidate)
            selected = decision.selected
            if selected is None or selected.executable_action is None:
                continue

            if decision.action == CONSUMABLE_BUY:
                source = "CONSUMABLE_BUY"
            elif decision.action == CONSUMABLE_BUY_AND_USE:
                source = "CONSUMABLE_BUY_AND_USE"
            else:
                continue

            actionable.append(
                _ExecutableConsumableDecision(
                    action=selected.executable_action,
                    source=source,
                    total=float(selected.total_advantage),
                    candidate=candidate,
                    decision=decision,
                    candidate_index=candidate_index,
                )
            )

        if not actionable:
            return None

        return max(
            actionable,
            key=lambda recommendation: (
                self.utility_scale.consumable_gain(state, recommendation).gain,
                -recommendation.candidate_index,
            ),
        )

    def _booster_policy_for_state(
        self,
        state: BalatroState,
    ) -> BuildAwareShopBoosterPolicy:
        if self.booster_policy is not None:
            return self.booster_policy

        try:
            playbook = default_balatro_playbooks().for_state(state)
        except BalatroPlaybookNotFound:
            return BuildAwareShopBoosterPolicy(shop_policy=self.shop_policy)

        thresholds = BoosterAcquisitionThresholds.from_mapping(
            playbook.thresholds_for("D8")
        )
        return BuildAwareShopBoosterPolicy(
            thresholds=thresholds,
            shop_policy=self.shop_policy,
        )

    def _reroll_policy_for_state(
        self,
        state: BalatroState,
    ) -> BuildAwareShopRerollPolicy:
        if self.reroll_policy is not None:
            return self.reroll_policy

        try:
            playbook = default_balatro_playbooks().for_state(state)
        except BalatroPlaybookNotFound:
            return BuildAwareShopRerollPolicy(shop_policy=self.shop_policy)

        thresholds = ShopRerollThresholds(**playbook.thresholds_for("D11"))
        return BuildAwareShopRerollPolicy(
            thresholds=thresholds,
            shop_policy=self.shop_policy,
        )

    def _joker_policy_for_state(self, state: BalatroState) -> JokerAcquisitionPolicy:
        if self.joker_policy is not None:
            return self.joker_policy

        try:
            playbook = default_balatro_playbooks().for_state(state)
        except BalatroPlaybookNotFound:
            return JokerAcquisitionPolicy()

        thresholds = JokerAcquisitionThresholds.from_mapping(
            playbook.strategy.get("decision_thresholds", {}).get(
                "joker_acquisition",
                {},
            )
        )
        return JokerAcquisitionPolicy(thresholds)

    def _consumable_policy_for_state(
        self,
        state: BalatroState,
    ) -> ConsumableAcquisitionPolicy:
        if self.consumable_policy is not None:
            return self.consumable_policy

        try:
            playbook = default_balatro_playbooks().for_state(state)
        except BalatroPlaybookNotFound:
            return ConsumableAcquisitionPolicy()

        thresholds = ConsumableAcquisitionThresholds.from_mapping(
            playbook.strategy.get("decision_thresholds", {}).get(
                "consumable_acquisition",
                {},
            )
        )
        return ConsumableAcquisitionPolicy(thresholds)
