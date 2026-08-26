from __future__ import annotations

"""Luchador boss-disable policy derived from live Red/White reviews.

Luchador is consumable boss protection. The original policy only spent it after D1
had already entered PACE_RECOVERY. That is too late for bosses whose effect can
poison normal hand construction from the opening draw (notably card-debuff bosses).

Proactive use is nevertheless a late override of D1 and must not burn Luchador just
because a named boss is present. For the card-debuff bosses whose disabled state is
fully represented by the public card debuff flags, compare canonical D1 clear
probability before and after removing those debuffs. Spend Luchador proactively only
when disabling the boss strictly improves modeled survival. Other high-pressure
bosses retain the conservative PACE_RECOVERY trigger because their full disabled
state is not reducible to card debuff flags alone.

The dispatcher remains fail-closed: only Luchador may be sold through this combat
path, and already-disabled bosses never consume it.
"""

from copy import deepcopy

from games.balatro.actions import SELL_JOKER, BalatroAction
from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
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

# These bosses express their relevant live effect through public playing-card
# debuff flags. Their disabled state can therefore be compared exactly enough for
# the bounded proactive Luchador gate without inventing future information.
_PROACTIVE_DISABLE_BOSSES = frozenset(
    {
        "The Club",
        "The Goad",
        "The Window",
        "The Head",
        "The Plant",
    }
)

_EPSILON = 1e-12


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


def _clear_probability(state) -> float | None:
    try:
        plan = LiveBlindClearPlanner().plan(state)
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
        return None
    return max(0.0, min(1.0, float(plan.value.clear_probability)))


def _state_with_card_debuff_boss_disabled(state):
    projected = deepcopy(state)
    for area_name in ("hand", "deck", "discard_pile"):
        for card in tuple(getattr(projected, area_name, ()) or ()):
            if hasattr(card, "debuffed"):
                card.debuffed = False
    owned = getattr(projected, "owned_deck", None)
    if owned is not None:
        for card in tuple(owned):
            if hasattr(card, "debuffed"):
                card.debuffed = False
    return projected


def _proactive_disable_clear_gain(state) -> tuple[bool, float, float]:
    """Return whether a card-debuff boss disable strictly improves D1 survival."""
    # No observed debuffed cards means there is no currently modeled boss damage to
    # justify consuming a one-use Joker. Preserve it rather than extrapolating future
    # harm that the public state does not establish.
    observed_cards = [
        *tuple(getattr(state, "hand", ()) or ()),
        *tuple(getattr(state, "deck", ()) or ()),
    ]
    if not any(bool(getattr(card, "debuffed", False)) for card in observed_cards):
        return False, 0.0, 0.0

    before = _clear_probability(state)
    after = _clear_probability(_state_with_card_debuff_boss_disabled(state))
    if before is None or after is None:
        return False, 0.0, 0.0
    return after > before + _EPSILON, before, after


def _should_sell_luchador(state, notes: tuple[str, ...]) -> tuple[bool, tuple[str, ...]]:
    boss_name = str(getattr(state, "boss_name", "") or "")
    if not boss_name:
        return False, ()
    if boss_blind_disabled_by_owned_jokers(state):
        return False, ()
    if _find_luchador(state) is None:
        return False, ()

    hands = max(0, int(getattr(state, "hands_remaining", 0) or 0))
    discards = max(0, int(getattr(state, "discards_remaining", 0) or 0))

    if boss_name in _PROACTIVE_DISABLE_BOSSES:
        improves, before, after = _proactive_disable_clear_gain(state)
        if not improves:
            return False, ()
        return True, (
            "proactive Luchador use is grounded by canonical D1 survival improvement",
            f"public D1 clear probability {before:.6f}->{after:.6f}",
            f"clear-probability gain={after - before:.6f}",
        )

    if _decision_mode(notes) != "PACE_RECOVERY":
        return False, ()
    should_sell = bool(
        boss_name in _HIGH_PRESSURE_BOSSES
        or hands <= 1
        or discards <= 0
    )
    return should_sell, (
        "D1 PACE_RECOVERY triggered conservative Luchador emergency use",
    ) if should_sell else ()


def install_luchador_activation_policy() -> None:
    if getattr(
        LiveMemoryInjectedSingleStepRunner,
        "_luchador_activation_policy_installed",
        False,
    ):
        return

    original_decide = LiveMemoryInjectedSingleStepRunner.decide

    def decide(self):
        decision = original_decide(self)
        if (
            str(decision.snapshot.phase) != "SELECTING_HAND"
            or decision.source != "D1 hand-action policy"
        ):
            return decision

        should_sell, activation_notes = _should_sell_luchador(
            decision.state,
            decision.notes,
        )
        if not should_sell:
            return decision

        luchador = _find_luchador(decision.state)
        if luchador is None:
            return decision
        boss_name = str(getattr(decision.state, "boss_name", "") or "unknown boss")
        proactive = boss_name in _PROACTIVE_DISABLE_BOSSES
        return AutonomousStepDecision(
            decision.snapshot,
            decision.state,
            BalatroAction(SELL_JOKER, target=luchador),
            "Luchador boss-disable policy",
            (
                f"boss={boss_name}",
                *activation_notes,
                (
                    "proactive boss disable: observed card debuff materially reduces modeled clear probability"
                    if proactive
                    else "D1 entered PACE_RECOVERY with Luchador available"
                ),
                "sell Luchador, then re-observe the disabled boss before committing any hand/discard action",
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
    LiveMemoryInjectedSingleStepRunner._luchador_activation_policy_installed = True
