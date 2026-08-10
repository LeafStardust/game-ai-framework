import time

from agents.red_deck_agent import RedDeckAgent
from games.balatro.actions import (
    BalatroAction,
    END_ROUND,
    END_SHOP,
    USE_CONSUMABLE,
)
from games.balatro.card_selector import CardSelector
from games.balatro.consumable import ConsumableContext
from games.balatro.live.action_executor import DefaultBalatroActionExecutor
from games.balatro.live.balatrobot_bridge import BalatroBotBridge
from games.balatro.live.lifecycle import BalatroLiveLifecycle
from games.balatro.live.recovery import BalatroLiveRecovery
from games.balatro.live.telemetry import BalatroConsoleTelemetry
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.state import BalatroState


class BalatroLiveRunner:
    """Runs a deck agent against a live BalatroBot-controlled game."""

    def __init__(
        self,
        bridge: BalatroBotBridge | None = None,
        agent=None,
        translator=None,
        executor=None,
        telemetry=None,
        poll_interval: float = 0.05,
        max_idle_polls: int = 200,
    ):
        self.bridge = bridge or BalatroBotBridge()
        self.agent = agent or RedDeckAgent()
        self.translator = translator or DefaultBalatroStateTranslator()
        self.executor = executor or DefaultBalatroActionExecutor()
        self.telemetry = telemetry or BalatroConsoleTelemetry()
        self.recovery = BalatroLiveRecovery(self.bridge)
        self.lifecycle = BalatroLiveLifecycle(self.recovery)
        self.card_selector = CardSelector()
        self.poll_interval = max(0.0, poll_interval)
        self.max_idle_polls = max(1, max_idle_polls)

    def run(
        self,
        deck: str = "RED",
        stake: str = "WHITE",
        seed: str | None = None,
        max_steps: int = 5000,
    ) -> bool:
        snapshot = self.lifecycle.restart_run(
            deck=deck,
            stake=stake,
            seed=seed,
        )
        state = self.translator.translate(snapshot)
        self.telemetry.run_started(snapshot, state)

        steps = 0
        idle_polls = 0

        while snapshot.phase != "GAME_OVER":
            if steps >= max_steps:
                error = RuntimeError(
                    f"live Balatro run exceeded {max_steps} steps"
                )
                self.telemetry.error(error)
                raise error

            try:
                next_snapshot, action = self._step(snapshot, state)
            except Exception as error:
                self.telemetry.error(error)
                raise

            if action is not None:
                self.telemetry.decision(action, state)

            unchanged = (
                next_snapshot.sequence == snapshot.sequence
                and next_snapshot.phase == snapshot.phase
            )
            idle_polls = idle_polls + 1 if unchanged else 0

            if idle_polls >= self.max_idle_polls:
                error = RuntimeError(
                    f"live Balatro state stalled in {snapshot.phase}"
                )
                self.telemetry.error(error)
                raise error

            snapshot = next_snapshot
            state = self.translator.translate(snapshot)
            steps += 1

            if snapshot.phase != "GAME_OVER":
                self.telemetry.state_observed(snapshot, state)

        self.telemetry.run_finished(snapshot, state)
        return snapshot.payload.get("won") is True

    def _step(
        self,
        snapshot,
        state: BalatroState,
    ):
        if snapshot.phase == "BLIND_SELECT":
            action = BalatroAction("SELECT_BLIND")
            return self.lifecycle.select_blind(), action

        if snapshot.phase == "SELECTING_HAND":
            actions = self._hand_actions(state)
            if not actions:
                return self._observe_transition(), None

            action = self.agent.act(state, actions)
            command = self.executor.command_for(action, snapshot)
            return self.recovery.send(command), action

        if snapshot.phase == "ROUND_EVAL":
            action = BalatroAction(END_ROUND)
            command = self.executor.command_for(action, snapshot)
            return self.recovery.send(command), action

        if snapshot.phase == "SHOP":
            action = BalatroAction(END_SHOP)
            command = self.executor.command_for(action, snapshot)
            return self.recovery.send(command), action

        return self._observe_transition(), None

    def _hand_actions(
        self,
        state: BalatroState,
    ) -> list[BalatroAction]:
        actions = self.card_selector.generate_actions(state)

        for consumable in state.consumables:
            for cards in consumable.get_target_cards(state):
                context = ConsumableContext(
                    state=state,
                    cards=cards,
                    target=consumable,
                )
                if consumable.can_use(context):
                    actions.append(
                        BalatroAction(
                            USE_CONSUMABLE,
                            cards=cards,
                            target=consumable,
                        )
                    )

        return actions

    def _observe_transition(self):
        if self.poll_interval > 0:
            time.sleep(self.poll_interval)
        return self.recovery.observe()
