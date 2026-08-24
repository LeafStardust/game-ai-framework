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
from games.balatro.live.consumable_timing import LiveConsumableTimingPolicy
from games.balatro.live.hand_action_policy import (
    SEARCH_SCHEDULE_FULL,
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
from games.balatro.live.run_experience_transition import (
    log_successful_live_transition,
)
from games.balatro.live.shop import BalatroShopActionGenerator
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.playbook import default_balatro_playbooks
from games.balatro.shop_arbiter import BuildAwareShopArbiter
from games.balatro.shop_reroll_policy import BuildAwareShopRerollPolicy
from games.balatro.shop_voucher_policy import VoucherAwareBalatroShopPolicy

from .live_memory_achievement_guard import achievement_gate_state
from .live_memory_observer import LiveMemoryBalatroObserver
from .live_memory_shop_terms import (
    LiveShopRerollTerms,
    read_live_shop_reroll_terms,
)


class UnsupportedAutonomousPhase(RuntimeError):
    pass


class AutonomousStepGuardError(RuntimeError):
    pass


class AutonomousBridgeCapabilityError(AutonomousStepGuardError):
    """A planned semantic action is unsupported by the installed bridge build."""


_REQUIRED_BRIDGE_CAPABILITIES = {
    SKIP_BLIND: "blind_skip",
    REORDER_HAND: "hand_reorder",
}


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


def _semantic_payload(value):
    """Remove presentation-only UI geometry from a live public-state payload.

    The injected bridge acts on Balatro's internal card objects and callbacks, not
    screen coordinates. Card/item ``ui`` geometry can drift from animation or
    hover while every gameplay-relevant field remains unchanged, so it must not
    invalidate a several-second D1 recommendation. All non-UI public fields stay
    exact and pack identity keeps its dedicated address/signature guard.
    """
    if isinstance(value, dict):
        return {
            key: _semantic_payload(item)
            for key, item in value.items()
            if key != "ui"
        }
    if isinstance(value, list):
        return [_semantic_payload(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_semantic_payload(item) for item in value)
    return value


def _same_snapshot(
    expected: LiveBalatroSnapshot,
    current: LiveBalatroSnapshot,
) -> bool:
    # Sequence can advance from presentation-only geometry because the observer's
    # general-purpose fingerprint intentionally includes its full payload. For
    # injected execution, stale-state equality is gameplay-semantic instead.
    return (
        current.phase == expected.phase
        and current.state_complete == expected.state_complete
        and _semantic_payload(current.payload) == _semantic_payload(expected.payload)
    )


def _search_schedule_mode(
    planner_config,
    *,
    max_horizon_override: int | None,
    max_search_nodes_override: int | None,
) -> str:
    # Any explicit search-depth/budget override is diagnostic intent. Preserve the
    # complete adaptive ladder in that case; only ordinary playbook-driven autonomy
    # may use a sparse latency profile.
    if max_horizon_override is not None or max_search_nodes_override is not None:
        return SEARCH_SCHEDULE_FULL
    return str(planner_config.get("search_schedule_mode", SEARCH_SCHEDULE_FULL))


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
        reroll_terms_reader: Callable[[], LiveShopRerollTerms] | None = None,
        consumable_timing_policy: LiveConsumableTimingPolicy | None = None,
        blind_skip_threshold: float = DEFAULT_BLIND_SKIP_THRESHOLD,
        fallback_tag_value: float = DEFAULT_FALLBACK_TAG_VALUE,
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
        self.blind_skip_threshold = max(0.0, float(blind_skip_threshold))
        self.fallback_tag_value = max(0.0, float(fallback_tag_value))
        self.max_horizon = max_horizon
        self.max_search_nodes = max_search_nodes
        self.exact_limit = int(exact_limit)
        self.child_exact_limit = int(child_exact_limit)
        self.consumable_timing_policy = (
            consumable_timing_policy or LiveConsumableTimingPolicy()
        )
        self._blocked_consumable_live_ids: set[object] = set()
        self.shop_generator = BalatroShopActionGenerator()
        self.shop_policy = VoucherAwareBalatroShopPolicy()
        self.shop_reroll_policy = BuildAwareShopRerollPolicy(
            shop_policy=self.shop_policy,
        )
        self.shop_arbiter = BuildAwareShopArbiter(
            shop_policy=self.shop_policy,
            reroll_policy=self.shop_reroll_policy,
        )
        self.reroll_terms_reader = reroll_terms_reader or (
            lambda: read_live_shop_reroll_terms(self.observer)
        )
        self.pack_generator = LivePackActionGenerator()
        self.pack_policy = BalatroPackPolicy()
        self.pack_choice_reader = pack_choice_reader or (
            lambda: tuple(self.pack_generator.read_choices(self.observer))
        )
        self.hand_recommender = hand_recommender or self._recommend_hand
        self.shop_recommender = shop_recommender or self._recommend_shop
        self.pack_recommender = pack_recommender or self._recommend_pack
        self.last_observation_seconds = 0.0
        self.last_translation_seconds = 0.0
        self.last_policy_seconds = 0.0

    def quarantine_failed_consumable(self, decision: AutonomousStepDecision) -> bool:
        """Suppress one held consumable after an accepted use never settles.

        The live id is process-local and unique to that concrete held card. Quarantine
        prevents an autonomous loop from retrying the same native no-op forever; a
        fresh consumable instance remains eligible normally.
        """
        if str(decision.action.name) != "USE_CONSUMABLE":
            return False
        live_id = getattr(decision.action.target, "live_id", None)
        if live_id is None:
            return False
        self._blocked_consumable_live_ids.add(live_id)
        return True

    def _recommend_consumable_use(
        self,
        state,
    ) -> tuple[BalatroAction, tuple[str, ...]] | None:
        visible_live_ids = {
            getattr(consumable, "live_id", None)
            for consumable in getattr(state, "consumables", ())
            if getattr(consumable, "live_id", None) is not None
        }
        self._blocked_consumable_live_ids.intersection_update(visible_live_ids)
        recommendations = tuple(
            recommendation
            for recommendation in self.consumable_timing_policy.recommend_inventory(state)
            if getattr(recommendation.consumable, "live_id", None)
            not in self._blocked_consumable_live_ids
        )
        if not recommendations:
            return None

        selected = recommendations[0]
        if not selected.should_use:
            return None

        action = selected.to_action()
        if action is None:
            raise RuntimeError(
                "B6 consumable timing returned USE without an executable action"
            )

        name = str(getattr(selected.consumable, "name", "unknown"))
        target_indices = (
            selected.target.target_indices
            if selected.target is not None
            else ()
        )
        decision_scope = (
            "shop" if getattr(state, "phase", None) == "SHOP" else "hand"
        )
        notes = (
            f"{decision_scope}_decision=USE_CONSUMABLE",
            f"consumable={name}",
            f"target_indices={target_indices}",
            *tuple(str(note) for note in selected.rationale),
        )
        return action, notes

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
        max_search_seconds = float(planner_config.get("max_search_seconds", 8.0))
        search_schedule_mode = _search_schedule_mode(
            planner_config,
            max_horizon_override=self.max_horizon,
            max_search_nodes_override=self.max_search_nodes,
        )
        engine = LiveHandActionDecisionEngine(
            policy=LiveHandActionPolicy(thresholds),
            max_horizon=max_horizon,
            max_search_nodes=max_search_nodes,
            exact_limit=self.exact_limit,
            child_exact_limit=self.child_exact_limit,
            search_schedule_mode=search_schedule_mode,
            max_search_seconds=max_search_seconds,
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
            f"search_schedule={search_schedule_mode}",
            f"mode={decision.mode}",
            f"confidence={decision.confidence:.6f}",
            f"indices={_indices(state, decision.action)}",
            (
                "clear_probability="
                f"{decision.selected_plan.value.clear_probability:.6f}"
            ),
            f"path_exact={decision.selected_plan.exact}",
            f"d1_decision_seconds={d1_elapsed:.3f}",
            f"d1_search_time_budget={max_search_seconds:.3f}s",
        ]
        if decision.selected_pace_ratio is not None:
            notes.append(f"pace_ratio={decision.selected_pace_ratio:.6f}")

        for index, attempt in enumerate(decision.search_attempts):
            elapsed = rank_timings[index] if index < len(rank_timings) else float("nan")
            stage = "confirmation" if attempt.confirmation else "adaptive"
            best_action = attempt.best_action or "NONE"
            best_clear_probability = (
                f"{attempt.best_clear_probability:.6f}"
                if attempt.best_clear_probability is not None
                else "NONE"
            )
            best_expected_score = (
                f"{attempt.best_expected_score:.3f}"
                if attempt.best_expected_score is not None
                else "NONE"
            )
            best_exact = (
                str(attempt.best_exact) if attempt.best_exact is not None else "NONE"
            )
            notes.append(
                "search[{}]={} h={} samples={} nodes={}/{} budget_exceeded={} "
                "elapsed={:.3f}s best_action={} best_clear_probability={} "
                "best_expected_score={} best_exact={}".format(
                    index,
                    stage,
                    attempt.horizon,
                    attempt.samples,
                    attempt.nodes_evaluated,
                    attempt.max_nodes,
                    attempt.budget_exceeded,
                    elapsed,
                    best_action,
                    best_clear_probability,
                    best_expected_score,
                    best_exact,
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
        visible_actions = self.shop_generator.generate_actions(state)
        recommendation = self.shop_arbiter.decide(state, visible_actions)
        notes = [
            f"shop_decision={recommendation.action.name}",
            f"shop_source={recommendation.source}",
            f"shop_total={recommendation.total:.6f}",
        ]
        notes.extend(str(note) for note in recommendation.notes)
        return recommendation.action, tuple(notes)

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
        observed_started = perf_counter()
        snapshot = self.observer.observe()
        self.last_observation_seconds = perf_counter() - observed_started
        if not snapshot.state_complete:
            raise UnsupportedAutonomousPhase(
                f"{snapshot.phase} is not settled; autonomous execution is blocked"
            )

        translated_started = perf_counter()
        state = self.translator.translate(snapshot)
        self.last_translation_seconds = perf_counter() - translated_started
        self.last_policy_seconds = 0.0
        phase = str(snapshot.phase)

        if phase == "BLIND_SELECT":
            policy_started = perf_counter()
            blind_decision = decide_blind_play_or_skip(
                snapshot,
                state=state,
                threshold=self.blind_skip_threshold,
                fallback_tag_value=self.fallback_tag_value,
            )
            self.last_policy_seconds = perf_counter() - policy_started
            return AutonomousStepDecision(
                snapshot,
                state,
                BalatroAction(blind_decision.action_name),
                "D13 blind play-vs-skip policy",
                blind_decision.notes,
            )

        if phase == "SELECTING_HAND":
            policy_started = perf_counter()
            consumable = self._recommend_consumable_use(state)
            if consumable is not None:
                action, notes = consumable
                self.last_policy_seconds = perf_counter() - policy_started
                return AutonomousStepDecision(
                    snapshot,
                    state,
                    action,
                    "B6 consumable timing policy",
                    notes,
                )

            action, notes = self.hand_recommender(state, snapshot)
            self.last_policy_seconds = perf_counter() - policy_started
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
            policy_started = perf_counter()
            consumable = self._recommend_consumable_use(state)
            if consumable is not None:
                action, notes = consumable
                self.last_policy_seconds = perf_counter() - policy_started
                return AutonomousStepDecision(
                    snapshot,
                    state,
                    action,
                    "B6 consumable timing policy",
                    notes,
                )

            action, notes = self.shop_recommender(state, snapshot)
            self.last_policy_seconds = perf_counter() - policy_started
            return AutonomousStepDecision(
                snapshot,
                state,
                action,
                "shop policy",
                notes,
            )

        if phase.endswith("_PACK"):
            policy_started = perf_counter()
            action, notes, signature = self.pack_recommender(state, snapshot)
            self.last_policy_seconds = perf_counter() - policy_started
            return AutonomousStepDecision(
                snapshot,
                state,
                action,
                "pack policy",
                notes,
                signature,
            )

        raise UnsupportedAutonomousPhase(
            f"{phase} has no autonomous action policy"
        )

    def execute(self, decision: AutonomousStepDecision):
        current = self.observer.observe()
        if not current.state_complete or not _same_snapshot(decision.snapshot, current):
            raise AutonomousStepGuardError(
                "live state changed after recommendation; refusing stale execution"
            )

        capability = _REQUIRED_BRIDGE_CAPABILITIES.get(decision.action.name)
        if capability is not None and not self.bridge.supports(capability):
            raise AutonomousBridgeCapabilityError(
                f"bridge does not advertise required capability {capability!r} "
                f"for action {decision.action.name}"
            )

        result = self.dispatcher.dispatch(
            decision.action,
            decision.snapshot,
            pack_signature=decision.pack_signature,
        )
        return result, self.observer.observe()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-horizon", type=int, default=None)
    parser.add_argument("--max-search-nodes", type=int, default=None)
    args = parser.parse_args(argv)
    with LiveMemoryBalatroObserver() as observer:
        runner = LiveMemoryInjectedSingleStepRunner(
            observer,
            max_horizon=args.max_horizon,
            max_search_nodes=args.max_search_nodes,
        )
        decision = runner.decide()
        result, _status = runner.execute(decision)
        log_successful_live_transition(decision, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
