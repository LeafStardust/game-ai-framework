from __future__ import annotations

from dataclasses import dataclass, field

from framework.agent.agent import Agent
from framework.decision.pipeline import DecisionPipeline
from framework.decision.policies.greedy import GreedyPolicy

from games.balatro.actions import BalatroAction
from games.balatro.card_selector import CardSelector
from games.balatro.evaluator import BalatroEvaluator
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.synchronizer import BalatroLiveSynchronizer
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.state import BalatroState

from .hand_mouse import ExternalHandMouseExecutor
from .save_observer import SaveBalatroObserver


@dataclass(frozen=True)
class ExternalHandStep:
    """One externally executed hand decision bounded by persisted save checkpoints."""

    action: BalatroAction
    indices: tuple[int, ...]
    before_snapshot: LiveBalatroSnapshot
    before_state: BalatroState
    after_snapshot: LiveBalatroSnapshot
    after_state: BalatroState


@dataclass(frozen=True)
class ExternalHandRunResult:
    """Result of a bounded checkpointed hand-action loop."""

    steps: tuple[ExternalHandStep, ...] = field(default_factory=tuple)
    final_snapshot: LiveBalatroSnapshot | None = None
    final_state: BalatroState | None = None
    stop_reason: str = ""


class ExternalHandController:
    """Choose and execute live hand actions one persisted checkpoint at a time."""

    def __init__(
        self,
        observer: SaveBalatroObserver,
        executor: ExternalHandMouseExecutor,
        *,
        translator=None,
        action_generator=None,
        agent=None,
        synchronizer=None,
    ):
        self.observer = observer
        self.executor = executor
        self.translator = translator or DefaultBalatroStateTranslator()
        self.action_generator = action_generator or CardSelector()
        self.agent = agent or self._default_agent()
        self.synchronizer = synchronizer or BalatroLiveSynchronizer(
            observer,
            poll_interval=0.05,
            timeout=20.0,
        )

    @staticmethod
    def _default_agent() -> Agent:
        return Agent(
            DecisionPipeline(
                BalatroEvaluator(),
                GreedyPolicy(),
            )
        )

    def observe(self) -> tuple[LiveBalatroSnapshot, BalatroState]:
        snapshot = self.observer.observe()
        return snapshot, self.translator.translate(snapshot)

    def recommend(self, state: BalatroState) -> BalatroAction:
        self._require_selecting_hand(state)
        actions = self.action_generator.generate_actions(state)
        if not actions:
            raise RuntimeError("no legal play/discard action is available")
        return self.agent.act(state, actions)

    def execute_one(
        self,
        snapshot: LiveBalatroSnapshot,
        state: BalatroState,
    ) -> ExternalHandStep:
        """Execute one action, then require a new authoritative save checkpoint."""
        self._require_selecting_hand(state)
        action = self.recommend(state)
        expected_indices = self.executor.card_indices(state, action)
        executed_indices = self.executor.dispatch(action, state)
        if executed_indices != expected_indices:
            raise RuntimeError(
                "hand executor index mapping changed during external dispatch"
            )

        persisted_snapshot = self.synchronizer.wait_for_change(
            snapshot,
            require_complete=False,
        )
        persisted_state = self.translator.translate(persisted_snapshot)
        return ExternalHandStep(
            action=action,
            indices=expected_indices,
            before_snapshot=snapshot,
            before_state=state,
            after_snapshot=persisted_snapshot,
            after_state=persisted_state,
        )

    def execute_until_phase_change(
        self,
        *,
        max_actions: int = 8,
    ) -> ExternalHandRunResult:
        """Run checkpointed hand actions until Balatro leaves SELECTING_HAND.

        Every action starts from the save checkpoint produced by the previous action.
        The loop never projects a future hand locally.
        """
        if max_actions < 1:
            raise ValueError("max_actions must be at least 1")

        snapshot, state = self.observe()
        if state.phase != "SELECTING_HAND":
            return ExternalHandRunResult(
                final_snapshot=snapshot,
                final_state=state,
                stop_reason=f"phase:{state.phase}",
            )

        steps: list[ExternalHandStep] = []
        while len(steps) < max_actions and state.phase == "SELECTING_HAND":
            step = self.execute_one(snapshot, state)
            steps.append(step)
            snapshot = step.after_snapshot
            state = step.after_state

        if state.phase != "SELECTING_HAND":
            stop_reason = f"phase:{state.phase}"
        else:
            stop_reason = "max_actions"

        return ExternalHandRunResult(
            steps=tuple(steps),
            final_snapshot=snapshot,
            final_state=state,
            stop_reason=stop_reason,
        )

    @staticmethod
    def _require_selecting_hand(state: BalatroState) -> None:
        if state.phase != "SELECTING_HAND":
            raise ValueError(
                "external hand action requires SELECTING_HAND phase, "
                f"observed {state.phase}"
            )
        if not state.hand:
            raise ValueError("external hand action requires at least one visible hand card")
