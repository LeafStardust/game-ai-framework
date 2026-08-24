from types import SimpleNamespace

from games.balatro.bond_pivot_authority import _forming_core_replacement_veto
from games.balatro.bonds.strategy_semantics import StrategyCommitment


class BurntJoker:
    pass


class SpaceJoker:
    pass


def _plan(strategy_id, *, commitment, strength, core_sources):
    return SimpleNamespace(
        strategy_id=strategy_id,
        commitment=commitment,
        strength=strength,
        core_sources=tuple(core_sources),
    )


def _composition(plan):
    return SimpleNamespace(strategy_plan=plan)


def test_forming_core_cannot_be_sold_into_no_strategy():
    current = _composition(
        _plan(
            "burnt_target_level",
            commitment=StrategyCommitment.FORMING,
            strength=8.0,
            core_sources=("Burnt Joker",),
        )
    )
    projected = _composition(None)

    veto, notes = _forming_core_replacement_veto(current, projected, BurntJoker())

    assert veto
    assert any("forming strategy core retention veto" in note for note in notes)


def test_noncore_joker_is_not_protected_by_forming_plan():
    current = _composition(
        _plan(
            "burnt_target_level",
            commitment=StrategyCommitment.FORMING,
            strength=8.0,
            core_sources=("Burnt Joker",),
        )
    )

    veto, _ = _forming_core_replacement_veto(current, _composition(None), SpaceJoker())

    assert not veto


def test_same_forming_strategy_may_replace_support_piece():
    current_plan = _plan(
        "burnt_target_level",
        commitment=StrategyCommitment.FORMING,
        strength=8.0,
        core_sources=("Burnt Joker",),
    )
    projected_plan = _plan(
        "burnt_target_level",
        commitment=StrategyCommitment.FORMING,
        strength=8.5,
        core_sources=("Burnt Joker", "Space Joker"),
    )

    veto, _ = _forming_core_replacement_veto(
        _composition(current_plan),
        _composition(projected_plan),
        BurntJoker(),
    )

    assert not veto


def test_materially_stronger_pinned_strategy_can_override_forming_core_retention():
    current = _composition(
        _plan(
            "burnt_target_level",
            commitment=StrategyCommitment.FORMING,
            strength=6.0,
            core_sources=("Burnt Joker",),
        )
    )
    projected = _composition(
        _plan(
            "baron_mime_steel",
            commitment=StrategyCommitment.PINNED,
            strength=8.0,
            core_sources=("Baron", "Mime"),
        )
    )

    veto, _ = _forming_core_replacement_veto(current, projected, BurntJoker())

    assert not veto
