from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JokerPublicFieldSpec:
    """Narrow live-memory source contract for one modeled Joker field.

    ``ability_keys`` are searched in ``card.ability`` and then in a table-valued
    ``card.ability.extra``. ``card_keys`` are explicit top-level card aliases.
    ``scalar_extra`` permits the primitive value of ``card.ability.extra`` itself
    only for Jokers whose public counter is stored there.
    """

    model_field: str
    ability_keys: tuple[str, ...] = ()
    card_keys: tuple[str, ...] = ()
    scalar_extra: bool = False


# Stateful fields that must be observed from public live state. Keep this list
# explicit. It is a whitelist, not a generic serializer for Balatro ability data.
PUBLIC_JOKER_STATE_SPECS_BY_CLASS: dict[str, tuple[JokerPublicFieldSpec, ...]] = {
    "AncientJoker": (
        # The suit itself is merged from G.GAME.current_round.ancient_card.
        JokerPublicFieldSpec("suit"),
    ),
    "CampfireJoker": (JokerPublicFieldSpec("x_mult", ("x_mult", "Xmult")),),
    "CanioJoker": (JokerPublicFieldSpec("x_mult", ("x_mult", "Xmult")),),
    "CastleJoker": (
        JokerPublicFieldSpec("chips", ("chips",)),
        JokerPublicFieldSpec("chip_mod", ("chip_mod",)),
        # Suit is merged from G.GAME.current_round.castle_card.
        JokerPublicFieldSpec("suit"),
    ),
    "ConstellationJoker": (
        JokerPublicFieldSpec("x_mult", ("x_mult", "Xmult")),
    ),
    "DaggerJoker": (JokerPublicFieldSpec("mult", ("mult",)),),
    "EggJoker": (
        JokerPublicFieldSpec(
            "sell_value",
            ("sell_value", "extra_value"),
            card_keys=("sell_cost",),
        ),
    ),
    "FlashCardJoker": (JokerPublicFieldSpec("mult", ("mult",)),),
    "FortuneTellerJoker": (JokerPublicFieldSpec("mult", ("mult",)),),
    "GlassJoker": (JokerPublicFieldSpec("x_mult", ("x_mult", "Xmult")),),
    "GreenJoker": (JokerPublicFieldSpec("mult", ("mult",)),),
    "HitTheRoadJoker": (JokerPublicFieldSpec("x_mult", ("x_mult", "Xmult")),),
    "HologramJoker": (JokerPublicFieldSpec("x_mult", ("x_mult", "Xmult")),),
    "IceCreamJoker": (
        JokerPublicFieldSpec("chips", ("chips",)),
        JokerPublicFieldSpec("chip_mod", ("chip_mod",)),
    ),
    "InvisibleJoker": (
        JokerPublicFieldSpec("rounds", ("rounds", "invis_rounds")),
    ),
    "LoyaltyCardJoker": (
        JokerPublicFieldSpec(
            "hands",
            ("hands", "hands_played", "loyalty_hands", "loyalty_remaining"),
        ),
    ),
    "LuckyCatJoker": (JokerPublicFieldSpec("x_mult", ("x_mult", "Xmult")),),
    "MadnessJoker": (JokerPublicFieldSpec("x_mult", ("x_mult", "Xmult")),),
    "ObeliskJoker": (JokerPublicFieldSpec("x_mult", ("x_mult", "Xmult")),),
    "PopcornJoker": (JokerPublicFieldSpec("mult", ("mult",)),),
    "RamenJoker": (JokerPublicFieldSpec("x_mult", ("x_mult", "Xmult")),),
    "RedCardJoker": (JokerPublicFieldSpec("mult", ("mult",)),),
    "RideTheBusJoker": (JokerPublicFieldSpec("mult", ("mult",)),),
    "RunnerJoker": (JokerPublicFieldSpec("chips", ("chips",)),),
    "SeltzerJoker": (
        JokerPublicFieldSpec(
            "rounds_remaining",
            ("rounds_remaining", "rounds"),
            scalar_extra=True,
        ),
    ),
    "SpareTrousersJoker": (JokerPublicFieldSpec("mult", ("mult",)),),
    "SquareJoker": (JokerPublicFieldSpec("chips", ("chips",)),),
    "TheIdolJoker": (
        # Rank/suit are merged from G.GAME.current_round.idol_card.
        JokerPublicFieldSpec("rank"),
        JokerPublicFieldSpec("suit"),
    ),
    "ThrowbackJoker": (JokerPublicFieldSpec("x_mult", ("x_mult", "Xmult")),),
    "ToDoListJoker": (
        JokerPublicFieldSpec(
            "target_hand",
            ("to_do_poker_hand", "target_hand"),
        ),
    ),
    "TurtleBeanJoker": (
        JokerPublicFieldSpec("hand_size", ("hand_size", "h_size")),
    ),
    "VampireJoker": (JokerPublicFieldSpec("x_mult", ("x_mult", "Xmult")),),
    "WeeJoker": (JokerPublicFieldSpec("chips", ("chips",)),),
    "YorickJoker": (
        JokerPublicFieldSpec(
            "discarded_cards",
            ("discarded_cards", "discards", "discard_count"),
        ),
        JokerPublicFieldSpec("x_mult", ("x_mult", "Xmult")),
    ),
}


# These fields mutate in the Python model, but live ownership itself determines
# their value. When they transition to the opposite value Balatro removes the
# Joker, so no mutable live counter needs to be exposed.
DERIVED_JOKER_STATE_FIELDS_BY_CLASS: dict[str, frozenset[str]] = {
    "CavendishJoker": frozenset({"active"}),
    "GrosMichelJoker": frozenset({"destroyed"}),
}


def public_joker_state_specs(class_name: str) -> tuple[JokerPublicFieldSpec, ...]:
    return PUBLIC_JOKER_STATE_SPECS_BY_CLASS.get(class_name, ())


def observed_public_joker_state_fields(class_name: str) -> frozenset[str]:
    return frozenset(spec.model_field for spec in public_joker_state_specs(class_name))


def derived_joker_state_fields(class_name: str) -> frozenset[str]:
    return DERIVED_JOKER_STATE_FIELDS_BY_CLASS.get(class_name, frozenset())


def public_joker_state_fields(class_name: str) -> frozenset[str]:
    return observed_public_joker_state_fields(class_name) | derived_joker_state_fields(class_name)


def all_observed_public_joker_state_fields() -> frozenset[str]:
    return frozenset(
        spec.model_field
        for specs in PUBLIC_JOKER_STATE_SPECS_BY_CLASS.values()
        for spec in specs
    )
