from __future__ import annotations

"""Preserve Purple-Seal discard branches through D1's bounded candidate beam.

Purple Seal is mechanically different from held-value seals: when a non-debuffed
Purple-Seal card is discarded and consumable capacity is available, Balatro creates
a Tarot. ``LiveDiscardJokerProjector`` already models that exact transition. This
module only prevents the bounded D1 candidate beam from pruning every such branch
before expectimax can compare it.

No chip-equivalent bonus is invented here. Final action ranking remains owned by
``LiveBlindPlanValue``: survival, progress, remaining hand/discard resources and
score are compared before the projected consumable count.
"""

from games.balatro.actions import BalatroAction, DISCARD_CARDS
from games.balatro.live.hand_action_planner_core import D1LiveBlindClearPlanner


def _open_consumable_slots(state) -> int:
    return max(
        0,
        int(getattr(state, "consumable_slots", 0) or 0)
        - len(getattr(state, "consumables", ()) or ()),
    )


def _eligible_purple_cards(state, cards) -> tuple:
    if _open_consumable_slots(state) <= 0:
        return ()
    return tuple(
        card
        for card in tuple(cards or ())
        if not bool(getattr(card, "debuffed", False))
        and str(getattr(card, "seal", "") or "").upper() == "PURPLE"
    )


def _purple_generation_count(state, action) -> int:
    room = _open_consumable_slots(state)
    if room <= 0:
        return 0
    return min(room, len(_eligible_purple_cards(state, getattr(action, "cards", ()))))


def install_purple_seal_discard_policy() -> None:
    if getattr(D1LiveBlindClearPlanner, "_purple_seal_discard_policy_installed", False):
        return

    original_child_candidates = D1LiveBlindClearPlanner._child_discard_candidates
    original_diverse_beam = D1LiveBlindClearPlanner._diverse_discard_beam

    def child_discard_candidates(self, state):
        candidates = list(original_child_candidates(self, state))
        purple_cards = _eligible_purple_cards(state, getattr(state, "hand", ()))
        if not purple_cards:
            return candidates

        seen = {self._action_identity(action) for action in candidates}
        # A singleton branch is enough to expose the trigger without replacing the
        # ordinary redraw-size representatives. Larger Purple-inclusive discards can
        # still arrive from exhaustive root generation.
        for card in purple_cards:
            action = BalatroAction(DISCARD_CARDS, cards=[card])
            key = self._action_identity(action)
            if key in seen:
                continue
            candidates.append(action)
            seen.add(key)
        return candidates

    def diverse_discard_beam(self, state, discards, limit: int):
        chosen = list(original_diverse_beam(self, state, discards, limit))
        if limit < 2 or not discards or _open_consumable_slots(state) <= 0:
            return chosen
        if any(_purple_generation_count(state, action) > 0 for action in chosen):
            return chosen

        purple = [
            action
            for action in discards
            if _purple_generation_count(state, action) > 0
        ]
        if not purple:
            return chosen

        # Reserve one search slot for this mechanically distinct transition; this is
        # beam coverage, not final preference. Expectimax still decides whether the
        # branch is worth taking after projecting the draw and generated Tarot.
        candidate = max(
            purple,
            key=lambda action: (
                _purple_generation_count(state, action),
                self._discard_priority(state, action),
                -len(getattr(action, "cards", ()) or ()),
            ),
        )
        key = self._action_identity(candidate)
        if any(self._action_identity(action) == key for action in chosen):
            return chosen
        if len(chosen) < limit:
            chosen.append(candidate)
        elif chosen:
            chosen[-1] = candidate
        return chosen

    D1LiveBlindClearPlanner._child_discard_candidates = child_discard_candidates
    D1LiveBlindClearPlanner._diverse_discard_beam = diverse_discard_beam
    D1LiveBlindClearPlanner._purple_seal_discard_policy_installed = True
