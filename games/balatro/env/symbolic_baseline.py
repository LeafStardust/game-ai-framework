"""Exact adapter from existing symbolic policies to the headless action schema."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Callable, Iterable

from games.balatro.actions import BalatroAction
from games.balatro.env.action_encoding import PUBLIC_ACTION_VERSION, action_index, legal_action_mask
from games.balatro.env.actions import EnvAction
from games.balatro.env.observation_encoding import PUBLIC_OBSERVATION_VERSION
from games.balatro.env.state import EnvStateFrame, RunStatus, TurnOwner


SYMBOLIC_HEADLESS_BASELINE_VERSION = "balatro-symbolic-headless-baseline-v1"


class SymbolicHeadlessBaselineError(ValueError):
    """Raised when symbolic output cannot map exactly to a legal schema slot."""


@dataclass(frozen=True)
class SymbolicHeadlessDecision:
    baseline_version: str
    observation_version: str
    action_version: str
    action_index: int
    action: EnvAction


SymbolicDecider = Callable[[object, tuple[BalatroAction, ...]], BalatroAction]


def _symbolic_policy_state(frame: EnvStateFrame):
    """Return an object-rich view with the same privacy boundary as v1 encoding."""
    state = deepcopy(frame.observation())
    # Remaining-deck size is public; its physical identities and order are not.
    state.deck = [None] * len(state.deck)
    for collection_name in (
        "hand", "owned_deck", "discard_pile", "jokers", "consumables",
        "shop_jokers", "shop_consumables", "shop_boosters", "shop_vouchers",
    ):
        collection = getattr(state, collection_name)
        if collection is None:
            continue
        for item in collection:
            for name in ("live_id", "area_index"):
                if hasattr(item, name):
                    setattr(item, name, None)
    return state


def _target_for(action: EnvAction, state):
    payload = action.payload()
    if action.alias == "BUY_JOKER":
        collection, key = state.shop_jokers, "slot"
    elif action.alias == "BUY_VOUCHER":
        collection, key = state.shop_vouchers, "slot"
    elif action.alias == "BUY_CONSUMABLE":
        collection, key = state.shop_consumables, "slot"
    elif action.alias == "OPEN_PACK":
        collection, key = state.shop_boosters, "slot"
    elif action.alias == "USE_CONSUMABLE":
        collection, key = state.consumables, "consumable_index"
    elif action.alias == "SELL_JOKER":
        return payload["joker_index"]
    elif action.alias == "CHOOSE_PACK_OPTION":
        raise SymbolicHeadlessBaselineError(
            "public pack-choice objects are not owned by EnvStateFrame"
        )
    else:
        if payload:
            raise SymbolicHeadlessBaselineError(
                f"parameterized symbolic mapping is unsupported for {action.alias}"
            )
        return None
    index = payload[key]
    if index < 0 or index >= len(collection):
        raise SymbolicHeadlessBaselineError(
            f"legal {action.alias} slot is absent from the public observation"
        )
    return collection[index]


class DeterministicSymbolicHeadlessBaseline:
    """Run one existing symbolic authority over exact headless candidates."""

    def __init__(self, decider: SymbolicDecider):
        if not callable(decider):
            raise TypeError("symbolic decider must be callable")
        self._decider = decider

    def select(
        self,
        frame: EnvStateFrame,
        legal_actions: Iterable[EnvAction],
    ) -> SymbolicHeadlessDecision | None:
        if not isinstance(frame, EnvStateFrame):
            raise TypeError("frame must be EnvStateFrame")
        actions = tuple(legal_actions)
        if frame.status.terminal:
            if actions:
                raise SymbolicHeadlessBaselineError("terminal frame cannot expose legal actions")
            return None
        if frame.status is not RunStatus.RUNNING or frame.owner is not TurnOwner.AGENT:
            raise SymbolicHeadlessBaselineError(
                "symbolic strategic selection requires an agent-owned running frame"
            )

        observation = frame.encoded_observation()
        mask = legal_action_mask(actions)
        if observation.schema_version != PUBLIC_OBSERVATION_VERSION:
            raise SymbolicHeadlessBaselineError("observation schema version mismatch")
        if mask.schema_version != PUBLIC_ACTION_VERSION:
            raise SymbolicHeadlessBaselineError("action schema version mismatch")
        if not any(mask.values):
            raise SymbolicHeadlessBaselineError(
                "nonterminal agent frame has an empty legal action mask"
            )

        policy_state = _symbolic_policy_state(frame)
        candidates: list[tuple[BalatroAction, EnvAction]] = []
        for action in actions:
            target = _target_for(action, policy_state)
            candidates.append((BalatroAction(action.action_id, target=target), action))

        selected = self._decider(policy_state, tuple(candidate for candidate, _ in candidates))
        if not isinstance(selected, BalatroAction) or selected.cards:
            raise SymbolicHeadlessBaselineError(
                "symbolic authority returned an unsupported action representation"
            )
        matches = [
            action
            for candidate, action in candidates
            if selected.name == candidate.name and selected.target is candidate.target
        ]
        if len(matches) != 1:
            raise SymbolicHeadlessBaselineError(
                "symbolic decision does not identify exactly one legal candidate"
            )
        action = matches[0]
        index = action_index(action)
        if not mask.values[index]:
            raise RuntimeError("symbolic adapter selected a masked action")
        return SymbolicHeadlessDecision(
            SYMBOLIC_HEADLESS_BASELINE_VERSION,
            observation.schema_version,
            mask.schema_version,
            index,
            action,
        )
