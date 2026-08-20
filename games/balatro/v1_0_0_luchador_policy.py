from __future__ import annotations

"""Luchador boss-disable policy derived from the five-run v1.0.0 review.

The review exposed a concrete failure mode: the agent carried Luchador through The
Needle while D1 was in recovery mode, spent every discard, then lost its only hand.
The semantic SELL_JOKER action already exists, but injected mid-blind selling was
restricted to Verdant Leaf, so Luchador's active effect was unreachable.

This layer stays deliberately conservative.  It never sells Luchador when D1 has a
normal pace/clear recommendation.  It only intervenes while a boss is active and D1
has entered PACE_RECOVERY, with either a known high-pressure boss or critically low
hand/discard runway.
"""

from games.balatro.actions import SELL_JOKER, BalatroAction
from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.live.injected.action_dispatcher import (
    LiveInjectedActionResult,
    LiveMemoryInjectedActionDispatcher,
    UnsupportedInjectedAction,
    _active_boss_name,
    _area_cards,
    _area_item,
    _target_index,
)
from games.balatro.live.runtime.live_memory_autonomous_step_injected import (
    AutonomousStepDecision,
    LiveMemoryInjectedSingleStepRunner,
)


_HIGH_PRESSURE_BOSSES = frozenset(
    {
        "The Needle",
        "The Water",
        "The Flint",
        "The Wall",
        "Violet Vessel",
        "Verdant Leaf",
    }
)


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _is_luchador(value: object) -> bool:
    if isinstance(value, dict):
        candidates = (
            value.get("center"),
            value.get("label"),
            value.get("name"),
            value.get("ability_name"),
        )
    else:
        candidates = (
            type(value).__name__,
            getattr(value, "center", None),
            getattr(value, "label", None),
            getattr(value, "name", None),
        )
    return bool(
        {"luchador", "luchadorjoker", "jluchador"}
        & {_normalize(candidate) for candidate in candidates if candidate is not None}
    )


def _find_luchador(state):
    for joker in getattr(state, "jokers", ()) or ():
        if _is_luchador(joker) and getattr(joker, "area_index", None) is not None:
            return joker
    return None


def _decision_mode(notes: tuple[str, ...]) -> str | None:
    for note in notes:
        if str(note).startswith("mode="):
            return str(note).split("=", 1)[1].strip().upper()
    return None


def _should_sell_luchador(state, notes: tuple[str, ...]) -> bool:
    boss_name = str(getattr(state, "boss_name", "") or "")
    if not boss_name or _decision_mode(notes) != "PACE_RECOVERY":
        return False
    if boss_blind_disabled_by_owned_jokers(state):
        return False
    if _find_luchador(state) is None:
        return False

    hands = max(0, int(getattr(state, "hands_remaining", 0) or 0))
    discards = max(0, int(getattr(state, "discards_remaining", 0) or 0))
    return bool(
        boss_name in _HIGH_PRESSURE_BOSSES
        or hands <= 1
        or discards <= 0
    )


def install_v1_0_0_luchador_policy() -> None:
    if getattr(
        LiveMemoryInjectedSingleStepRunner,
        "_v1_0_0_luchador_policy_installed",
        False,
    ):
        return

    original_decide = LiveMemoryInjectedSingleStepRunner.decide

    def decide(self):
        decision = original_decide(self)
        if (
            str(decision.snapshot.phase) != "SELECTING_HAND"
            or decision.source != "D1 hand-action policy"
            or not _should_sell_luchador(decision.state, decision.notes)
        ):
            return decision

        luchador = _find_luchador(decision.state)
        if luchador is None:
            return decision
        boss_name = str(getattr(decision.state, "boss_name", "") or "unknown boss")
        return AutonomousStepDecision(
            decision.snapshot,
            decision.state,
            BalatroAction(SELL_JOKER, target=luchador),
            "Luchador boss-disable policy",
            (
                f"boss={boss_name}",
                "D1 entered PACE_RECOVERY with Luchador available",
                "sell Luchador before spending further hand/discard runway; re-observe after boss disable",
                *decision.notes,
            ),
        )

    LiveMemoryInjectedSingleStepRunner.decide = decide

    original_dispatch = LiveMemoryInjectedActionDispatcher.dispatch

    def dispatch(self, action, *, state=None, snapshot=None):
        before = snapshot or self.observer.observe()
        if (
            action.name != SELL_JOKER
            or before.phase != "SELECTING_HAND"
            or _active_boss_name(before) is None
        ):
            return original_dispatch(self, action, state=state, snapshot=before)

        index = _target_index(action.target)
        item = _area_item(before, "jokers", index)
        if not _is_luchador(item):
            # Preserve the existing fail-closed dispatcher contract.  Verdant Leaf
            # remains handled by the original dispatcher; arbitrary combat sales
            # are still forbidden.
            return original_dispatch(self, action, state=state, snapshot=before)

        before_count = len(_area_cards(before, "jokers"))
        target_live_id = item.get("live_id")
        self.bridge.sell_joker(index)

        def luchador_sale_settled(value) -> bool:
            after_jokers = _area_cards(value, "jokers")
            if (
                value.sequence <= before.sequence
                or value.phase != before.phase
                or not value.state_complete
                or len(after_jokers) != before_count - 1
            ):
                return False
            if target_live_id is None:
                return True
            return all(
                not isinstance(joker, dict)
                or joker.get("live_id") != target_live_id
                for joker in after_jokers
            )

        after = self._wait(before, luchador_sale_settled, "Luchador boss-disable sale")
        return LiveInjectedActionResult(
            action,
            before,
            after,
            {"area_index": index, "item": item, "boss": _active_boss_name(before)},
        )

    LiveMemoryInjectedActionDispatcher.dispatch = dispatch
    LiveMemoryInjectedSingleStepRunner._v1_0_0_luchador_policy_installed = True
