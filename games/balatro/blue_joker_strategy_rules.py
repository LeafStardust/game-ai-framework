from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType

from games.balatro.strategy import BANNED, GOLD, NEUTRAL, SILVER


BLUE_JOKER_STRATEGY_ID = "blue_joker_deck"
_BLUE_JOKER = "bluejoker"
_HOLOGRAM = "hologramjoker"
_DECK_GROWTH_SCORERS = frozenset({_BLUE_JOKER, _HOLOGRAM})
_DECK_GROWTH_PARTNERS = frozenset({"marblejoker", "certificatejoker"})
_PLAYING_CARD_DESTRUCTION_JOKERS = frozenset(
    {
        "tradingcardjoker",
        "sixthsensejoker",
    }
)
# Erosion does not destroy cards itself, but shrinking the deck directly opposes
# Blue Joker's cards-remaining chip scaling. These are conditional conflicts only
# while Blue Joker is actually present; Hologram alone is compatible with thinning.
_BLUE_JOKER_ROUTE_BANS = frozenset({"erosionjoker", *_PLAYING_CARD_DESTRUCTION_JOKERS})
_RETIRED_HOLOGRAM_ROUTE_IDS = (
    "hologram_growth",
    "hologram_dna",
    "hologram_certificate",
    "hologram_marble",
)


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _item_token(item: object) -> str:
    type_token = _normalize(type(item).__name__)
    if type_token and type_token not in {"simplenamespace", "object"}:
        return type_token if type_token.endswith("joker") else type_token + "joker"
    for value in (
        getattr(item, "name", ""),
        getattr(item, "label", ""),
        getattr(item, "ability_name", ""),
    ):
        token = _normalize(value)
        if token:
            return token if token.endswith("joker") else token + "joker"
    return type_token


def _owned_joker_tokens(state) -> frozenset[str]:
    return frozenset(
        _item_token(joker)
        for joker in getattr(state, "jokers", ()) or ()
    )


def _with_joker_aliases(tokens: frozenset[str]) -> frozenset[str]:
    values = set(tokens)
    for token in tuple(tokens):
        if token.endswith("joker"):
            values.add(token[:-5])
    return frozenset(values)


def _retired_requirement() -> frozenset[str]:
    return frozenset({"__merged_into_blue_hologram_deck_growth__"})


def apply_blue_joker_strategy_rules() -> None:
    """Merge Blue Joker and Hologram into one card-growth strategy family.

    Blue Joker or Hologram alone is Silver evidence. Either becomes Gold when a
    real card generator (currently Certificate or Marble Joker) is owned. The
    generator is Silver support only after at least one scorer exists, so a lone
    Certificate/Marble does not manufacture the strategy by itself.

    The legacy Hologram leaves are retired from active competition and folded into
    this route. Card-destruction is Banned only while Blue Joker is actually part of
    the engine; Hologram by itself does not require a large remaining deck.
    """
    from games.balatro import strategy_conditional_relationships as relationships
    from games.balatro import strategy_tree_catalog as catalog

    definitions = dict(catalog.TREE_MIGRATED_UNIVERSAL_BALATRO_STRATEGIES)
    definition = definitions.get(BLUE_JOKER_STRATEGY_ID)
    if definition is None:
        return

    scorer_aliases = _with_joker_aliases(_DECK_GROWTH_SCORERS)
    support_aliases = _with_joker_aliases(_DECK_GROWTH_PARTNERS)
    ban_aliases = _with_joker_aliases(_BLUE_JOKER_ROUTE_BANS)

    updated = replace(
        definition,
        name="Blue Joker / Hologram Deck-Growth",
        gold_jokers=frozenset(definition.gold_jokers - scorer_aliases),
        silver_jokers=frozenset(
            (definition.silver_jokers | scorer_aliases) - support_aliases - ban_aliases
        ),
        # Destruction conflicts are conditional on owning Blue Joker, not static.
        banned_jokers=frozenset(definition.banned_jokers - ban_aliases),
    )
    definitions[BLUE_JOKER_STRATEGY_ID] = updated
    catalog._tree_definitions[BLUE_JOKER_STRATEGY_ID] = updated

    for strategy_id in _RETIRED_HOLOGRAM_ROUTE_IDS:
        legacy = definitions.get(strategy_id)
        if legacy is None:
            continue
        retired = replace(
            legacy,
            required_jokers=_retired_requirement(),
            minimum_positive_jokers=0,
            entry_evidence_cap=0.0,
        )
        definitions[strategy_id] = retired
        catalog._tree_definitions[strategy_id] = retired

    catalog.TREE_MIGRATED_UNIVERSAL_BALATRO_STRATEGIES = MappingProxyType(definitions)

    original = relationships.conditional_joker_relationship
    if getattr(original, "_blue_joker_rules_installed", False):
        return

    def conditional_joker_relationship(state, strategy_id: str, item: object) -> str:
        if strategy_id == BLUE_JOKER_STRATEGY_ID:
            token = _item_token(item)
            owned = _owned_joker_tokens(state)
            generator_present = bool(owned & _DECK_GROWTH_PARTNERS)
            scorer_present = bool(owned & _DECK_GROWTH_SCORERS)
            blue_present = _BLUE_JOKER in owned

            if token in _BLUE_JOKER_ROUTE_BANS:
                return BANNED if blue_present else NEUTRAL
            if token in _DECK_GROWTH_SCORERS:
                return GOLD if generator_present else SILVER
            if token in _DECK_GROWTH_PARTNERS:
                return SILVER if scorer_present else NEUTRAL
        return original(state, strategy_id, item)

    conditional_joker_relationship._blue_joker_rules_installed = True
    relationships.conditional_joker_relationship = conditional_joker_relationship
