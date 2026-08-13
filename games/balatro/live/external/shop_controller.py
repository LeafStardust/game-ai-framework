from __future__ import annotations

from dataclasses import dataclass

from games.balatro.actions import (
    BUY_CONSUMABLE,
    BUY_JOKER,
    END_SHOP,
    BalatroAction,
)
from games.balatro.joker import Joker
from games.balatro.live.joker_projection import LiveJokerScoreProjector
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.shop import BalatroShopActionGenerator
from games.balatro.live.shop_sync import BufferedShopTransaction
from games.balatro.live.synchronizer import BalatroLiveSynchronizer
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.shop_policy import BalatroShopPolicy, ShopActionScore
from games.balatro.state import BalatroState

from .save_observer import SaveBalatroObserver
from .shop_mouse import ExternalShopMouseExecutor
from .shop_reflow import ShopMainReflowLocator


@dataclass
class ExternalShopSession:
    """Mutable projected SHOP state backed by one persisted save checkpoint."""

    snapshot: LiveBalatroSnapshot
    state: BalatroState
    transaction: BufferedShopTransaction
    closed: bool = False


class ExternalShopController:
    """Coordinate save observation, shop decisions, buffered input, and reconciliation."""

    def __init__(
        self,
        observer: SaveBalatroObserver,
        executor: ExternalShopMouseExecutor,
        *,
        translator=None,
        action_generator=None,
        policy=None,
        synchronizer=None,
        checkpoint_phases: set[str] | None = None,
        reflow_locator=None,
    ):
        self.observer = observer
        self.executor = executor
        self.translator = translator or DefaultBalatroStateTranslator()
        self.action_generator = action_generator or BalatroShopActionGenerator()
        self.policy = policy or BalatroShopPolicy()
        self.synchronizer = synchronizer or BalatroLiveSynchronizer(
            observer,
            timeout=15.0,
        )
        self.checkpoint_phases = checkpoint_phases or {"BLIND_SELECT"}
        self.reflow_locator = reflow_locator or ShopMainReflowLocator(executor)

    def open(self) -> ExternalShopSession:
        snapshot = self.observer.observe()
        state = self.translator.translate(snapshot)
        if state.phase != "SHOP":
            raise ValueError(
                f"external shop session requires SHOP phase, observed {state.phase}"
            )

        return ExternalShopSession(
            snapshot=snapshot,
            state=state,
            transaction=BufferedShopTransaction.begin(state),
        )

    def available_actions(
        self,
        session: ExternalShopSession,
    ) -> list[BalatroAction]:
        self._require_open(session)
        actions = self.action_generator.generate_bufferable_actions(session.state)
        return [
            action
            for action in actions
            if action.name != BUY_JOKER
            or not isinstance(action.target, Joker)
            or LiveJokerScoreProjector.supports(action.target)
        ]

    def rank_actions(
        self,
        session: ExternalShopSession,
    ) -> list[ShopActionScore]:
        self._require_open(session)
        return self.policy.rank_actions(
            session.state,
            self.available_actions(session),
        )

    def recommended_action(
        self,
        session: ExternalShopSession,
    ) -> BalatroAction:
        ranked = self.rank_actions(session)
        if not ranked:
            raise RuntimeError("no buffer-safe shop action is available")
        return ranked[0].action

    def execute_recommended_purchase(
        self,
        session: ExternalShopSession,
    ) -> BalatroAction:
        """Execute exactly one current policy-recommended purchase.

        END_SHOP is deliberately not executed here. Call leave_shop() explicitly so
        policy-driven purchase validation cannot unexpectedly advance the run.
        """
        action = self.recommended_action(session)
        if action.name == END_SHOP:
            raise RuntimeError(
                "shop policy recommends END_SHOP; no purchase should be executed"
            )
        self.execute_purchase(session, action)
        return action

    def execute_purchase(
        self,
        session: ExternalShopSession,
        action: BalatroAction,
    ) -> BalatroState:
        self._require_open(session)
        if action.name == END_SHOP:
            raise ValueError("use leave_shop() for END_SHOP")

        use_fresh_main_geometry = (
            bool(session.transaction.purchases)
            and action.name in {BUY_JOKER, BUY_CONSUMABLE}
        )
        if use_fresh_main_geometry:
            self.reflow_locator.dispatch(
                action,
                session.state,
                session.transaction,
            )
        else:
            self.executor.dispatch(
                action,
                session.state,
                session.transaction,
            )
        return session.state

    def leave_shop(
        self,
        session: ExternalShopSession,
    ) -> tuple[LiveBalatroSnapshot, BalatroState]:
        self._require_open(session)
        end_shop = self._end_shop_action(session)

        self.executor.dispatch(end_shop, session.state)
        persisted_snapshot = self.synchronizer.wait_for_change(
            session.snapshot,
            phases=self.checkpoint_phases,
            require_complete=False,
        )
        persisted_state = self.translator.translate(persisted_snapshot)
        session.transaction.assert_reconciled(persisted_state)
        session.closed = True
        return persisted_snapshot, persisted_state

    def _end_shop_action(self, session: ExternalShopSession) -> BalatroAction:
        for action in self.action_generator.generate_bufferable_actions(session.state):
            if action.name == END_SHOP:
                return action
        raise RuntimeError("END_SHOP is not available in current projected shop state")

    @staticmethod
    def _require_open(session: ExternalShopSession) -> None:
        if session.closed:
            raise RuntimeError("external shop session is already closed")
