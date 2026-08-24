from games.balatro.bonds.model import MechanicalRole
from games.balatro.bonds.strategy_semantics import _Evidence, _semantic_relation


def _evidence(*, bond_id: str, source: str, role: MechanicalRole, target: str):
    return _Evidence(
        bond_id=bond_id,
        source=source,
        value=4.0,
        roles=(role,),
        targets=(target,),
    )


def test_shared_target_without_compatible_roles_does_not_form_semantic_link():
    left = _evidence(
        bond_id="kings",
        source="King payoff A",
        role=MechanicalRole.RANK_PAYOFF,
        target="KINGS",
    )
    right = _evidence(
        bond_id="held_cards",
        source="King payoff B",
        role=MechanicalRole.HELD_RANK_PAYOFF,
        target="KINGS",
    )

    assert _semantic_relation(left, right) is None


def test_explicit_compatible_roles_form_semantic_link_without_shared_target():
    payoff = _evidence(
        bond_id="held_cards",
        source="Baron",
        role=MechanicalRole.HELD_RANK_PAYOFF,
        target="KINGS",
    )
    retrigger = _evidence(
        bond_id="held_retrigger",
        source="Mime",
        role=MechanicalRole.HELD_RETRIGGER,
        target="HELD_CARD_EFFECTS",
    )

    assert _semantic_relation(payoff, retrigger) == "RETRIGGER_AMPLIFIES_HELD_PAYOFF"
