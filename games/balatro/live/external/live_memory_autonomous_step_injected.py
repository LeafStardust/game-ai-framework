from __future__ import annotations

import argparse
from dataclasses import dataclass
from time import perf_counter
from typing import Callable

from games.balatro.actions import END_ROUND, SELECT_BLIND, BalatroAction
from games.balatro.live.hand_action_policy import (
    HandActionThresholds,
    LiveHandActionDecisionEngine,
    LiveHandActionPolicy,
)
from games.balatro.live.injected.action_dispatcher import (
    LiveMemoryInjectedActionDispatcher,
)
from games.balatro.live.injected.bridge import (
    FirstPartyBalatroBridge,
    InjectedBridgeError,
)
from games.balatro.live.pack import LivePackActionGenerator
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.shop import BalatroShopActionGenerator
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.playbook import default_balatro_playbooks
from games.balatro.shop_policy import BalatroShopPolicy

from .live_memory_achievement_guard import achievement_gate_state
from .live_memory_observer import LiveMemoryBalatroObserver


class UnsupportedAutonomousPhase(RuntimeError):
    pass


class AutonomousStepGuardError(RuntimeError):
    pass


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
    return tuple(
        index
        for index, card in enumerate(getattr(state, "hand", ()))
        if id(card) in selected_ids
    )


def _target_index(target) -> int | None:
    if isinstance(target, dict):
        value = target.get("area_index")
    else:
        value = getattr(target, "area_index", None)
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
        value = (
            getattr(target, "label", None)
            or getattr(target, "name", None)
            or getattr(target, "center", None)
        )
    return str(value) if value is not None else None


def _target_cost(target) -> float | None:
    if isinstance(target, dict):
        value = target.get("cost", target.get("price"))
    else:
        value = getattr(target, "price", getattr(target, "cost", None))
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _pack_choice_signature(choices) -> tuple[tuple, ...]:
    result = []
    for choice in choices:
        data = getattr(choice, "data", {}) or {}
        result.append(
            (
                int(getattr(choice, "area_index", -1)),
                int(getattr(choice, "address", 0)),
                str(getattr(choice, "kind", "")),
                str(getattr(choice, "label", "") or ""),
                str(data.get("center") or data.get("key") or ""),
            )
        )
    return tuple(result)


def _same_snapshot(
    expected: LiveBalatroSnapshot,
    current: LiveBalatroSnapshot,
) -> bool:
    return (
        current.sequence == expected.sequence
        and current.phase == expected.phase
        and current.state_complete == expected.state_complete
        and current.payload == expected.payload
    )


class LiveMemoryInjectedSingleStepRunner:
    """Choose and execute at most one autonomous Balatro action.

    Observation stays read-only. Execution is exclusively through the first-party
    injected bridge and the unified semantic dispatcher. This class never loops,
    chains actions, traverses hidden draws, or falls back to mouse input.
    """

    SHOP_POLICY_ACTIONS = {
        "BUY_JOKER",
        "BUY_CONSUMABLE",
        "BUY_VOUCHER",
        "END_SHOP",
    }

    def __init__(
        self,
        observer,
        *,
        translator=None,
        bridge=None,
        dispatcher=None,
        hand_recommender: Callable[[object, LiveBalatroSnapshot], tuple[BalatroAction, tuple[str, ...]]] | None = None,
        shop_recommender: Callable[[object, LiveBalatroSnapshot], tuple[BalatroAction, tuple[str, ...]]] | None = None,
        pack_recommender: Callable[[object, LiveBalatroSnapshot], tuple[BalatroAction, tuple[str, ...], tuple[tuple, ...]]] | None = None,
        pack_choice_reader: Callable[[], tuple] | None = None,
        max_horizon: int | None = None,
        max_search_nodes: int | None = None,
        exact_limit: int = 128,
        child_exact_limit: int = 8,
    ) -> None:
        self.observer = observer
        self.translator = translator or DefaultBalatroStateTranslator()
        self.bridge = bridge or FirstPartyBalatroBridge()
        self.dispatcher = dispatcher or LiveMemoryInjectedActionDispatcher(
            observer,
            bridge=self.bridge,
        )
        self.max_horizon = max_horizon
        self.max_search_nodes = max_search_nodes
        self.exact_limit = int(exact_limit)
        self.child_exact_limit = int(child_exact_limit)
        self.shop_generator = BalatroShopActionGenerator()
        self.shop_policy = BalatroShopPolicy()
        self.pack_generator = LivePackActionGenerator()
        self.pack_policy = BalatroPackPolicy()
        self.pack_choice_reader = pack_choice_reader or (
            lambda: tuple(self.pack_generator.read_choices(self.observer))
        )
        self.hand_recommender = hand_recommender or self._recommend_hand
        self.shop_recommender = shop_recommender or self._recommend_shop
        self.pack_recommender = pack_recommender or self._recommend_pack

    def _recommend_hand(
        self,
        state,
        snapshot: LiveBalatroSnapshot,
    ) -> tuple[BalatroAction, tuple[str, ...]]:
        del snapshot
        playbook = default_balatro_playbooks().for_state(state)
        thresholds = HandActionThresholds.from_mapping(
            playbook.strategy.get("decision_thresholds", {}).get("hand_action", {})
        )
        planner_config = playbook.strategy.get("planner", {})
        max_horizon = (
            self.max_horizon
            if self.max_horizon is not None
            else int(planner_config.get("max_horizon", 8))
        )
        max_search_nodes = (
            self.max_search_nodes
            if self.max_search_nodes is not None
            else int(planner_config.get("max_search_nodes", 5000))
        )
        engine = LiveHandActionDecisionEngine(
            policy=LiveHandActionPolicy(thresholds),
            max_horizon=max_horizon,
            max_search_nodes=max_search_nodes,
            exact_limit=self.exact_limit,
            child_exact_limit=self.child_exact_limit,
        )

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

        notes = [
            f"playbook={playbook.name} v{playbook.version}",
            f"mode={decision.mode}",
            f"confidence={decision.confidence:.6f}",
            f"indices={_indices(state, decision.action)}",
            (
                "clear_probability="
                f"{decision.selected_plan.value.clear_probability:.6f}"
            ),
            f"path_exact={decision.selected_plan.exact}",
            f"d1_decision_seconds={d1_elapsed:.3f}",
        ]
        if decision.selected_pace_ratio is not None:
            notes.append(f"pace_ratio={decision.selected_pace_ratio:.6f}")

        for index, attempt in enumerate(decision.search_attempts):
            elapsed = rank_timings[index] if index < len(rank_timings) else float("nan")
            stage = "confirmation" if attempt.confirmation else "adaptive"
            notes.append(
                "search[{}]={} h={} samples={} nodes={}/{} budget_exceeded={} elapsed={:.3f}s".format(
                    index,
                    stage,
                    attempt.horizon,
                    attempt.samples,
                    attempt.nodes_evaluated,
                    attempt.max_nodes,
                    attempt.budget_exceeded,
                    elapsed,
                )
            )

        if len(rank_timings) > len(decision.search_attempts):
            fallback_elapsed = sum(rank_timings[len(decision.search_attempts):])
            notes.append(f"fallback_search_elapsed={fallback_elapsed:.3f}s")

        return decision.action, tuple(notes)

    def _recommend_shop(
        self,
        state,
        snapshot: LiveBalatroSnapshot,
    ) -> tuple[BalatroAction, tuple[str, ...]]:
        del snapshot
        actions = [
            action
            for action in self.shop_generator.generate_actions(state)
            if action.name in self.SHOP_POLICY_ACTIONS
        ]
        ranked = self.shop_policy.rank_actions(state, actions)
        if not ranked:
            raise RuntimeError("shop policy produced no scoreable action")
        selected = ranked[0]
        notes = [f"policy_score={selected.total:.6f}"]
        notes.extend(str(note) for note in selected.notes)
        return selected.action, tuple(notes)

    def _recommend_pack(
        self,
        state,
        snapshot: LiveBalatroSnapshot,
    ) -> tuple[BalatroAction, tuple[str, ...], tuple[tuple, ...]]:
        del snapshot
        choices = tuple(self.pack_choice_reader())
        actions = self.pack_generator.generate_actions(state, list(choices))
        ranked = self.pack_policy.rank_actions(state, actions)
        if not ranked:
            raise RuntimeError("pack policy produced no scoreable action")
        selected = ranked[0]
        notes = [f"policy_score={selected.total:.6f}"]
        notes.extend(str(note) for note in selected.notes)
        return selected.action, tuple(notes), _pack_choice_signature(choices)

    def decide(self) -> AutonomousStepDecision:
        snapshot = self.observer.observe()
        if not snapshot.state_complete:
            raise UnsupportedAutonomousPhase(
                f"{snapshot.phase} is not settled; autonomous execution is blocked"
            )
        state = self.translator.translate(snapshot)
        phase = str(snapshot.phase)

        if phase == "BLIND_SELECT":
            return AutonomousStepDecision(
                snapshot,
                state,
                BalatroAction(SELECT_BLIND),
                "deterministic blind-selection policy",
                ("fight current blind; skip policy not yet enabled",),
            )

        if phase == "SELECTING_HAND":
            action, notes = self.hand_recommender(state, snapshot)
            return AutonomousStepDecision(
                snapshot,
                state,
                action,
                "D1 hand-action policy",
                notes,
            )

        if phase == "ROUND_EVAL":
            return AutonomousStepDecision(
                snapshot,
                state,
                BalatroAction(END_ROUND),
                "deterministic round-flow policy",
                ("cash out completed blind",),
            )

        if phase == "SHOP":
            action, notes = self.shop_recommender(state, snapshot)
            return AutonomousStepDecision(
                snapshot,
                state,
                action,
                "shop policy",
                notes,
            )

        if phase.endswith("_PACK"):
            action, notes, signature = self.pack_recommender(state, snapshot)
            return AutonomousStepDecision(
                snapshot,
                state,
                action,
                "pack policy",
                notes,
                signature,
            )

        raise UnsupportedAutonomousPhase(
            f"no first-party autonomous action policy is validated for {phase}"
        )

    def _verify_live_checkpoint(self, decision: AutonomousStepDecision) -> None:
        latest = self.observer.observe()
        if not _same_snapshot(decision.snapshot, latest):
            raise AutonomousStepGuardError(
                "live state changed after autonomous planning; decide again from the new checkpoint"
            )

        if decision.pack_signature is not None:
            current = _pack_choice_signature(tuple(self.pack_choice_reader()))
            if current != decision.pack_signature:
                raise AutonomousStepGuardError(
                    "visible booster-pack choices changed after autonomous planning"
                )

    def _achievement_status(self) -> dict[str, str]:
        status = self.bridge.status()
        if status.get("bridge") != "1":
            raise AutonomousStepGuardError(
                "unexpected or missing first-party bridge version"
            )
        state, disabled = achievement_gate_state(status.get("achievement_gate"))
        if disabled is True:
            raise AutonomousStepGuardError(
                "Balatro reports G.F_NO_ACHIEVEMENTS enabled; autonomous execution blocked"
            )
        if disabled is None:
            raise AutonomousStepGuardError(
                f"Balatro achievement gate is unavailable or unexpected: {state}"
            )
        return status

    def execute(self, decision: AutonomousStepDecision):
        self._verify_live_checkpoint(decision)
        status = self._achievement_status()
        # STATUS itself is read-only but can take time. Recheck the exact public
        # checkpoint afterwards so the gameplay action is never submitted from a
        # stale recommendation.
        self._verify_live_checkpoint(decision)
        result = self.dispatcher.dispatch(
            decision.action,
            state=decision.state,
            snapshot=decision.snapshot,
        )
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
    parser = argparse.ArgumentParser(
        description=(
            "Choose exactly one action from the current public Balatro state. "
            "Preview is read-only. --execute sends exactly one gameplay action "
            "through the first-party injected bridge, then stops after its settled "
            "semantic checkpoint."
        )
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--expect-phase",
        help="required with --execute; prevents acting if Balatro is in another phase",
    )
    parser.add_argument("--max-horizon", type=int)
    parser.add_argument("--max-search-nodes", type=int)
    parser.add_argument("--exact-limit", type=int, default=128)
    parser.add_argument("--child-exact-limit", type=int, default=8)
    args = parser.parse_args()

    if args.execute and args.expect_phase is None:
        parser.error("--execute requires --expect-phase")
    if not args.execute and args.expect_phase is not None:
        parser.error("--expect-phase is only valid with --execute")
    for name in ("max_horizon", "max_search_nodes"):
        value = getattr(args, name)
        if value is not None and value < 1:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    if args.exact_limit < 1 or args.child_exact_limit < 1:
        parser.error("exact combination limits must be positive")

    try:
        with LiveMemoryBalatroObserver() as observer:
            runner = LiveMemoryInjectedSingleStepRunner(
                observer,
                max_horizon=args.max_horizon,
                max_search_nodes=args.max_search_nodes,
                exact_limit=args.exact_limit,
                child_exact_limit=args.child_exact_limit,
            )
            decision_started = perf_counter()
            decision = runner.decide()
            decision_elapsed = perf_counter() - decision_started

            print("Live-memory autonomous injected step -> READY")
            print("Observation source -> live Balatro process memory")
            print("Execution backend -> game-ai-framework injected Lua bridge")
            print("Runtime loader -> none (fused LÖVE archive)")
            print("Lovely required -> False")
            print("Steamodded required -> False")
            print("BalatroBot required -> False")
            print("Mouse fallback -> False")
            print(f"Phase -> {decision.snapshot.phase}")
            print(f"Decision source -> {decision.source}")
            print(f"Decision latency -> {decision_elapsed:.3f}s")
            print(f"Recommended action -> {_action_text(decision)}")
            for note in decision.notes:
                print(f"  {note}")
            print("Observation process writes -> False")
            print("Hidden RNG/deck traversal -> False")
            print("Follow-up action chaining -> False")

            if not args.execute:
                print("Execution guard -> PREVIEW ONLY")
                print("Achievement status command sent -> False")
                print("Injected gameplay command sent -> False")
                print("Mouse input sent -> False")
                return 0

            assert args.expect_phase is not None
            if decision.snapshot.phase != args.expect_phase:
                print("Execution guard -> BLOCKED")
                print(
                    f"Reason -> expected phase {args.expect_phase}, "
                    f"observed {decision.snapshot.phase}"
                )
                print("Achievement status command sent -> False")
                print("Injected gameplay command sent -> False")
                print("Mouse input sent -> False")
                return 0

            print(
                "WARNING -> --execute is armed: exactly one real in-process "
                "Balatro gameplay action may now be invoked"
            )
            print(f"Execution scope -> exactly one {_action_text(decision)} action")
            print("Mouse input sent -> False")

            try:
                result, status = runner.execute(decision)
            except AutonomousStepGuardError as error:
                print("Execution guard -> BLOCKED")
                print(f"Reason -> {error}")
                print("Injected gameplay command sent -> False")
                return 0
            except InjectedBridgeError as error:
                print("Injected execution -> FAILED")
                print(f"Reason -> {error}")
                print("Follow-up action executed -> False")
                return 1
            except RuntimeError as error:
                print("Injected execution -> FAILED")
                print(f"Reason -> {error}")
                print("Follow-up action executed -> False")
                return 1

            print("Execution guard -> PASS")
            print("Achievement status command sent -> True")
            print(f"Bridge version -> {status.get('bridge', 'MISSING')}")
            gate_state, _ = achievement_gate_state(status.get("achievement_gate"))
            print(f"G.F_NO_ACHIEVEMENTS state -> {gate_state}")
            print("Steam achievement gate -> NOT DISABLED")
            print("Injected gameplay command sent -> True")
            print(f"Checkpoint sequence -> {result.after.sequence}")
            print(f"Phase after -> {result.after.phase}")
            print("Follow-up action executed -> False")
            return 0
    except UnsupportedAutonomousPhase as error:
        print("Live-memory autonomous injected step -> BLOCKED")
        print(f"Reason -> {error}")
        print("Injected gameplay command sent -> False")
        print("Mouse input sent -> False")
        return 0
    except (InjectedBridgeError, RuntimeError, ValueError) as error:
        print("Live-memory autonomous injected step -> FAIL")
        print(f"Reason -> {error}")
        print("Injected gameplay command sent -> False")
        print("Mouse input sent -> False")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
