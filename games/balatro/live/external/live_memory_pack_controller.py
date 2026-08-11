from __future__ import annotations

from dataclasses import dataclass

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.live.pack import LivePackActionGenerator, LivePackChoice
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore
from games.balatro.state import BalatroState

from .live_memory_action_dispatcher import LiveExternalActionResult, LiveMemoryActionDispatcher
from .live_memory_observer import LiveMemoryBalatroObserver


@dataclass(frozen=True)
class LiveMemoryPackView:
    snapshot: LiveBalatroSnapshot
    state: BalatroState
    choices: tuple[LivePackChoice, ...]


class LiveMemoryPackController:
    """Observe, rank, and execute public booster-pack choices from live memory."""

    def __init__(
        self,
        observer: LiveMemoryBalatroObserver | None = None,
        *,
        translator=None,
        action_generator=None,
        policy=None,
        dispatcher=None,
    ) -> None:
        self.observer = observer or LiveMemoryBalatroObserver()
        self.translator = translator or DefaultBalatroStateTranslator()
        self.action_generator = action_generator or LivePackActionGenerator()
        self.policy = policy or BalatroPackPolicy()
        self.dispatcher = dispatcher or LiveMemoryActionDispatcher(self.observer)
        self._owns_observer = observer is None
        self._owns_dispatcher = dispatcher is None

    def observe(self) -> LiveMemoryPackView:
        snapshot = self.observer.observe()
        if not snapshot.phase.endswith("_PACK"):
            raise ValueError(
                f"live-memory pack controller requires *_PACK phase, observed {snapshot.phase}"
            )
        state = self.translator.translate(snapshot)
        choices = tuple(self.action_generator.read_choices(self.observer))
        return LiveMemoryPackView(snapshot, state, choices)

    def available_actions(self, view: LiveMemoryPackView | None = None) -> list[BalatroAction]:
        view = view or self.observe()
        return self.action_generator.generate_actions(view.state, list(view.choices))

    def rank_actions(self, view: LiveMemoryPackView | None = None) -> list[PackActionScore]:
        view = view or self.observe()
        return self.policy.rank_actions(view.state, self.available_actions(view))

    def recommended_action(self, view: LiveMemoryPackView | None = None) -> BalatroAction:
        ranked = self.rank_actions(view)
        if not ranked:
            raise RuntimeError("no live booster-pack action is available")
        return ranked[0].action

    def execute(
        self,
        action: BalatroAction,
        view: LiveMemoryPackView | None = None,
    ) -> LiveExternalActionResult:
        view = view or self.observe()
        if not any(self._same_action(candidate, action) for candidate in self.available_actions(view)):
            raise ValueError(f"pack action {action.name!r} is not currently available")
        return self.dispatcher.dispatch(action, state=view.state, snapshot=view.snapshot)

    def execute_recommended(self, view: LiveMemoryPackView | None = None) -> LiveExternalActionResult:
        view = view or self.observe()
        return self.execute(self.recommended_action(view), view)

    @staticmethod
    def _same_action(left: BalatroAction, right: BalatroAction) -> bool:
        if left.name != right.name:
            return False
        if left.name == SKIP_BOOSTER:
            return True
        if left.name != SELECT_PACK_CARD:
            return left.target == right.target
        left_index = getattr(left.target, "area_index", None)
        right_index = getattr(right.target, "area_index", None)
        return (
            left_index is not None
            and right_index is not None
            and int(left_index) == int(right_index)
        )

    def close(self) -> None:
        if self._owns_dispatcher:
            self.dispatcher.close()
        if self._owns_observer:
            self.observer.close()

    def __enter__(self) -> "LiveMemoryPackController":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
