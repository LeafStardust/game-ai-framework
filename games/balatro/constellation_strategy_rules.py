from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType

from games.balatro.strategy import GOLD, NEUTRAL, SILVER


_CONSTELLATION = "constellationjoker"
_ASTRONOMER = "astronomerjoker"
_SATELLITE = "satellitejoker"
_PLANET_STRATEGY_IDS = (
    "planet_constellation",
    "planet_satellite",
    "planet_constellation_satellite",
)
_UNSUPPORTED_ACQUISITION_VALUE = -1000.0


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


def constellation_partner_tier(state) -> str:
    """Return Constellation's relationship from currently owned planet engines."""
    owned = _owned_joker_tokens(state)
    if _SATELLITE in owned:
        return GOLD
    if _ASTRONOMER in owned:
        return SILVER
    return NEUTRAL


def apply_constellation_strategy_rules() -> None:
    """Make Constellation a dependent planet-engine payoff, never a route starter.

    Constellation by itself should not seed or justify a planet strategy. It becomes
    useful only after the run already owns Astronomer (free Planet acquisition) or
    Satellite (a committed Planet-economy partner). Satellite is the stronger pair
    and therefore upgrades candidate Constellation to Gold; Astronomer makes it
    Silver support. Without either partner, ordinary Joker scoring is also blocked
    from buying Constellation as a generic speculative pickup.
    """
    from games.balatro import strategy_conditional_relationships as relationships
    from games.balatro import strategy_tree_catalog as catalog
    from games.balatro.strategy_value import StrategyAwareJokerBuildValueEvaluator

    constellation_aliases = _with_joker_aliases(frozenset({_CONSTELLATION}))
    exported = dict(catalog.TREE_MIGRATED_UNIVERSAL_BALATRO_STRATEGIES)

    for strategy_id in _PLANET_STRATEGY_IDS:
        definition = exported.get(strategy_id)
        if definition is None:
            continue
        updated = replace(
            definition,
            gold_jokers=frozenset(definition.gold_jokers - constellation_aliases),
            silver_jokers=frozenset(definition.silver_jokers - constellation_aliases),
            bronze_jokers=frozenset(definition.bronze_jokers - constellation_aliases),
        )
        catalog._tree_definitions[strategy_id] = updated
        exported[strategy_id] = updated

    catalog.TREE_MIGRATED_UNIVERSAL_BALATRO_STRATEGIES = MappingProxyType(exported)

    # strategy_catalog_guard can be imported before this installer runs because
    # games.balatro.__init__ imports all policies before invoking installers. Keep
    # the guarded runtime catalogue synchronized as well; otherwise Constellation
    # can remain static Gold there even though the tree catalogue was corrected.
    try:
        from games.balatro import strategy_catalog_guard as guard
    except ImportError:
        guard = None
    if guard is not None:
        guarded = dict(guard.RUNTIME_UNIVERSAL_BALATRO_STRATEGIES)
        for strategy_id in _PLANET_STRATEGY_IDS:
            definition = guarded.get(strategy_id)
            if definition is None:
                continue
            guarded[strategy_id] = replace(
                definition,
                gold_jokers=frozenset(definition.gold_jokers - constellation_aliases),
                silver_jokers=frozenset(definition.silver_jokers - constellation_aliases),
                bronze_jokers=frozenset(definition.bronze_jokers - constellation_aliases),
            )
        guard.RUNTIME_UNIVERSAL_BALATRO_STRATEGIES = MappingProxyType(guarded)

    original = relationships.conditional_joker_relationship
    if not getattr(original, "_constellation_rules_installed", False):
        def conditional_joker_relationship(state, strategy_id: str, item: object) -> str:
            if strategy_id in _PLANET_STRATEGY_IDS and _item_token(item) == _CONSTELLATION:
                return constellation_partner_tier(state)
            return original(state, strategy_id, item)

        conditional_joker_relationship._constellation_rules_installed = True
        relationships.conditional_joker_relationship = conditional_joker_relationship

    original_evaluate = StrategyAwareJokerBuildValueEvaluator.evaluate
    if getattr(original_evaluate, "_constellation_acquisition_gate_installed", False):
        return

    def evaluate(self, state, joker):
        result = original_evaluate(self, state, joker)
        if _item_token(joker) != _CONSTELLATION:
            return result
        if constellation_partner_tier(state) != NEUTRAL:
            return result

        delta = _UNSUPPORTED_ACQUISITION_VALUE - float(result.total_gain)
        return replace(
            result,
            total_gain=_UNSUPPORTED_ACQUISITION_VALUE,
            strategic_adjustment=float(result.strategic_adjustment) + delta,
            rationale=(
                *result.rationale,
                "Constellation acquisition blocked without owned Astronomer or Satellite",
                "Constellation is a dependent Planet payoff, not a standalone route starter",
            ),
        )

    evaluate._constellation_acquisition_gate_installed = True
    StrategyAwareJokerBuildValueEvaluator.evaluate = evaluate
