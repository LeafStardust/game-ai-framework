from __future__ import annotations

from dataclasses import dataclass

from games.balatro.actions import (
    BUY_BOOSTER,
    BUY_CONSUMABLE,
    BUY_JOKER,
    BUY_VOUCHER,
    END_SHOP,
    BalatroAction,
)
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.shop import BalatroShopActionGenerator
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.shop_policy import BalatroShopPolicy, ShopActionScore
from games.balatro.state import BalatroState

from .live_memory_action_dispatcher import (
    LiveExternalActionResult,
    LiveMemoryActionDispatcher,
)
from .live_memory_observer import LiveMemoryBalatroObserver


@dataclass(frozen=True)
class LiveMemoryShopView:
    snapshot: LiveBalatroSnapshot
    state: BalatroState


class LiveMemoryShopController:
    """Run the existing SHOP planner directly against live process-memory state.

    Unlike ``ExternalShopController``, this controller has no save-checkpoint
    buffering and no calibrated mouse layout. Every action is executed immediately
    through ``LiveMemoryActionDispatcher`` and the resulting live state is observed
    again before another decision is made.
    """

    POLICY_ACTIONS = {
        BUY_JOKER,
        BUY_CONSUMABLE,
        BUY_VOUCHER,
        END_SHOP,
    }

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
        self.action_generator = action_generator or BalatroShopActionGenerator()
        self.policy = policy or BalatroShopPolicy()
        self.dispatcher = dispatcher or LiveMemoryActionDispatcher(self.observer)
        self._owns_observer = observer is None
        self._owns_dispatcher = dispatcher is None

    def observe(self) -> LiveMemoryShopView:
        snapshot = self.observer.observe()
        state = self.translator.translate(snapshot)
        if state.phase != "SHOP":
            raise ValueError(
                f"live-memory shop controller requires SHOP phase, observed {state.phase}"
            )
        return LiveMemoryShopView(snapshot, state)

    def available_actions(self, view: LiveMemoryShopView | None = None) -> list[BalatroAction]:
        view = view or self.observe()
        if view.state.phase != "SHOP":
            return []
        return self.action_generator.generate_actions(view.state)

    def policy_actions(self, view: LiveMemoryShopView | None = None) -> list[BalatroAction]:
        return [
            action
            for action in self.available_actions(view)
            if action.name in self.POLICY_ACTIONS
        ]

    def rank_actions(self, view: LiveMemoryShopView | None = None) -> list[ShopActionScore]:
        view = view or self.observe()
        return self.policy.rank_actions(view.state, self.policy_actions(view))

    def recommended_action(self, view: LiveMemoryShopView | None = None) -> BalatroAction:
        ranked = self.rank_actions(view)
        if not ranked:
            raise RuntimeError("no policy-scoreable live SHOP action is available")
        return ranked[0].action

    def execute(
        self,
        action: BalatroAction,
        view: LiveMemoryShopView | None = None,
    ) -> LiveExternalActionResult:
        view = view or self.observe()
        allowed = self.available_actions(view)
        if not any(self._same_action(candidate, action) for candidate in allowed):
            raise ValueError(f"action {action.name!r} is not currently available in SHOP")
        return self.dispatcher.dispatch(
            action,
            state=view.state,
            snapshot=view.snapshot,
        )

    def execute_recommended_purchase(
        self,
        view: LiveMemoryShopView | None = None,
    ) -> LiveExternalActionResult:
        view = view or self.observe()
        action = self.recommended_action(view)
        if action.name == END_SHOP:
            raise RuntimeError(
                "shop policy recommends END_SHOP; no purchase should be executed"
            )
        return self.execute(action, view)

    def leave_shop(self, view: LiveMemoryShopView | None = None) -> LiveExternalActionResult:
        view = view or self.observe()
        action = next(
            (
                candidate
                for candidate in self.available_actions(view)
                if candidate.name == END_SHOP
            ),
            None,
        )
        if action is None:
            raise RuntimeError("END_SHOP is not available")
        return self.execute(action, view)

    def open_booster(
        self,
        index: int,
        view: LiveMemoryShopView | None = None,
    ) -> LiveExternalActionResult:
        """Explicitly open one available booster without changing shop-policy scoring."""
        view = view or self.observe()
        action = next(
            (
                candidate
                for candidate in self.available_actions(view)
                if candidate.name == BUY_BOOSTER
                and int(getattr(candidate.target, "area_index", -1)) == int(index)
            ),
            None,
        )
        if action is None:
            raise ValueError(f"no affordable booster exists at area_index={index}")
        return self.execute(action, view)

    @staticmethod
    def _same_action(left: BalatroAction, right: BalatroAction) -> bool:
        if left.name != right.name:
            return False
        if left.target is right.target:
            return True
        left_index = getattr(left.target, "area_index", None)
        right_index = getattr(right.target, "area_index", None)
        if left_index is not None and right_index is not None:
            return int(left_index) == int(right_index)
        return left.target == right.target

    def close(self) -> None:
        if self._owns_dispatcher:
            self.dispatcher.close()
        if self._owns_observer:
            self.observer.close()

    def __enter__(self) -> "LiveMemoryShopController":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
