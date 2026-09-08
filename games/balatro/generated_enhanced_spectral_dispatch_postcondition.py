from __future__ import annotations

"""Verify Familiar/Grim/Incantation permanent-deck mutation after pack use.

These Spectrals have no player-selected target, so the generic targeted-consumable
postcondition path is not invoked. Wrap injected dispatch narrowly for these three
pack choices and verify their public permanent-deck effect after Balatro's ordinary
pack callback completes.

The exact destroyed identity and generated identities are random, but two invariants
are deterministic and public:

* permanent deck size changes by generated_count - 1;
* at least generated_count - 1 additional cards match the Spectral's generated
  rank/enhancement pool (the destroyed card can itself have matched that pool).

This checks the semantic mutation without consulting RNG or future draw order.
"""

from games.balatro.actions import SELECT_PACK_CARD
from games.balatro.live.injected import action_dispatcher
from games.balatro.live.injected import consumable_target_postcondition as postconditions
from games.balatro.spectrals import GENERATED_ENHANCEMENTS, NUMBERED_RANKS


_SPECS = {
    "Familiar": {
        "generated_count": 3,
        "ranks": frozenset({"J", "Q", "K"}),
    },
    "Grim": {
        "generated_count": 2,
        "ranks": frozenset({"A"}),
    },
    "Incantation": {
        "generated_count": 4,
        "ranks": frozenset(NUMBERED_RANKS),
    },
}

_GENERATED_ENHANCEMENTS = frozenset(GENERATED_ENHANCEMENTS)


def _owned_records(snapshot) -> list[dict] | None:
    area = snapshot.payload.get("owned_cards")
    if not isinstance(area, dict):
        return None
    cards = area.get("cards")
    if not isinstance(cards, list):
        return None
    return [record for record in cards if isinstance(record, dict)]


def _choice_label(action) -> str:
    target = getattr(action, "target", None)
    return str(getattr(target, "label", "") or "")


def _qualifies(record: dict, ranks: frozenset[str]) -> bool:
    signature = postconditions._snapshot_card_signature(record)
    if signature is None:
        return False
    rank, _suit, enhancement, _edition, _seal = signature
    return rank in ranks and enhancement in _GENERATED_ENHANCEMENTS


def _verify(before, after, label: str) -> None:
    spec = _SPECS[label]
    before_records = _owned_records(before)
    after_records = _owned_records(after)
    if before_records is None or after_records is None:
        raise action_dispatcher.InjectedActionPostconditionError(
            f"{label} verification requires authoritative public owned_cards"
        )

    generated_count = int(spec["generated_count"])
    expected_after_count = len(before_records) + generated_count - 1
    if len(after_records) != expected_after_count:
        raise action_dispatcher.InjectedActionPostconditionError(
            f"{label} permanent deck count mismatch: expected {expected_after_count}, "
            f"observed {len(after_records)}"
        )

    ranks = spec["ranks"]
    before_qualifying = sum(_qualifies(record, ranks) for record in before_records)
    after_qualifying = sum(_qualifies(record, ranks) for record in after_records)
    minimum_after_qualifying = before_qualifying + generated_count - 1
    if after_qualifying < minimum_after_qualifying:
        raise action_dispatcher.InjectedActionPostconditionError(
            f"{label} generated-card pool mismatch: expected at least "
            f"{minimum_after_qualifying} qualifying permanent cards, observed "
            f"{after_qualifying}"
        )


def install_generated_enhanced_spectral_dispatch_postcondition() -> None:
    if getattr(
        action_dispatcher.LiveMemoryInjectedActionDispatcher,
        "_generated_enhanced_spectral_postcondition_installed",
        False,
    ):
        return

    dispatcher_class = action_dispatcher.LiveMemoryInjectedActionDispatcher
    original_dispatch = dispatcher_class.dispatch

    def dispatch(self, action, *, state=None, snapshot=None):
        label = _choice_label(action) if action.name == SELECT_PACK_CARD else ""
        if label not in _SPECS:
            return original_dispatch(self, action, state=state, snapshot=snapshot)

        result = original_dispatch(self, action, state=state, snapshot=snapshot)
        _verify(result.before, result.after, label)
        return result

    dispatcher_class.dispatch = dispatch
    dispatcher_class._generated_enhanced_spectral_postcondition_installed = True
