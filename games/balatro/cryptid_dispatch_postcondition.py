from __future__ import annotations

"""Verify Cryptid pack execution from the public permanent deck.

The generic targeted-consumable verifier expects the selected card itself to change.
Cryptid instead leaves that source untouched and adds two exact copies to the owned
playing-card collection.  Verify that semantic transition directly so injected pack
execution remains fail-closed rather than accepting a click with no checked result.
"""

from dataclasses import dataclass

from games.balatro.live.injected import action_dispatcher
from games.balatro.live.injected import consumable_target_postcondition as postconditions


@dataclass(frozen=True)
class CryptidCopyPostcondition:
    source_live_id: int | str
    signature: postconditions.CardSignature
    minimum_owned_count: int

    @property
    def live_ids(self) -> tuple[int | str, ...]:
        return (self.source_live_id,)

    def matches(self, snapshot) -> bool:
        records = postconditions._target_card_records(snapshot)
        count = sum(
            1
            for record in records
            if postconditions._snapshot_card_signature(record) == self.signature
        )
        return count >= self.minimum_owned_count


def _cryptid_postcondition(state, consumable, target_indices):
    if len(target_indices) != 1:
        raise ValueError("modeled Cryptid verification requires exactly one hand target")

    hand = list(getattr(state, "hand", ()))
    index = target_indices[0]
    if index < 0 or index >= len(hand):
        raise ValueError("modeled Cryptid target index is outside the public hand")

    source = hand[index]
    live_id = getattr(source, "live_id", None)
    if live_id is None:
        raise ValueError("modeled Cryptid verification requires live_id on its source card")

    owned = getattr(state, "owned_deck", None)
    if owned is None:
        raise ValueError(
            "modeled Cryptid verification requires authoritative public owned_deck"
        )

    signature = postconditions._model_card_signature(source)
    before_count = sum(
        1
        for card in owned
        if postconditions._model_card_signature(card) == signature
    )
    return CryptidCopyPostcondition(
        source_live_id=live_id,
        signature=signature,
        minimum_owned_count=before_count + 2,
    )


def install_cryptid_dispatch_postcondition() -> None:
    if getattr(action_dispatcher, "_cryptid_postcondition_installed", False):
        return

    original = action_dispatcher.build_consumable_target_postcondition_for_consumable

    def build(state, *, consumable, target_indices, snapshot=None):
        category = str(getattr(consumable, "category", "")).upper()
        name = str(getattr(consumable, "name", ""))
        if category == "SPECTRAL" and name == "Cryptid":
            return _cryptid_postcondition(state, consumable, target_indices)
        return original(
            state,
            consumable=consumable,
            target_indices=target_indices,
            snapshot=snapshot,
        )

    action_dispatcher.build_consumable_target_postcondition_for_consumable = build
    action_dispatcher._cryptid_postcondition_installed = True
