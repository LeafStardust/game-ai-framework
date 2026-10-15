"""Serialize Mahjong Soul input and stop on uncertain delivery or confirmation."""

from dataclasses import asdict
from threading import RLock
import time

from games.mahjong_soul.live.runtime.input import DiscardPlan, DiscardExecutor, board_token
from games.mahjong_soul.live.runtime.kan import ConcealedKanPlan, ConcealedKanExecutor
from games.mahjong_soul.live.runtime.riichi import RiichiPlan, RiichiExecutor
from games.mahjong_soul.live.runtime.skip import SkipPlan, SkipExecutor
from games.mahjong_soul.live.runtime.calls import PonPlan, PonExecutor, ChiPlan, ChiExecutor


class InputController:
    def __init__(self, backend, confirmation_timeout=5.0):
        if confirmation_timeout <= 0:
            raise ValueError("Confirmation timeout must be positive")
        self._executors = {DiscardPlan: DiscardExecutor(backend),
                           PonPlan: PonExecutor(backend), ChiPlan: ChiExecutor(backend), SkipPlan: SkipExecutor(backend), RiichiPlan: RiichiExecutor(backend),
                           ConcealedKanPlan: ConcealedKanExecutor(backend)}
        self._lock = RLock()
        self._active = None
        self._active_key = None
        self._deadline = None
        self._blocked = None
        self._attempted = set()
        self.confirmation_timeout = confirmation_timeout

    @staticmethod
    def _now(now):
        return time.monotonic() if now is None else now

    @staticmethod
    def _key(report, step):
        meta = (report.get("state") or {}).get("round", {})
        return (report.get("game_connection"), report.get("game_generation", 0),
                meta.get("chang", 0), meta.get("ju", 0), meta.get("ben", 0), step)

    def submit(self, plan, report, *, enabled=False, now=None):
        with self._lock:
            self.update(report, now=now)
            if self._active is not None or self._blocked:
                raise ValueError("Input is pending or blocked; no overlapping action")
            if not enabled:
                raise ValueError("Real input is disabled")
            executor = self._executors.get(type(plan))
            if executor is None:
                raise ValueError("Unsupported input plan")
            key = self._key(report, plan.step)
            if key in self._attempted:
                raise ValueError("An action was already attempted at this game step")
            self._active = executor
            self._active_key = key
            self._attempted.add(key)
            try:
                executor.execute(plan, report, enabled=True, now=now)
            except Exception:
                if executor.pending is None:
                    self._active = None
                    self._active_key = None
                    self._attempted.remove(key)
                else:
                    self._blocked = "Input delivery failed; inspect the game before recovery"
                raise
            self._deadline = self._now(now) + self.confirmation_timeout

    def confirm_selection(self, plan, report, selected_tile, *, enabled=False, now=None):
        with self._lock:
            self.update(report, now=now)
            executor = self._active
            if self._blocked or not isinstance(executor, DiscardExecutor):
                raise ValueError("No active discard selection to confirm")
            try:
                executor.confirm_selection(plan, report, selected_tile, enabled=enabled, now=now)
            except Exception:
                if plan.token in executor.selection_confirmed:
                    self._blocked = "Selection input failed; inspect the game before recovery"
                raise
            self._deadline = self._now(now) + self.confirmation_timeout

    def select_riichi_discard(self, plan, report, visible_allowed_tiles, *, enabled=False, now=None):
        with self._lock:
            self.update(report, now=now)
            executor = self._executors[RiichiPlan]
            if self._blocked or self._active is not executor:
                raise ValueError("No active riichi menu")
            try:
                executor.select_discard(plan, report, visible_allowed_tiles, enabled=enabled, now=now)
            except Exception:
                if executor.phase == "tile_selection_attempted":
                    self._blocked = "Riichi selection input failed; inspect before recovery"
                raise
            self._deadline = self._now(now) + self.confirmation_timeout

    def observe(self, connection, event, *, now=None):
        with self._lock:
            if self._active is None or self._blocked:
                return False
            if self._deadline is not None and self._now(now) >= self._deadline:
                self._blocked = "Action confirmation timed out; no automatic retry"
                return False
            if self._active.observe(connection, event):
                self._active = None
                self._active_key = None
                self._deadline = None
                return True
            if getattr(self._active, "failed", False):
                self._blocked = "Declaration was rejected by the server"
                return False
            if isinstance(self._active, RiichiExecutor) and self._active.declaration_step == event.get("step"):
                return False
            plan = self._active.pending
            if (event.get("source") == "live" and connection == plan.connection
                    and event.get("step", -1) > plan.step
                    and event.get("name") in ("ActionDiscardTile", "ActionChiPengGang", "ActionAnGangAddGang")
                    and event.get("data", {}).get("seat", 0) == plan.seat):
                self._blocked = "A different own action was observed; inspect before recovery"
            return False

    def observe_message(self, connection, decoded, from_client, *, now=None):
        """Feed RPC messages as well as action events for Skip confirmation."""
        with self._lock:
            executor = self._executors[SkipPlan]
            if self._active is not executor or self._blocked:
                return False
            if self._deadline is not None and self._now(now) >= self._deadline:
                self._blocked = "Action confirmation timed out; no automatic retry"
                return False
            if executor.observe_message(connection, decoded, from_client):
                self._active = None
                self._active_key = None
                self._deadline = None
                return True
            if executor.failed:
                self._blocked = "Skip cancellation was rejected by the server"
            return False

    def update(self, report, *, now=None):
        """Call after feeding decoded events, and periodically even with no new rows."""
        with self._lock:
            if self._active is not None and not self._blocked:
                plan = self._active.pending
                if (not report.get("connection_open") or report.get("game_connection") != plan.connection
                        or not report.get("state_ready")):
                    self._blocked = "Game state or connection is no longer ready"
                elif self._deadline is not None and self._now(now) >= self._deadline:
                    self._blocked = "Action confirmation timed out; no automatic retry"
            return self.snapshot()

    def recover(self, report, *, visually_verified=False):
        """Explicit recovery only on a newer ready board after visual inspection.

        Attempted steps are retained. Recovery does not resend any action.
        """
        with self._lock:
            if not self._blocked or self._active is None:
                raise ValueError("No blocked input to recover")
            plan = self._active.pending
            state = report.get("state") or {}
            if (not visually_verified or not report.get("state_ready")
                    or not report.get("connection_open") or board_token(report) == plan.token):
                raise ValueError("Recovery requires a visually verified newer ready board")
            if self._key(report, state.get("step"))[:-1] == self._active_key[:-1] and state.get("step", -1) <= plan.step:
                raise ValueError("Recovery cannot reuse the attempted game step")
            self._active.pending = None
            self._active = None
            self._active_key = None
            self._deadline = None
            self._blocked = None

    def snapshot(self):
        with self._lock:
            return {"status": "blocked" if self._blocked else "awaiting_confirmation" if self._active else "idle",
                    "reason": self._blocked, "deadline": self._deadline,
                    "pending": asdict(self._active.pending) if self._active and self._active.pending else None,
                    "attempted_steps": len(self._attempted)}
