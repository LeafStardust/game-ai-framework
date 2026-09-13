"""Versioned exact serialization for the admitted headless run-state surface."""

from __future__ import annotations

import math
from dataclasses import asdict, fields
from typing import Any, Mapping

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.env.blind_progression import BlindProgressionState
from games.balatro.env.boss_selection import BossSelectionState
from games.balatro.env.joker_order import JokerOrderState
from games.balatro.env.shop_booster_generation import GeneratedShopBoosterItem
from games.balatro.env.shop_consumable_items import GeneratedShopConsumableItem
from games.balatro.env.shop_items import GeneratedShopJokerItem
from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.env.tag_selection import TagProfileState
from games.balatro.state import BalatroState


HEADLESS_RUN_STATE_SCHEMA = "balatro-headless-run-state-v4"
_CARD_ZONE_FIELDS = frozenset({"deck", "owned_deck", "hand", "discard_pile"})
_UNSUPPORTED_OBJECT_FIELDS = frozenset(
    {
        "jokers",
        "consumables",
    }
)
_SHOP_ITEM_TYPES = {
    "JOKER": GeneratedShopJokerItem,
    "CONSUMABLE": GeneratedShopConsumableItem,
    "BOOSTER": GeneratedShopBoosterItem,
    "VOUCHER": GeneratedShopVoucherItem,
}
_SHOP_FIELDS = {
    "shop_jokers": "JOKER",
    "shop_consumables": "CONSUMABLE",
    "shop_boosters": "BOOSTER",
    "shop_vouchers": "VOUCHER",
}
_PRIVATE_SCALARS = (
    "round_bonus_hands",
    "round_bonus_discards",
    "boss_hands_sub",
    "boss_discards_sub",
    "boss_hand_size_sub",
    "base_reroll_cost",
    "reroll_cost",
    "skips",
    "tags",
    "pack_return_phase",
    "pack_choices_remaining",
    "consumable_usage_observed",
    "consumable_usage_counts",
    "consumable_usage_totals",
    "generation_discovery",
)


def _plain_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise HeadlessTransitionError("headless snapshot cannot contain non-finite floats")
        return value
    if isinstance(value, list):
        return [_plain_value(item) for item in value]
    if isinstance(value, tuple):
        return {"$tuple": [_plain_value(item) for item in value]}
    if isinstance(value, set):
        encoded = [_plain_value(item) for item in value]
        return {"$set": sorted(encoded, key=repr)}
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise HeadlessTransitionError("headless snapshot dictionaries require string keys")
        return {key: _plain_value(item) for key, item in sorted(value.items())}
    raise HeadlessTransitionError(
        f"headless snapshot does not support {type(value).__name__} objects"
    )


def _restore_plain(value: Any) -> Any:
    if isinstance(value, list):
        return [_restore_plain(item) for item in value]
    if isinstance(value, dict):
        if set(value) == {"$tuple"} and isinstance(value["$tuple"], list):
            return tuple(_restore_plain(item) for item in value["$tuple"])
        if set(value) == {"$set"} and isinstance(value["$set"], list):
            restored = [_restore_plain(item) for item in value["$set"]]
            try:
                return set(restored)
            except TypeError as exc:
                raise HeadlessTransitionError("invalid set value in headless snapshot") from exc
        if any(not isinstance(key, str) for key in value):
            raise HeadlessTransitionError("invalid dictionary key in headless snapshot")
        return {key: _restore_plain(item) for key, item in value.items()}
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise HeadlessTransitionError("invalid plain value in headless snapshot")


def _card_payload(card: BalatroCard) -> dict[str, Any]:
    return _plain_value(asdict(card))


def _blind_payload(blind: Blind | None) -> dict[str, Any] | None:
    if blind is None:
        return None
    if type(blind) is not Blind or blind.modifiers:
        raise HeadlessTransitionError("headless snapshot supports only modifier-free base Blind")
    return {
        "type": blind.type.value,
        "requirement": blind.requirement,
        "reward": blind.reward,
        "disabled": blind.disabled,
        "tag_key": blind.tag_key,
    }


def _boss_selection_payload(
    selection: BossSelectionState | None,
) -> dict[str, Any] | None:
    if selection is None:
        return None
    if not isinstance(selection, BossSelectionState):
        raise HeadlessTransitionError("invalid retained Boss selection state")
    return {
        "usage_counts": _plain_value(selection.usage_counts),
        "banned_keys": sorted(selection.banned_keys),
        "win_ante": selection.win_ante,
    }


def _restore_boss_selection(value: Any) -> BossSelectionState | None:
    if value is None:
        return None
    if not isinstance(value, Mapping) or set(value) != {
        "usage_counts", "banned_keys", "win_ante"
    }:
        raise HeadlessTransitionError("invalid retained Boss selection record")
    banned = value["banned_keys"]
    if (
        not isinstance(banned, list)
        or any(not isinstance(key, str) for key in banned)
        or len(banned) != len(set(banned))
    ):
        raise HeadlessTransitionError("invalid retained Boss ban state")
    try:
        return BossSelectionState(
            usage_counts=_restore_plain(value["usage_counts"]),
            banned_keys=frozenset(banned),
            win_ante=value["win_ante"],
        )
    except (TypeError, ValueError) as exc:
        raise HeadlessTransitionError("invalid retained Boss selection record") from exc


def _tag_profile_payload(profile: TagProfileState | None) -> list[str] | None:
    if profile is None:
        return None
    if not isinstance(profile, TagProfileState):
        raise HeadlessTransitionError("invalid retained Tag profile state")
    return sorted(profile.discovered_center_keys)


def _restore_tag_profile(value: Any) -> TagProfileState | None:
    if value is None:
        return None
    if (
        not isinstance(value, list)
        or any(not isinstance(key, str) for key in value)
        or len(value) != len(set(value))
    ):
        raise HeadlessTransitionError("invalid retained Tag profile record")
    return TagProfileState(frozenset(value))


def _shop_item_payload(item: Any, expected_kind: str) -> dict[str, Any]:
    item_type = _SHOP_ITEM_TYPES[expected_kind]
    if type(item) is not item_type:
        raise HeadlessTransitionError(
            f"headless snapshot requires exact generated {expected_kind} metadata"
        )
    _validate_shop_item(item, expected_kind)
    return {
        "type": expected_kind,
        "fields": _plain_value(asdict(item)),
    }


def _validate_shop_item(item: Any, kind: str) -> None:
    if not isinstance(item.center_key, str) or not item.center_key:
        raise HeadlessTransitionError("generated shop center key is invalid")
    for name in ("base_cost", "price"):
        value = getattr(item, name)
        if type(value) is not int or value < 0:
            raise HeadlessTransitionError(f"generated shop {name} is invalid")
    if item.discovered is not None and not isinstance(item.discovered, bool):
        raise HeadlessTransitionError("generated shop discovery is invalid")
    if kind == "JOKER":
        if type(item.rarity) is not int or item.rarity not in (1, 2, 3):
            raise HeadlessTransitionError("generated Joker rarity is invalid")
        if item.edition not in {None, "Foil", "Holographic", "Polychrome", "Negative"}:
            raise HeadlessTransitionError("generated Joker edition is invalid")
    elif kind == "CONSUMABLE":
        if item.card_type not in {"Tarot", "Planet"}:
            raise HeadlessTransitionError("generated consumable type is invalid")
    elif kind == "VOUCHER":
        if item.area_index is not None and (
            type(item.area_index) is not int or item.area_index < 0
        ):
            raise HeadlessTransitionError("generated Voucher area index is invalid")
    elif kind == "BOOSTER":
        if any(
            not isinstance(getattr(item, name), str) or not getattr(item, name)
            for name in ("family", "label")
        ):
            raise HeadlessTransitionError("generated Booster labels are invalid")
        if any(
            type(getattr(item, name)) is not int or getattr(item, name) < 1
            for name in ("pack_size", "choices")
        ) or item.booster_position not in (1, 2):
            raise HeadlessTransitionError("generated Booster dimensions are invalid")


def _restore_shop_item(value: Any, expected_kind: str) -> Any:
    item_type = _SHOP_ITEM_TYPES[expected_kind]
    expected_fields = {field.name for field in fields(item_type)}
    if (
        not isinstance(value, Mapping)
        or set(value) != {"type", "fields"}
        or value["type"] != expected_kind
        or not isinstance(value["fields"], Mapping)
        or set(value["fields"]) != expected_fields
    ):
        raise HeadlessTransitionError("invalid generated shop item record")
    try:
        item = item_type(**{
            key: _restore_plain(field_value)
            for key, field_value in value["fields"].items()
        })
    except (TypeError, ValueError) as exc:
        raise HeadlessTransitionError("invalid generated shop item record") from exc
    # Re-encoding enforces the admitted concrete type, metadata invariants, and
    # plain-value surface.
    _shop_item_payload(item, expected_kind)
    return item


def serialize_headless_run_state(run: HeadlessRunState) -> dict[str, Any]:
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if run.pack_choices:
        raise HeadlessTransitionError("headless snapshot does not yet support pack-choice objects")
    for name in _UNSUPPORTED_OBJECT_FIELDS:
        if getattr(run.public, name):
            raise HeadlessTransitionError(
                f"headless snapshot does not yet support nonempty {name}"
            )

    cards = run.require_playing_card_order()
    indices = {id(card): index for index, card in enumerate(cards)}

    def refs(values: list[BalatroCard] | None) -> list[int] | None:
        if values is None:
            return None
        try:
            return [indices[id(card)] for card in values]
        except KeyError as exc:
            raise HeadlessTransitionError("headless snapshot card zone is outside owned order") from exc

    public_payload: dict[str, Any] = {}
    for name, value in vars(run.public).items():
        if name in _CARD_ZONE_FIELDS:
            public_payload[name] = refs(value)
        elif name == "blind":
            public_payload[name] = _blind_payload(value)
        elif name in _SHOP_FIELDS:
            public_payload[name] = [
                _shop_item_payload(item, _SHOP_FIELDS[name]) for item in value
            ]
        else:
            public_payload[name] = _plain_value(value)

    joker_order = run.require_joker_order_state()
    if joker_order.creation_order or joker_order.physical_order:
        raise HeadlessTransitionError("headless snapshot does not yet support Joker objects")

    progression = (
        None
        if run.blind_progression_state is None
        else _plain_value(asdict(run.blind_progression_state))
    )
    return {
        "schema": HEADLESS_RUN_STATE_SCHEMA,
        "seed": run.seed,
        "rng": run.rng_snapshot(),
        "cards": [_card_payload(card) for card in cards],
        "public": public_payload,
        "private_zones": {
            "draw_pile": refs(run.draw_pile),
            "discard_pile": refs(run.discard_pile),
            "played_pile": refs(run.played_pile),
        },
        "blind_progression": progression,
        "boss_selection": _boss_selection_payload(run.boss_selection_state),
        "tag_profile": _tag_profile_payload(run.tag_profile_state),
        "private": {name: _plain_value(getattr(run, name)) for name in _PRIVATE_SCALARS},
    }


def restore_headless_run_state(payload: Mapping[str, Any]) -> HeadlessRunState:
    if not isinstance(payload, Mapping) or payload.get("schema") != HEADLESS_RUN_STATE_SCHEMA:
        raise HeadlessTransitionError("unsupported headless run-state snapshot schema")
    expected_keys = {
        "schema", "seed", "rng", "cards", "public", "private_zones",
        "blind_progression", "boss_selection", "tag_profile", "private",
    }
    if set(payload) != expected_keys:
        raise HeadlessTransitionError("headless run-state snapshot fields are incomplete")

    card_payloads = payload["cards"]
    if not isinstance(card_payloads, list):
        raise HeadlessTransitionError("headless snapshot cards must be a list")
    card_fields = {field.name for field in fields(BalatroCard)}
    cards: list[BalatroCard] = []
    for record in card_payloads:
        if not isinstance(record, Mapping) or set(record) != card_fields:
            raise HeadlessTransitionError("invalid card record in headless snapshot")
        cards.append(BalatroCard(**{key: _restore_plain(value) for key, value in record.items()}))

    def card_refs(value: Any) -> list[BalatroCard] | None:
        if value is None:
            return None
        if (
            not isinstance(value, list)
            or any(type(index) is not int or index < 0 or index >= len(cards) for index in value)
        ):
            raise HeadlessTransitionError("invalid card references in headless snapshot")
        return [cards[index] for index in value]

    public_payload = payload["public"]
    expected_public = set(vars(BalatroState()))
    if not isinstance(public_payload, Mapping) or set(public_payload) != expected_public:
        raise HeadlessTransitionError("headless public snapshot fields are incomplete")
    state = BalatroState()
    for name, value in public_payload.items():
        if name in _CARD_ZONE_FIELDS:
            setattr(state, name, card_refs(value))
        elif name == "blind":
            if value is None:
                state.blind = None
            elif isinstance(value, Mapping) and set(value) == {
                "type", "requirement", "reward", "disabled", "tag_key"
            }:
                try:
                    state.blind = Blind(
                        BlindType(value["type"]),
                        value["requirement"],
                        value["reward"],
                        disabled=value["disabled"],
                        tag_key=value["tag_key"],
                    )
                except (TypeError, ValueError) as exc:
                    raise HeadlessTransitionError("invalid Blind in headless snapshot") from exc
            else:
                raise HeadlessTransitionError("invalid Blind record in headless snapshot")
        elif name in _SHOP_FIELDS:
            if not isinstance(value, list):
                raise HeadlessTransitionError("invalid generated shop inventory")
            setattr(
                state,
                name,
                [_restore_shop_item(item, _SHOP_FIELDS[name]) for item in value],
            )
        else:
            setattr(state, name, _restore_plain(value))

    zones = payload["private_zones"]
    if not isinstance(zones, Mapping) or set(zones) != {
        "draw_pile", "discard_pile", "played_pile"
    }:
        raise HeadlessTransitionError("invalid private zones in headless snapshot")
    private = payload["private"]
    if not isinstance(private, Mapping) or set(private) != set(_PRIVATE_SCALARS):
        raise HeadlessTransitionError("invalid private fields in headless snapshot")
    progression_payload = payload["blind_progression"]
    progression = None
    if progression_payload is not None:
        expected_progression = {field.name for field in fields(BlindProgressionState)}
        if not isinstance(progression_payload, Mapping) or set(progression_payload) != expected_progression:
            raise HeadlessTransitionError("invalid blind progression in headless snapshot")
        try:
            progression = BlindProgressionState(**{
                key: _restore_plain(value) for key, value in progression_payload.items()
            })
        except (TypeError, ValueError) as exc:
            raise HeadlessTransitionError("invalid blind progression in headless snapshot") from exc

    try:
        return HeadlessRunState(
            public=state,
            seed=payload["seed"],
            rng_state=payload["rng"],
            playing_card_order=cards,
            joker_order_state=JokerOrderState([], []),
            blind_progression_state=progression,
            boss_selection_state=_restore_boss_selection(payload["boss_selection"]),
            tag_profile_state=_restore_tag_profile(payload["tag_profile"]),
            draw_pile=card_refs(zones["draw_pile"]) or [],
            discard_pile=card_refs(zones["discard_pile"]) or [],
            played_pile=card_refs(zones["played_pile"]) or [],
            pack_choices=[],
            **{key: _restore_plain(value) for key, value in private.items()},
        )
    except (TypeError, ValueError) as exc:
        raise HeadlessTransitionError("invalid headless run-state snapshot") from exc
