from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType

from games.balatro.strategy import BANNED, GOLD, SILVER


BLUE_JOKER_STRATEGY_ID = "blue_joker_deck"
_BLUE_JOKER = "bluejoker"
_DECK_GROWTH_PARTNERS = frozenset({"marblejoker", "certificatejoker"})
_PLAYING_CARD_DESTRUCTION_JOKERS = frozenset(
    {
        "tradingcardjoker",
        "sixthsensejoker",
    }
)
# Erosion does not destroy cards itself, but shrinking the deck is directly opposed
# to Blue Joker's cards-remaining chip scaling and remains a hard route conflict.
_BLUE_JOKER_ROUTE_BANS = frozenset({"erosionjoker", *_PLAYING_CARD_DESTRUCTION_JOKERS})


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _item_token(item: object) -> str:
    return _normalize(type(item).__name__)


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


def apply_blue_joker_strategy_rules() -> None:
    """Install the Blue Joker large-deck rules on the migrated strategy catalogue.

    Blue Joker alone is Silver evidence. It becomes Gold only when the public
    roster also contains Marble Joker or Certificate. Certificate and Marble are
    Silver support components, while playing-card destruction is Banned because it
    permanently reduces Blue Joker's cards-remaining chip source.
    """
    from games.balatro import strategy_conditional_relationships as relationships
    from games.balatro import strategy_tree_catalog as catalog

    definition = catalog.TREE_MIGRATED_UNIVERSAL_BALATRO_STRATEGIES.get(
        BLUE_JOKER_STRATEGY_ID
    )
    if definition is None:
        return

    blue_aliases = _with_joker_aliases(frozenset({_BLUE_JOKER}))
    support_aliases = _with_joker_aliases(_DECK_GROWTH_PARTNERS)
    ban_aliases = _with_joker_aliases(_BLUE_JOKER_ROUTE_BANS)
    updated = replace(
        definition,
        gold_jokers=frozenset(definition.gold_jokers - blue_aliases),
        silver_jokers=frozenset(
            (definition.silver_jokers | blue_aliases | support_aliases) - ban_aliases
        ),
        banned_jokers=frozenset(definition.banned_jokers | ban_aliases),
    )

    # Keep the private construction dictionary and exported immutable view aligned;
    # consumers created after package import therefore all see the same definition.
    catalog._tree_definitions[BLUE_JOKER_STRATEGY_ID] = updated
    exported = dict(catalog.TREE_MIGRATED_UNIVERSAL_BALATRO_STRATEGIES)
    exported[BLUE_JOKER_STRATEGY_ID] = updated
    catalog.TREE_MIGRATED_UNIVERSAL_BALATRO_STRATEGIES = MappingProxyType(exported)

    original = relationships.conditional_joker_relationship
    if getattr(original, "_blue_joker_rules_installed", False):
        return

    def conditional_joker_relationship(state, strategy_id: str, item: object) -> str:
        if strategy_id == BLUE_JOKER_STRATEGY_ID:
            token = _item_token(item)
            if token in _BLUE_JOKER_ROUTE_BANS:
                return BANNED
            if token == _BLUE_JOKER:
                partnered = bool(_owned_joker_tokens(state) & _DECK_GROWTH_PARTNERS)
                return GOLD if partnered else SILVER
            if token in _DECK_GROWTH_PARTNERS:
                return SILVER
        return original(state, strategy_id, item)

    conditional_joker_relationship._blue_joker_rules_installed = True
    relationships.conditional_joker_relationship = conditional_joker_relationship
