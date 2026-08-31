from __future__ import annotations

import argparse
from dataclasses import dataclass
from time import perf_counter
from typing import Callable

from games.balatro.actions import END_ROUND, REORDER_HAND, SKIP_BLIND, BalatroAction
from games.balatro.blind_skip_policy import (
    DEFAULT_BLIND_SKIP_THRESHOLD,
    DEFAULT_FALLBACK_TAG_VALUE,
    decide_blind_play_or_skip,
)
from games.balatro.hand_order_policy import HandOrderPolicy
from games.balatro.live.consumable_timing import LiveConsumableTimingPolicy
from games.balatro.live.hand_action_policy import (
    SEARCH_SCHEDULE_FULL,
    HandActionThresholds,
    LiveHandActionDecisionEngine,
    LiveHandActionPolicy,
)
from games.balatro.live.injected.action_dispatcher import LiveMemoryInjectedActionDispatcher
from games.balatro.live.injected.bridge import FirstPartyBalatroBridge, InjectedBridgeError
from games.balatro.live.joker_generation_pool_state import (
    JokerGenerationPoolLiveMemoryObserver,
)
from games.balatro.live.pack import LivePackActionGenerator
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.run_experience_transition import log_successful_live_transition
from games.balatro.live.shop import BalatroShopActionGenerator
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.playbook import default_balatro_playbooks
from games.balatro.shop_arbiter import BuildAwareShopArbiter
from games.balatro.shop_reroll_policy import BuildAwareShopRerollPolicy
from games.balatro.shop_voucher_policy import VoucherAwareBalatroShopPolicy

from .live_memory_achievement_guard import achievement_gate_state
from .live_memory_shop_terms import LiveShopRerollTerms, read_live_shop_reroll_terms


class UnsupportedAutonomousPhase(RuntimeError):
    pass


class AutonomousStepGuardError(RuntimeError):
    pass


class AutonomousBridgeCapabilityError(AutonomousStepGuardError):
    """A planned semantic action is unsupported by the installed bridge build."""


_REQUIRED_BRIDGE_CAPABILITIES = {SKIP_BLIND: "blind_skip", REORDER_HAND: "hand_reorder"}


@dataclass(frozen=True)
class AutonomousStepDecision:
    snapshot: LiveBalatroSnapshot
    state: object
    action: BalatroAction
    source: str
    notes: tuple[str, ...] = ()
    pack_signature: tuple[tuple, ...] | None = None


def _indices(state, action: BalatroAction) -> tuple[int, ...]:
    selected_ids = {id(card) for card in action.cards}
    return tuple(index for index, card in enumerate(getattr(state, "hand", ())) if id(card) in selected_ids)


def _target_index(target) -> int | None:
    value = target.get("area_index") if isinstance(target, dict) else getattr(target, "area_index", None)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _target_label(target) -> str | None:
    if isinstance(target, dict):
        value = target.get("label") or target.get("name") or target.get("center")
    else:
        value = getattr(target, "label", None) or getattr(target, "name", None) or getattr(target, "center", None)
    return str(value) if value is not None else None


def _target_cost(target) -> float | None:
    value = target.get("cost", target.get("price")) if isinstance(target, dict) else getattr(target, "price", getattr(target, "cost", None))
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _pack_choice_signature(choices) -> tuple[tuple, ...]:
    """Return only the stable public identity of visible pack choices.

    ``LivePackChoice.address`` is a transient Lua/process-memory table address. It is
    useful to the low-level postcondition reader, but it is not part of a visible
    choice's semantic identity and may legitimately change between two reads of an
    otherwise unchanged settled pack. The stale-plan guard therefore compares only
    the stable public fields used to identify the same visible option.
    """
    result = []
    for choice in choices:
        data = getattr(choice, "data", {}) or {}
        result.append(
            (
                int(getattr(choice, "area_index", -1)),
                str(getattr(choice, "kind", "")),
                str(getattr(choice, "label", "") or ""),
                str(data.get("center") or data.get("key") or ""),
            )
        )
    return tuple(result)


def _semantic_payload(value):
    if isinstance(value, dict):
        return {key: _semantic_payload(item) for key, item in value.items() if key != "ui"}
    if isinstance(value, list):
        return [_semantic_payload(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_semantic_payload(item) for item in value)
    return value


def _same_snapshot(expected: LiveBalatroSnapshot, current: LiveBalatroSnapshot) -> bool:
    return current.phase == expected.phase and current.state_complete == expected.state_complete and _semantic_payload(current.payload) == _semantic_payload(expected.payload)


def _search_schedule_mode(planner_config, *, max_horizon_override: int | None, max_search_nodes_override: int | None) -> str:
    if max_horizon_override is not None or max_search_nodes_override is not None:
        return SEARCH_SCHEDULE_FULL
    return str(planner_config.get("search_schedule_mode", SEARCH_SCHEDULE_FULL))


class LiveMemoryInjectedSingleStepRunner:
    SHOP_POLICY_ACTIONS = {"BUY_JOKER", "BUY_CONSUMABLE", "BUY_VOUCHER", "END_SHOP"}

    def __init__(self, observer, *, translator=None, bridge=None, dispatcher=None, hand_recommender: Callable[[object, LiveBalatroSnapshot], tuple[BalatroAction, tuple[str, ...]]] | None = None, shop_recommender: Callable[[object, LiveBalatroSnapshot], tuple[BalatroAction, tuple[str, ...]]] | None = None, pack_recommender: Callable[[object, LiveBalatroSnapshot], tuple[BalatroAction, tuple[str, ...], tuple[tuple, ...]]] | None = None, pack_choice_reader: Callable[[], tuple] | None = None, reroll_terms_reader: Callable[[], LiveShopRerollTerms] | None = None, consumable_timing_policy: LiveConsumableTimingPolicy | None = None, blind_skip_threshold: float = DEFAULT_BLIND_SKIP_THRESHOLD, fallback_tag_value: float = DEFAULT_FALLBACK_TAG_VALUE, max_horizon: int | None = None, max_search_nodes: int | None = None, exact_limit: int = 128, child_exact_limit: int = 8) -> None:
        self.observer = observer
        self.translator = translator or DefaultBalatroStateTranslator()
        self.bridge = bridge or FirstPartyBalatroBridge()
        self.dispatcher = dispatcher or LiveMemoryInjectedActionDispatcher(observer, bridge=self.bridge)
        self.blind_skip_threshold = max(0.0, float(blind_skip_threshold))
        self.fallback_tag_value = max(0.0, float(fallback_tag_value))
        self.max_horizon = max_horizon
        self.max_search_nodes = max_search_nodes
        self.exact_limit = int(exact_limit)
        self.child_exact_limit = int(child_exact_limit)
        self.consumable_timing_policy = consumable_timing_policy or LiveConsumableTimingPolicy()
        self.hand_order_policy = HandOrderPolicy()
        self._blocked_consumable_live_ids: set[object] = set()
        self.shop_generator = BalatroShopActionGenerator()
        self.shop_policy = VoucherAwareBalatroShopPolicy()
        self.shop_reroll_policy = BuildAwareShopRerollPolicy(shop_policy=self.shop_policy)
        self.shop_arbiter = BuildAwareShopArbiter(shop_policy=self.shop_policy, reroll_policy=self.shop_reroll_policy)
        self.reroll_terms_reader = reroll_terms_reader or (lambda: read_live_shop_reroll_terms(self.observer))
        self.pack_generator = LivePackActionGenerator()
        self.pack_policy = BalatroPackPolicy()
        self.pack_choice_reader = pack_choice_reader or (lambda: tuple(self.pack_generator.read_choices(self.observer)))
        self.hand_recommender = hand_recommender or self._recommend_hand
        self.shop_recommender = shop_recommender or self._recommend_shop
        self.pack_recommender = pack_recommender or self._recommend_pack
        self.last_observation_seconds = 0.0
        self.last_translation_seconds = 0.0
        self.last_policy_seconds = 0.0

    def quarantine_failed_consumable(self, decision: AutonomousStepDecision) -> bool:
        if str(decision.action.name) != "USE_CONSUMABLE":
            return False
        live_id = getattr(decision.action.target, "live_id", None)
        if live_id is None:
            return False
        self._blocked_consumable_live_ids.add(live_id)
        return True

    def _recommend_consumable_use(self, state) -> tuple[BalatroAction, tuple[str, ...]] | None:
        visible_live_ids = {getattr(consumable, "live_id", None) for consumable in getattr(state, "consumables", ()) if getattr(consumable, "live_id", None) is not None}
        self._blocked_consumable_live_ids.intersection_update(visible_live_ids)
        recommendations = tuple(recommendation for recommendation in self.consumable_timing_policy.recommend_inventory(state) if getattr(recommendation.consumable, "live_id", None) not in self._blocked_consumable_live_ids)
        if not recommendations or not recommendations[0].should_use:
            return None
        selected = recommendations[0]
        action = selected.to_action()
        if action is None:
            raise RuntimeError("B6 consumable timing returned USE without an executable action")
        name = str(getattr(selected.consumable, "name", "unknown"))
        target_indices = selected.target.target_indices if selected.target is not None else ()
        decision_scope = "shop" if getattr(state, "phase", None) == "SHOP" else "hand"
        return action, (f"{decision_scope}_decision=USE_CONSUMABLE", f"consumable={name}", f"target_indices={target_indices}", *tuple(str(note) for note in selected.rationale))

    def _recommend_hand(self, state, snapshot: LiveBalatroSnapshot) -> tuple[BalatroAction, tuple[str, ...]]:
        del snapshot
        playbook = default_balatro_playbooks().for_state(state)
        thresholds = HandActionThresholds.from_mapping(playbook.strategy.get("decision_thresholds", {}).get("hand_action", {}))
        planner_config = playbook.strategy.get("planner", {})
        max_horizon = self.max_horizon if self.max_horizon is not None else int(planner_config.get("max_horizon", 8))
        max_search_nodes = self.max_search_nodes if self.max_search_nodes is not None else int(planner_config.get("max_search_nodes", 5000))
        max_search_seconds = float(planner_config.get("max_search_seconds", 8.0))
        search_schedule_mode = _search_schedule_mode(planner_config, max_horizon_override=self.max_horizon, max_search_nodes_override=self.max_search_nodes)
        engine = LiveHandActionDecisionEngine(policy=LiveHandActionPolicy(thresholds), max_horizon=max_horizon, max_search_nodes=max_search_nodes, exact_limit=self.exact_limit, child_exact_limit=self.child_exact_limit, search_schedule_mode=search_schedule_mode, max_search_seconds=max_search_seconds)
        rank_timings: list[float] = []
        original_rank_plans = engine.rank_plans
        def timed_rank_plans(current_state, *, planner=None):
            started = perf_counter()
            try:
                return original_rank_plans(current_state, planner=planner)
            finally:
                rank_timings.append(perf_counter() - started)
        engine.rank_plans = timed_rank_plans
        decision_started = perf_counter()
        decision = engine.decide(state)
        d1_elapsed = perf_counter() - decision_started
        notes = [f"playbook={playbook.name} v{playbook.version}", f"search_schedule={search_schedule_mode}", f"mode={decision.mode}", f"confidence={decision.confidence:.6f}", f"indices={_indices(state, decision.action)}", f"clear_probability={decision.selected_plan.value.clear_probability:.6f}", f"path_exact={decision.selected_plan.exact}", f"d1_decision_seconds={d1_elapsed:.3f}", f"d1_search_time_budget={max_search_seconds:.3f}s"]
        if decision.selected_pace_ratio is not None:
            notes.append(f"pace_ratio={decision.selected_pace_ratio:.6f}")
        for index, attempt in enumerate(decision.search_attempts):
            elapsed = rank_timings[index] if index < len(rank_timings) else float("nan")
            stage = "confirmation" if attempt.confirmation else "adaptive"
            best_action = attempt.best_action or "NONE"
            best_clear_probability = f"{attempt.best_clear_probability:.6f}" if attempt.best_clear_probability is not None else "NONE"
            best_expected_score = f"{attempt.best_expected_score:.3f}" if attempt.best_expected_score is not None else "NONE"
            best_exact = str(attempt.best_exact) if attempt.best_exact is not None else "NONE"
            notes.append("search[{}]={} h={} samples={} nodes={}/{} budget_exceeded={} elapsed={:.3f}s best_action={} best_clear_probability={} best_expected_score={} best_exact={}".format(index, stage, attempt.horizon, attempt.samples, attempt.nodes_evaluated, attempt.max_nodes, attempt.budget_exceeded, elapsed, best_action, best_clear_probability, best_expected_score, best_exact))
        if len(rank_timings) > len(decision.search_attempts):
            notes.append(f"fallback_search_elapsed={sum(rank_timings[len(decision.search_attempts):]):.3f}s")

        order_decision = self.hand_order_policy.recommend(state, decision.action)
        if order_decision is not None:
            notes.extend(
                (
                    "execution_override=REORDER_HAND",
                    f"hand_order_permutation={order_decision.permutation}",
                    *order_decision.rationale,
                )
            )
            return order_decision.to_action(), tuple(notes)
        return decision.action, tuple(notes)

    def _recommend_shop(self, state, snapshot: LiveBalatroSnapshot) -> tuple[BalatroAction, tuple[str, ...]]:
        del snapshot
        visible_actions = self.shop_generator.generate_actions(state)
        try:
            terms = self.reroll_terms_reader()
            effective_cost = 0 if terms.free_rerolls > 0 else int(terms.cost)
            terms_notes = (f"observed_reroll_cost={int(terms.cost)}", f"free_rerolls={terms.free_rerolls}", f"effective_reroll_spend={effective_cost}")
        except RuntimeError as error:
            effective_cost = None
            terms_notes = (f"reroll_terms_unavailable={error}",)
        decision = self.shop_arbiter.decide(state, visible_actions, reroll_cost=effective_cost)
        shop_decision = "REROLL" if decision.source == "REROLL" else "HOLD_REROLL"
        notes = [f"shop_decision={shop_decision}", *terms_notes, f"arbiter_source={decision.source}", f"policy_score={decision.total:.6f}"]
        if decision.source != "REROLL" and decision.reroll is not None:
            notes.extend(str(note) for note in decision.reroll.rationale)
        notes.extend(str(note) for note in decision.rationale)
        return decision.action, tuple(notes)

    def _recommend_pack(self, state, snapshot: LiveBalatroSnapshot) -> tuple[BalatroAction, tuple[str, ...], tuple[tuple, ...]]:
        del snapshot
        choices = tuple(self.pack_choice_reader())
        actions = self.pack_generator.generate_actions(state, list(choices))
        ranked = self.pack_policy.rank_actions(state, actions)
        if not ranked:
            raise RuntimeError("pack policy produced no scoreable action")
        selected = ranked[0]
        return selected.action, (f"policy_score={selected.total:.6f}", *tuple(str(note) for note in selected.notes)), _pack_choice_signature(choices)

    def decide(self) -> AutonomousStepDecision:
        observed_started = perf_counter()
        snapshot = self.observer.observe()
        self.last_observation_seconds = perf_counter() - observed_started
        if not snapshot.state_complete:
            raise UnsupportedAutonomousPhase(f"{snapshot.phase} is not settled; autonomous execution is blocked")
        translated_started = perf_counter()
        state = self.translator.translate(snapshot)
        self.last_translation_seconds = perf_counter() - translated_started
        self.last_policy_seconds = 0.0
        phase = str(snapshot.phase)
        if phase == "BLIND_SELECT":
            policy_started = perf_counter()
            blind_decision = decide_blind_play_or_skip(snapshot, state=state, threshold=self.blind_skip_threshold, fallback_tag_value=self.fallback_tag_value)
            self.last_policy_seconds = perf_counter() - policy_started
            return AutonomousStepDecision(snapshot, state, BalatroAction(blind_decision.action_name), "D13 blind play-vs-skip policy", blind_decision.notes)
        if phase == "SELECTING_HAND":
            policy_started = perf_counter()
            consumable = self._recommend_consumable_use(state)
            if consumable is not None:
                action, notes = consumable
                self.last_policy_seconds = perf_counter() - policy_started
                return AutonomousStepDecision(snapshot, state, action, "B6 consumable timing policy", notes)
            action, notes = self.hand_recommender(state, snapshot)
            self.last_policy_seconds = perf_counter() - policy_started
            return AutonomousStepDecision(snapshot, state, action, "D1 hand-action policy", notes)
        if phase == "ROUND_EVAL":
            return AutonomousStepDecision(snapshot, state, BalatroAction(END_ROUND), "deterministic round-flow policy", ("cash out completed blind",))
        if phase == "SHOP":
            policy_started = perf_counter()
            consumable = self._recommend_consumable_use(state)
            if consumable is not None:
                action, notes = consumable
                self.last_policy_seconds = perf_counter() - policy_started
                return AutonomousStepDecision(snapshot, state, action, "B6 consumable timing policy", notes)
            action, notes = self.shop_recommender(state, snapshot)
            self.last_policy_seconds = perf_counter() - policy_started
            return AutonomousStepDecision(snapshot, state, action, "shop policy", notes)
        if phase.endswith("_PACK"):
            policy_started = perf_counter()
            action, notes, signature = self.pack_recommender(state, snapshot)
            self.last_policy_seconds = perf_counter() - policy_started
            return AutonomousStepDecision(snapshot, state, action, "pack policy", notes, signature)
        raise UnsupportedAutonomousPhase(f"no first-party autonomous action policy is validated for {phase}")

    def _verify_live_checkpoint(self, decision: AutonomousStepDecision) -> None:
        latest = self.observer.observe()
        if not _same_snapshot(decision.snapshot, latest):
            raise AutonomousStepGuardError("live state changed after autonomous planning; decide again from the new checkpoint")
        if decision.pack_signature is not None:
            current = _pack_choice_signature(tuple(self.pack_choice_reader()))
            if current != decision.pack_signature:
                raise AutonomousStepGuardError("visible booster-pack choices changed after autonomous planning")

    def _achievement_status(self) -> dict[str, str]:
        status = self.bridge.status()
        if status.get("bridge") != "1":
            raise AutonomousStepGuardError("unexpected or missing first-party bridge version")
        state, disabled = achievement_gate_state(status.get("achievement_gate"))
        if disabled is True:
            raise AutonomousStepGuardError("Balatro reports G.F_NO_ACHIEVEMENTS enabled; autonomous execution blocked")
        if disabled is None:
            raise AutonomousStepGuardError(f"Balatro achievement gate is unavailable or unexpected: {state}")
        return status

    def _require_action_capability(self, action: BalatroAction, status: dict[str, str]) -> None:
        capability = _REQUIRED_BRIDGE_CAPABILITIES.get(str(action.name))
        if capability is None or status.get(capability) == "1":
            return
        revision = status.get("bridge_revision", "unknown")
        raise AutonomousBridgeCapabilityError(f"installed first-party bridge does not advertise {action.name} support ({capability}=missing, bridge_revision={revision}); close Balatro and reinstall/update the repository bridge before resuming autonomous play")

    def execute(self, decision: AutonomousStepDecision):
        self._verify_live_checkpoint(decision)
        status = self._achievement_status()
        self._require_action_capability(decision.action, status)
        self._verify_live_checkpoint(decision)
        result = self.dispatcher.dispatch(decision.action, state=decision.state, snapshot=decision.snapshot)
        return result, status


def _action_text(decision: AutonomousStepDecision) -> str:
    action = decision.action
    indices = _indices(decision.state, action)
    if indices:
        return f"{action.name} indices={indices}"
    index = _target_index(action.target)
    label = _target_label(action.target)
    cost = _target_cost(action.target)
    details = []
    if index is not None:
        details.append(f"index={index}")
    if label:
        details.append(f"label={label!r}")
    if cost is not None:
        details.append(f"cost={cost:g}")
    return action.name + (" " + " ".join(details) if details else "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Choose exactly one action from the current public Balatro state.")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--expect-phase")
    parser.add_argument("--run-id")
    parser.add_argument("--max-horizon", type=int)
    parser.add_argument("--max-search-nodes", type=int)
    parser.add_argument("--exact-limit", type=int, default=128)
    parser.add_argument("--child-exact-limit", type=int, default=8)
    parser.add_argument("--blind-skip-threshold", type=float, default=DEFAULT_BLIND_SKIP_THRESHOLD)
    parser.add_argument("--fallback-tag-value", type=float, default=DEFAULT_FALLBACK_TAG_VALUE)
    args = parser.parse_args()
    if args.execute and args.expect_phase is None:
        parser.error("--execute requires --expect-phase")
    if not args.execute and args.expect_phase is not None:
        parser.error("--expect-phase is only valid with --execute")
    if not args.execute and args.run_id is not None:
        parser.error("--run-id is only valid with --execute")
    if args.run_id is not None and not args.run_id.strip():
        parser.error("--run-id cannot be empty")
    for name in ("max_horizon", "max_search_nodes"):
        value = getattr(args, name)
        if value is not None and value < 1:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    if args.exact_limit < 1 or args.child_exact_limit < 1:
        parser.error("exact combination limits must be positive")
    if args.blind_skip_threshold < 0 or args.fallback_tag_value < 0:
        parser.error("blind skip threshold and fallback tag value cannot be negative")
    try:
        with JokerGenerationPoolLiveMemoryObserver() as observer:
            runner = LiveMemoryInjectedSingleStepRunner(observer, blind_skip_threshold=args.blind_skip_threshold, fallback_tag_value=args.fallback_tag_value, max_horizon=args.max_horizon, max_search_nodes=args.max_search_nodes, exact_limit=args.exact_limit, child_exact_limit=args.child_exact_limit)
            decision_started = perf_counter()
            decision = runner.decide()
            decision_elapsed = perf_counter() - decision_started
            print("Live-memory autonomous injected step -> READY")
            print(f"Phase -> {decision.snapshot.phase}")
            print(f"Decision source -> {decision.source}")
            print(f"Decision latency -> {decision_elapsed:.3f}s")
            print(f"Recommended action -> {_action_text(decision)}")
            for note in decision.notes:
                print(f"  {note}")
            if not args.execute:
                print("Execution guard -> PREVIEW ONLY")
                return 0
            assert args.expect_phase is not None
            if decision.snapshot.phase != args.expect_phase:
                print("Execution guard -> BLOCKED")
                print(f"Reason -> expected phase {args.expect_phase}, observed {decision.snapshot.phase}")
                return 0
            try:
                result, status = runner.execute(decision)
            except AutonomousStepGuardError as error:
                print("Execution guard -> BLOCKED")
                print(f"Reason -> {error}")
                return 0
            except InjectedBridgeError as error:
                print("Injected execution -> FAILED")
                print(f"Reason -> {error}")
                return 1
            run_logger = None
            run_log_error: Exception | None = None
            if args.run_id is not None:
                try:
                    run_logger = log_successful_live_transition(decision, result, run_id=args.run_id)
                except Exception as error:
                    run_log_error = error
            print("Execution guard -> PASS")
            print(f"Bridge version -> {status.get('bridge', 'MISSING')}")
            gate_state, _ = achievement_gate_state(status.get("achievement_gate"))
            print(f"G.F_NO_ACHIEVEMENTS state -> {gate_state}")
            print(f"Checkpoint sequence -> {result.after.sequence}")
            print(f"Phase after -> {result.after.phase}")
            if run_log_error is not None:
                print(f"Run logging reason -> {run_log_error}")
            elif run_logger is not None:
                print(f"Run experience log -> {run_logger.path}")
            return 1 if run_log_error is not None else 0
    except UnsupportedAutonomousPhase as error:
        print("Live-memory autonomous injected step -> BLOCKED")
        print(f"Reason -> {error}")
        return 0
    except (InjectedBridgeError, RuntimeError, ValueError) as error:
        print("Live-memory autonomous injected step -> FAIL")
        print(f"Reason -> {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())