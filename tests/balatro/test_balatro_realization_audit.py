from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import FROZEN_BOND_IDS, REALIZERS, extra_realizers, missing_realizers, realize_bond


def test_every_frozen_bond_has_exactly_one_realizer():
    assert len(FROZEN_BOND_IDS) == 46
    assert len(set(FROZEN_BOND_IDS)) == 46
    assert missing_realizers() == ()
    assert extra_realizers() == ()
    assert len(REALIZERS) == 46


def test_unified_realizer_preserves_rank_and_contribution():
    # Representative passive state exercises the invariant wrapper across every
    # registered Bond without requiring each mechanical trigger to be active.
    state = SimpleNamespace(
        jokers=[], hand=[], current_hand=[], cards_in_hand=[], owned_deck=[], deck=[],
        money=0, hand_levels={}, vouchers=[], consumables=[], discards_left=0,
        discards_remaining=0, discards_used_this_round=0, blinds_skipped=0,
        joker_sell_value_total=0, jokers_destroyed=0, cards_destroyed=0,
        hand_play_counts={}, vampire_enhancements_consumed=0,
    )
    for bond_id in FROZEN_BOND_IDS:
        dev = BondDevelopment(
            bond_id=bond_id,
            unlocked=True,
            contribution=10.0,
            rank=BondRank.R2,
            next_rank_threshold=15.0,
            contributions=(),
            realization=BondRealization.PARTIAL,
        )
        out = realize_bond(dev, state)
        assert out.rank == BondRank.R2
        assert out.contribution == 10.0
        assert out.realization in set(BondRealization)


def _intrinsic_dev(bond_id: str) -> BondDevelopment:
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=True,
        contribution=10.0,
        rank=BondRank.R2,
        next_rank_threshold=15.0,
        contributions=(),
        realization=BondRealization.PARTIAL,
    )


def test_intrinsic_card_effects_realize_without_joker_payoff():
    # Lucky, Glass and Stone cards have intrinsic live effects. Their dedicated
    # payoff Jokers may deepen/mature the Bond but must not gate ACTIVE status.
    cases = (
        ("lucky", SimpleNamespace(enhancement="Lucky", rank="7", suit="Hearts")),
        ("glass", SimpleNamespace(enhancement="Glass", rank="8", suit="Clubs")),
        ("stone", SimpleNamespace(enhancement="Stone", is_stone=True, rank="", suit="")),
    )
    for bond_id, card in cases:
        state = SimpleNamespace(
            jokers=[], scoring_cards=[card], played_cards=[], current_played_cards=[],
            hand=[], current_hand=[], cards_in_hand=[],
        )
        out = realize_bond(_intrinsic_dev(bond_id), state)
        assert out.realization == BondRealization.ACTIVE
