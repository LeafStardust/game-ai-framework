from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.relationships import BondRelationship, relationship_between
from games.balatro.joker_policy import _bond_transition_bonus
from games.balatro.jokers.burnt_joker import BurntJoker
from games.balatro.jokers.green_joker import GreenJoker
from games.balatro.jokers.ramen import RamenJoker
from games.balatro.state import BalatroState


def _state(*jokers):
    state = BalatroState()
    state.jokers = list(jokers)
    state.owned_deck = list(state.deck)
    return state


def test_burnt_and_no_discard_are_explicitly_conflicting_axes():
    assert relationship_between("burnt", "no_discard") == BondRelationship.CONFLICT

    _, composition = evaluate_bond_composition(_state(GreenJoker(), BurntJoker()))

    selected = set(composition.bond_ids)
    assert not {"burnt", "no_discard"}.issubset(selected)
    assert any(
        set(conflict) == {"burnt", "no_discard"}
        for conflict in composition.conflicts
    )


def test_selected_no_discard_strategy_rewards_reinforcement_not_conflicting_burnt_axis():
    state = _state(GreenJoker())
    developments, composition = evaluate_bond_composition(state)
    no_discard = next(dev for dev in developments if dev.bond_id == "no_discard")

    assert no_discard.unlocked
    assert "no_discard" in composition.bond_ids
    assert "burnt" not in composition.bond_ids

    aligned_value, aligned_notes = _bond_transition_bonus(state, RamenJoker())
    conflicting_value, conflicting_notes = _bond_transition_bonus(state, BurntJoker())

    # Ramen deepens the already-selected zero-discard engine. Burnt creates a real
    # developed Bond too, but that Bond is explicitly incompatible with the current
    # no-discard direction and must not be rewarded merely for developing.
    assert aligned_value > 0.0
    assert any("no_discard" in note for note in aligned_notes)
    assert conflicting_value < aligned_value
    assert conflicting_value <= 0.0
    assert any("burnt" in note for note in conflicting_notes)

    projected = _state(GreenJoker(), BurntJoker())
    _, projected_composition = evaluate_bond_composition(projected)
    assert not {"burnt", "no_discard"}.issubset(set(projected_composition.bond_ids))
    assert any(
        set(conflict) == {"burnt", "no_discard"}
        for conflict in projected_composition.conflicts
    )
