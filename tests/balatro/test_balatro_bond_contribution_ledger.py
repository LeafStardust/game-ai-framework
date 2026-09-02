from types import SimpleNamespace

from games.balatro.bonds.contributions import (
    component_contribution,
    finalize_development,
    normalize_contributions,
)
from games.balatro.bonds.held_cards import evaluate_held_cards_bond
from games.balatro.bonds.mechanical_core import (
    DECK_THINNING_THRESHOLDS,
    evaluate_deck_thinning_bond,
    evaluate_steel_bond,
)
from games.balatro.bonds.model import BondRank
from games.balatro.mechanics import (
    CARD_DESTRUCTION,
    DECK_THIN_PAYOFF,
    HELD_KING_XMULT,
    HELD_QUEEN_MULT,
    STEEL_CARD_PAYOFF,
)


def _component(*mechanics):
    return SimpleNamespace(name="arbitrary-component", mechanics=frozenset(mechanics))


def _card(*, enhancement="", seal=""):
    return SimpleNamespace(rank="7", suit="Hearts", enhancement=enhancement, seal=seal)


def _neutral_deck():
    return tuple(_card() for _ in range(52))


def _state(*, jokers=(), deck=None, hand_size=8):
    resolved_deck = _neutral_deck() if deck is None else tuple(deck)
    return SimpleNamespace(
        jokers=list(jokers),
        owned_deck=list(resolved_deck),
        deck=list(resolved_deck),
        deck_name="Red Deck",
        hand_size=hand_size,
    )


def test_same_component_source_is_not_double_counted_within_one_bond():
    source = _component(DECK_THIN_PAYOFF, CARD_DESTRUCTION)
    development = evaluate_deck_thinning_bond(_state(jokers=(source,)))

    # The same Joker supports Deck Thinning through two descriptors (7 and 5),
    # but it is one underlying source and therefore contributes only once.
    assert development.contribution == 7.0
    assert len(development.contributions) == 1
    contribution = development.contributions[0]
    assert contribution.source_id == "jokers:slot:0"
    assert contribution.value == 7.0
    assert "mechanic:deck_thin_payoff" in contribution.conditions
    assert "mechanic:card_destruction" in contribution.conditions


def test_one_component_source_may_contribute_to_multiple_bonds():
    source = _component(DECK_THIN_PAYOFF, STEEL_CARD_PAYOFF)
    state = _state(jokers=(source,))

    thinning = evaluate_deck_thinning_bond(state)
    steel = evaluate_steel_bond(state)

    assert thinning.contribution == 7.0
    assert steel.contribution == 5.0
    assert thinning.contributions[0].source_id == "jokers:slot:0"
    assert steel.contributions[0].source_id == "jokers:slot:0"
    assert thinning.contributions[0].mechanic == DECK_THIN_PAYOFF
    assert steel.contributions[0].mechanic == STEEL_CARD_PAYOFF


def test_canonical_state_evidence_has_diagnostic_source_identity():
    state = _state(deck=tuple(_card(enhancement="Steel", seal="Red") for _ in range(4)))
    development = evaluate_steel_bond(state)

    source_ids = {item.source_id for item in development.contributions}
    assert "state:deck:steel_density" in source_ids
    assert "state:deck:red_steel_density" in source_ids


def test_held_cards_uses_component_and_state_ledger_sources():
    state = _state(
        jokers=(_component(HELD_KING_XMULT), _component(HELD_QUEEN_MULT)),
        deck=tuple(_card(enhancement="Steel") for _ in range(6)),
        hand_size=10,
    )
    development = evaluate_held_cards_bond(state)

    assert development.contribution == 19.0
    source_ids = {item.source_id for item in development.contributions}
    assert "jokers:slot:0" in source_ids
    assert "jokers:slot:1" in source_ids
    assert "state:deck:steel_held_density" in source_ids
    assert "state:hand:extra_size" in source_ids


def test_held_cards_snapshot_compatibility_is_isolated_for_remaining_holdouts():
    state = _state(jokers=("raisedfistjoker", "blackboardjoker"))
    development = evaluate_held_cards_bond(state)

    assert development.contribution == 6.0
    assert {item.source_id for item in development.contributions} == {
        "jokers:slot:0",
        "jokers:slot:1",
    }


def test_normalization_preserves_legacy_entries_during_incremental_migration():
    legacy = component_contribution(
        _component(DECK_THIN_PAYOFF),
        collection="jokers",
        index=0,
        label="canonical",
        value=7.0,
        mechanic=DECK_THIN_PAYOFF,
    )
    duplicate = component_contribution(
        _component(CARD_DESTRUCTION),
        collection="jokers",
        index=0,
        label="same source",
        value=5.0,
        mechanic=CARD_DESTRUCTION,
    )
    normalized = normalize_contributions((legacy, duplicate))
    assert len(normalized) == 1
    assert normalized[0].value == 7.0


def test_finalize_development_ranks_after_source_normalization():
    source = _component(DECK_THIN_PAYOFF)
    parts = (
        component_contribution(
            source,
            collection="jokers",
            index=0,
            label="strong",
            value=7.0,
            mechanic=DECK_THIN_PAYOFF,
        ),
        component_contribution(
            source,
            collection="jokers",
            index=0,
            label="weak duplicate",
            value=5.0,
            mechanic=CARD_DESTRUCTION,
        ),
    )
    development = finalize_development("deck_thinning", parts, DECK_THINNING_THRESHOLDS)
    assert development.contribution == 7.0
    assert development.rank == BondRank.R2
