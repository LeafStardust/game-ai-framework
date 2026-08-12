from __future__ import annotations


# Public live-state fields that the observer currently exposes for each modeled
# Joker class. Keep this deliberately explicit: adding a field here is a promise
# that the value is publicly observable and intentionally whitelisted.
PUBLIC_JOKER_STATE_FIELDS_BY_CLASS: dict[str, frozenset[str]] = {
    "IceCreamJoker": frozenset({"chips", "chip_mod"}),
    "CastleJoker": frozenset({"chips", "chip_mod", "suit"}),
    "TheIdolJoker": frozenset({"rank", "suit"}),
}


def public_joker_state_fields(class_name: str) -> frozenset[str]:
    return PUBLIC_JOKER_STATE_FIELDS_BY_CLASS.get(class_name, frozenset())
