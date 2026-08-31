from __future__ import annotations

from types import SimpleNamespace

from games.balatro.actions import BUY_AND_USE_CONSUMABLE, BUY_CONSUMABLE
from games.balatro.consumable import Consumable, ConsumableContext
from games.balatro.semantic_benchmark import SemanticBenchmarkCase, SemanticCheck
from games.balatro.shop_consumable_policy import (
    BUY_AND_USE,
    HOLD,
    ConsumableAcquisitionPolicy,
)
from games.balatro.shop_policy import BalatroShopPolicy
from games.balatro.shop_utility_scale import ShopUtilityScale
from games.balatro.state import BalatroState


class _SyntheticConsumable(Consumable):
    def __init__(self, name: str, *, category: str = "TAROT", price: int = 1) -> None:
        self.name = name
        self.category = category
        self.price = int(price)

    def can_use(self, context: ConsumableContext) -> bool:
        return True

    def use(self, context: ConsumableContext) -> ConsumableContext:
        return context


class _ZeroBuildEvaluator:
    def evaluate(self, candidate, state):
        return SimpleNamespace(total_gain=0.0, rationale=("synthetic zero build gain",))


class _ImmediateTimingPolicy:
    def __init__(self, gain: float) -> None:
        self.gain = float(gain)

    def recommend(self, state, consumable):
        return SimpleNamespace(
            should_use=self.gain > 0.0,
            immediate_gain=self.gain,
            rationale=(f"synthetic immediate gain={self.gain:.3f}",),
        )


def _full_inventory_blocks_hold_buy_but_allows_explicit_immediate_use() -> SemanticCheck:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 20
    state.consumable_slots = 2
    state.consumables = [object(), object()]
    candidate = _SyntheticConsumable("The Hermit", price=1)
    policy = ConsumableAcquisitionPolicy(
        evaluator=_ZeroBuildEvaluator(),
        timing_policy=_ImmediateTimingPolicy(20.0),
    )

    decision = policy.decide(state, candidate)
    modes = tuple(option.mode for option in decision.options)
    passed = (
        BUY_CONSUMABLE not in modes
        and decision.action == BUY_AND_USE
        and decision.selected is not None
        and decision.selected.mode == BUY_AND_USE
        and decision.selected.executable_action is not None
        and decision.selected.executable_action.name == BUY_AND_USE_CONSUMABLE
        and abs(float(decision.selected.economics.slot_penalty)) <= 1e-12
    )
    return SemanticCheck(
        passed,
        observed=(
            f"inventory={len(state.consumables)}/{state.consumable_slots}, modes={modes}, "
            f"decision={decision.action}, slot_penalty="
            f"{decision.selected.economics.slot_penalty if decision.selected else None}"
        ),
        expected="full consumable inventory forbids persistent BUY but still permits an explicitly modeled immediate BUY_AND_USE that consumes no persistent slot",
        detail=(
            "D4 owns acquisition mode: slot capacity constrains held inventory, not a transaction whose consumable is "
            "used immediately; BUY_AND_USE must therefore remain a distinct legal resource path rather than being "
            "blocked by held-slot pressure"
        ),
    )


def _full_inventory_without_immediate_authority_holds() -> SemanticCheck:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 20
    state.consumable_slots = 2
    state.consumables = [object(), object()]
    candidate = _SyntheticConsumable("Strength", price=1)
    policy = ConsumableAcquisitionPolicy(
        evaluator=_ZeroBuildEvaluator(),
        timing_policy=_ImmediateTimingPolicy(20.0),
    )

    decision = policy.decide(state, candidate)
    passed = decision.action == HOLD and decision.selected is None and not decision.options
    return SemanticCheck(
        passed,
        observed=(
            f"inventory={len(state.consumables)}/{state.consumable_slots}, "
            f"options={tuple(option.mode for option in decision.options)}, decision={decision.action}"
        ),
        expected="full consumable inventory fails closed when the candidate has no explicit immediate-use authority",
        detail=(
            "a full slot must not be bypassed by inventing BUY_AND_USE for an otherwise holdable Tarot/Spectral; "
            "only D4's modeled immediate-use cases may avoid persistent slot occupancy"
        ),
    )


def _d14_buy_and_use_does_not_reprice_consumable_slot() -> SemanticCheck:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 20
    state.consumable_slots = 2
    state.consumables = [object(), object()]
    candidate = _SyntheticConsumable("The Hermit", price=1)
    policy = ConsumableAcquisitionPolicy(
        evaluator=_ZeroBuildEvaluator(),
        timing_policy=_ImmediateTimingPolicy(20.0),
    )
    decision = policy.decide(state, candidate)
    selected = decision.selected
    if selected is None:
        return SemanticCheck(
            False,
            observed=f"decision={decision.action}, selected=None",
            expected="D4 supplies an admitted BUY_AND_USE option for the D14 normalization check",
            detail="fixture did not reach the intended parent resource-boundary assertion",
        )

    executable = SimpleNamespace(decision=decision, candidate=candidate)
    shop_policy = BalatroShopPolicy()
    scale = ShopUtilityScale(shop_policy)
    normalized = scale.consumable_gain(state, executable)
    money_only = scale._money_spend_cost(state, int(selected.economics.price))
    hypothetical_held_slot = scale.resource_valuator.slot_opportunity_cost(
        occupied=len(state.consumables),
        capacity=int(state.consumable_slots),
        last_slot_penalty=scale.last_consumable_slot_penalty,
        resource="consumable",
    ).total

    passed = (
        decision.action == BUY_AND_USE
        and abs(float(normalized.resource_cost) - float(money_only.total)) <= 1e-12
        and float(hypothetical_held_slot) > 0.0
    )
    return SemanticCheck(
        passed,
        observed=(
            f"mode={selected.mode}, parent_resource={normalized.resource_cost:.3f}, "
            f"money_only={money_only.total:.3f}, hypothetical_held_slot={hypothetical_held_slot:.3f}"
        ),
        expected="D14 charges BUY_AND_USE the shared money cost exactly once and no persistent consumable-slot cost",
        detail=(
            "D14 may normalize child economics but must preserve D4 transaction semantics: immediate use releases/avoids "
            "the held slot, whereas persistent BUY alone pays consumable-slot opportunity cost"
        ),
    )


RED_WHITE_PHASE4_CONSUMABLE_CASES = (
    SemanticBenchmarkCase(
        case_id="resource.consumable.full_inventory_immediate_use_allowed",
        category="RESOURCE_COHERENCE",
        description="full inventory permits only explicit immediate BUY_AND_USE",
        evaluate=_full_inventory_blocks_hold_buy_but_allows_explicit_immediate_use,
        source="Phase 4 consumable audit: D4 slot and acquisition-mode boundary",
    ),
    SemanticBenchmarkCase(
        case_id="resource.consumable.full_inventory_unmodeled_holds",
        category="RESOURCE_COHERENCE",
        description="full inventory cannot synthesize immediate-use authority",
        evaluate=_full_inventory_without_immediate_authority_holds,
        source="Phase 4 consumable audit: fail-closed full-slot admission",
    ),
    SemanticBenchmarkCase(
        case_id="resource.consumable.buy_and_use_no_slot_reprice",
        category="RESOURCE_COHERENCE",
        description="D14 preserves BUY_AND_USE no-persistent-slot semantics",
        evaluate=_d14_buy_and_use_does_not_reprice_consumable_slot,
        source="Phase 4 consumable audit: D4-to-D14 resource normalization boundary",
    ),
)
