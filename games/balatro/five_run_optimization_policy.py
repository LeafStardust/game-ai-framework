from __future__ import annotations

"""Public-state optimizations derived from the 2026-08-20 five-run review.

The rules in this module are intentionally narrow. They correct deterministic
value mistakes or activate mechanics that the ordinary policy can otherwise leave
idle, without reading future shops, draw order, or RNG state.
"""

from dataclasses import replace

from games.balatro.actions import (
    BUY_AND_USE_CONSUMABLE,
    BUY_CONSUMABLE,
    BUY_JOKER,
    DISCARD_CARDS,
    END_SHOP,
    SELL_CONSUMABLE,
    SELL_JOKER,
    BalatroAction,
)
from games.balatro.live.consumable_timing_base import (
    HOLD,
    USE,
    ConsumableTimingRecommendation,
    LiveConsumableTimingPolicy as BaseConsumableTimingPolicy,
)
from games.balatro.live.hand_action_policy import (
    PACE_PLAY,
    LiveHandActionPolicy,
)
from games.balatro.shop_arbiter import BuildAwareShopArbiter, ShopArbiterDecision
from games.balatro.strategy import GOLD
import games.balatro.strategy_conditional_relationships as conditional_relationships


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _label(item: object) -> str:
    return str(
        getattr(item, "label", None)
        or getattr(item, "name", None)
        or getattr(item, "center", None)
        or type(item).__name__
    )


def _token(item: object) -> str:
    return _normalize(type(item).__name__)


def _price(item: object) -> int:
    value = getattr(item, "price", getattr(item, "cost", 0))
    if isinstance(value, dict):
        value = value.get("buy", 0)
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _held_joker_tokens(state) -> frozenset[str]:
    return frozenset(_token(joker) for joker in getattr(state, "jokers", ()) or ())


def _is_negative(item: object) -> bool:
    return _normalize(getattr(item, "edition", "")) == "negative"


def _shop_decision(
    self,
    *,
    state,
    action: BalatroAction,
    source: str,
    gain: float,
    rationale: tuple[str, ...],
) -> ShopArbiterDecision:
    hold = float(self.shop_policy.hold_bias)
    gain = max(0.001, float(gain))
    return ShopArbiterDecision(
        action=action,
        source=source,
        total=hold + gain,
        hold_baseline=hold,
        normalized_gain=gain,
        rationale=rationale,
    )


def _straight_replacement_index(state) -> int | None:
    """Return a replaceable weak slot for the Devious + Four Fingers activation."""
    priority = {
        "bannerjoker": 0,
        "hallucinationjoker": 1,
        "goldenjoker": 2,
        "greenjoker": 3,
        "joker": 4,
        "slyjoker": 5,
        "jollyjoker": 6,
    }
    candidates: list[tuple[int, int]] = []
    for index, joker in enumerate(getattr(state, "jokers", ()) or ()):
        token = _token(joker)
        if token in {"deviousjoker", "fourfingersjoker"}:
            continue
        if bool(getattr(joker, "eternal", False)) or _is_negative(joker):
            continue
        if token in priority:
            candidates.append((priority[token], index))
    if not candidates:
        return None
    return min(candidates)[1]


def install_five_run_optimization_policy() -> None:
    if getattr(BuildAwareShopArbiter, "_five_run_optimization_installed", False):
        return

    # ------------------------------------------------------------------
    # Rocket / To the Moon: the catalogue guard makes either Joker Silver.
    # Owning one and evaluating the other upgrades the pair to Gold, and once
    # both are held each member remains Gold evidence for the combined route.
    # ------------------------------------------------------------------
    original_conditional = conditional_relationships.conditional_joker_relationship

    def conditional_joker_relationship(state, strategy_id: str, item: object) -> str:
        token = _token(item)
        if strategy_id == "cash_growth" and token in {"rocketjoker", "tothemoonjoker"}:
            owned = _held_joker_tokens(state)
            other = "tothemoonjoker" if token == "rocketjoker" else "rocketjoker"
            if other in owned:
                return GOLD
        return original_conditional(state, strategy_id, item)

    conditional_relationships.conditional_joker_relationship = conditional_joker_relationship

    # ------------------------------------------------------------------
    # Hermit: current Balatro doubles money with a +$20 gain cap. The old timing
    # formula incorrectly treated $20 as a final-money cap, producing zero gain
    # at $20+. Preserve below $20 when there is room, but spend at the maximum
    # deterministic +$20 payout or under slot pressure.
    # ------------------------------------------------------------------
    original_economy = BaseConsumableTimingPolicy._recommend_economy

    def recommend_economy(self, state, consumable, *, name: str):
        if name != "The Hermit":
            return original_economy(self, state, consumable, name=name)

        money = max(0, int(getattr(state, "money", 0) or 0))
        gain = min(money, 20)
        required = self._required_per_hand(state)
        slots_full = self._consumable_slots_full(state)
        if gain <= 0:
            return self._hold(
                state,
                consumable,
                "Hermit has no positive deterministic money gain",
                immediate_gain=0.0,
            )
        if money >= 20:
            decision = USE
            reason = "Hermit has reached its maximum deterministic +$20 payout"
        elif slots_full:
            decision = USE
            reason = "full consumable slots plus positive deterministic Hermit gain"
        else:
            decision = HOLD
            reason = "Hermit is below $20, so preserving it can increase deterministic payout"
        return ConsumableTimingRecommendation(
            decision=decision,
            consumable=consumable,
            target=None,
            before_projection=None,
            after_projection=None,
            required_per_hand=required,
            immediate_gain=float(gain),
            rationale=(
                f"{decision}: {reason}",
                f"Hermit money ${money} -> ${money + gain}",
                f"deterministic money gain=${gain}",
                f"consumable slots full={slots_full}",
            ),
        )

    BaseConsumableTimingPolicy._recommend_economy = recommend_economy

    # ------------------------------------------------------------------
    # Shop arbitration:
    #   * take a guaranteed net-profitable Hermit Buy & Use transaction;
    #   * never leave a shop with Perkeo and no consumable when a cheap safe seed
    #     is visible, because that throws away Perkeo's free Negative copy;
    #   * monetize surplus Negative Perkeo copies while retaining an identical seed;
    #   * activate Straight when Devious is already owned and Four Fingers appears.
    # ------------------------------------------------------------------
    original_shop_decide = BuildAwareShopArbiter.decide

    def shop_decide(self, state, visible_actions, *, reroll_cost: int | None):
        money = max(0, int(getattr(state, "money", 0) or 0))

        pending = getattr(self, "_five_run_pending_four_fingers", False)
        if pending:
            target = next(
                (
                    joker
                    for joker in getattr(state, "shop_jokers", ()) or ()
                    if _token(joker) == "fourfingersjoker"
                ),
                None,
            )
            if (
                target is not None
                and len(getattr(state, "jokers", ()) or ()) < int(getattr(state, "joker_slots", 5) or 5)
                and money >= _price(target)
            ):
                self._five_run_pending_four_fingers = False
                return _shop_decision(
                    self,
                    state=state,
                    action=BalatroAction(BUY_JOKER, target=target),
                    source="JOKER_BUY",
                    gain=3.0,
                    rationale=(
                        "five-run correction: complete Devious + Four Fingers Straight activation",
                        "the preceding weak-slot sale was authorized only for this visible Four Fingers",
                    ),
                )
            self._five_run_pending_four_fingers = False

        # A Hermit purchase is a deterministic cash arbitrage whenever the payout
        # after paying its price exceeds that price. Execute it immediately rather
        # than letting interest/reserve utility hide literal net profit.
        for consumable in getattr(state, "shop_consumables", ()) or ():
            if _normalize(_label(consumable)) not in {"thehermit", "hermit"}:
                continue
            price = _price(consumable)
            money_after = money - price
            if money_after < 0:
                continue
            payout = min(money_after, 20)
            final_money = money_after + payout
            net_profit = final_money - money
            if net_profit > 0:
                return _shop_decision(
                    self,
                    state=state,
                    action=BalatroAction(BUY_AND_USE_CONSUMABLE, target=consumable),
                    source="CONSUMABLE_BUY_AND_USE",
                    gain=float(net_profit),
                    rationale=(
                        "five-run correction: guaranteed profitable Hermit Buy & Use",
                        f"cash ${money} -> ${final_money} after ${price} purchase and +${payout} Hermit payout",
                        f"deterministic net profit=${net_profit}",
                    ),
                )

        owned = _held_joker_tokens(state)
        has_perkeo = "perkeojoker" in owned
        if has_perkeo:
            held = list(getattr(state, "consumables", ()) or ())
            # A Negative copy created by Perkeo is free and consumes no slot. If an
            # identical seed remains, selling one surplus Negative copy converts
            # the ability into deterministic cash without disabling next-shop copy.
            for index, consumable in enumerate(held):
                if not _is_negative(consumable):
                    continue
                name = _normalize(_label(consumable))
                if any(
                    other is not consumable and _normalize(_label(other)) == name
                    for other in held
                ):
                    return _shop_decision(
                        self,
                        state=state,
                        action=BalatroAction(SELL_CONSUMABLE, target=index),
                        source="PERKEO_CASH",
                        gain=max(1.0, float(getattr(consumable, "sell_cost", 1) or 1)),
                        rationale=(
                            "five-run correction: monetize surplus Negative Perkeo copy",
                            f"retain another {_label(consumable)} as the next Perkeo seed",
                        ),
                    )

        result = original_shop_decide(
            self,
            state,
            visible_actions,
            reroll_cost=reroll_cost,
        )

        # Devious + Four Fingers is a real Straight engine. The second/third-place
        # shortlist is meant to permit this activation instead of preserving weak
        # no-discard filler merely because it is already owned.
        four_fingers = next(
            (
                joker
                for joker in getattr(state, "shop_jokers", ()) or ()
                if _token(joker) == "fourfingersjoker"
            ),
            None,
        )
        if (
            four_fingers is not None
            and "deviousjoker" in owned
            and "fourfingersjoker" not in owned
            and money >= _price(four_fingers)
        ):
            jokers = list(getattr(state, "jokers", ()) or ())
            slots = int(getattr(state, "joker_slots", 5) or 5)
            if len(jokers) < slots:
                return _shop_decision(
                    self,
                    state=state,
                    action=BalatroAction(BUY_JOKER, target=four_fingers),
                    source="JOKER_BUY",
                    gain=3.0,
                    rationale=(
                        "five-run correction: Four Fingers activates the existing Devious Straight route",
                        "secondary/third-place strategy infrastructure may be developed when the combined route outranks weak filler",
                    ),
                )
            replace_index = _straight_replacement_index(state)
            if replace_index is not None:
                self._five_run_pending_four_fingers = True
                return _shop_decision(
                    self,
                    state=state,
                    action=BalatroAction(SELL_JOKER, target=replace_index),
                    source="JOKER_REPLACE_SELL",
                    gain=3.0,
                    rationale=(
                        "five-run correction: replace weak filler to activate Devious + Four Fingers Straight",
                        f"replacement slot={replace_index}",
                        "follow-up Four Fingers purchase requires a fresh settled shop observation",
                    ),
                )

        # Do not throw away Perkeo's end-of-shop trigger. Only intervene when the
        # ordinary arbiter would leave and there is no held seed at all. Preserve a
        # $5 reserve so the copy engine cannot sabotage survival for an expensive
        # speculative consumable.
        if has_perkeo and not getattr(state, "consumables", ()) and result.action.name == END_SHOP:
            affordable = [
                consumable
                for consumable in getattr(state, "shop_consumables", ()) or ()
                if _price(consumable) <= max(0, money - 5)
            ]
            if affordable:
                seed = min(affordable, key=lambda item: (_price(item), _normalize(_label(item))))
                return _shop_decision(
                    self,
                    state=state,
                    action=BalatroAction(BUY_CONSUMABLE, target=seed),
                    source="PERKEO_SEED",
                    gain=1.0,
                    rationale=(
                        "five-run correction: Perkeo must not leave shop with an empty consumable area",
                        f"buy cheapest safe seed {_label(seed)} for ${_price(seed)}",
                        "Perkeo will create a free Negative copy at end of shop; $5 cash reserve retained",
                    ),
                )

        return result

    BuildAwareShopArbiter.decide = shop_decide

    # ------------------------------------------------------------------
    # Burnt Joker training. Burnt triggers on the first discard of the round.
    # If D1 already has a comfortable pace play, one spare discard and one spare
    # hand, prefer its best modeled discard so the permanent hand-level upgrade is
    # not left idle. CLEAR_PATH and marginal-pace states are never overridden.
    # ------------------------------------------------------------------
    original_hand_decide = LiveHandActionPolicy.decide

    def hand_decide(self, state, plans, **kwargs):
        result = original_hand_decide(self, state, plans, **kwargs)
        if "burntjoker" not in _held_joker_tokens(state):
            return result
        if getattr(state, "discards_used", None) != 0:
            return result
        if int(getattr(state, "discards_remaining", 0) or 0) <= 1:
            return result
        if int(getattr(state, "hands_remaining", 0) or 0) <= 1:
            return result
        if result.mode != PACE_PLAY or float(result.best_play_pace_ratio) < 1.35:
            return result

        discards = [plan for plan in result.plans if plan.action.name == DISCARD_CARDS]
        if not discards:
            return result
        training = max(
            discards,
            key=lambda plan: (
                float(plan.value.clear_probability),
                float(plan.value.expected_score),
                len(plan.action.cards),
            ),
        )
        return replace(
            result,
            action=training.action,
            selected_plan=training,
            selected_immediate_score=None,
            selected_pace_ratio=None,
            rationale=(
                "Burnt Joker first-discard training: spend one safe spare discard for a permanent hand level",
                "override applies only with comfortable current pace (>=1.35x), at least two discards, and at least two hands remaining",
                *result.rationale,
            ),
        )

    LiveHandActionPolicy.decide = hand_decide
    BuildAwareShopArbiter._five_run_optimization_installed = True
