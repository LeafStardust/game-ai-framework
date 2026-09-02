from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond


def _dev(bond_id):
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=True,
        contribution=22.0,
        rank=BondRank.R4,
        next_rank_threshold=30.0,
        contributions=(),
        realization=BondRealization.PARTIAL,
    )


def _j(name, **kwargs):
    return SimpleNamespace(name=name, **kwargs)


def _c(rank="7", suit="Hearts", enhancement="", seal="", debuffed=False, **kwargs):
    return SimpleNamespace(
        rank=rank,
        suit=suit,
        enhancement=enhancement,
        seal=seal,
        debuffed=debuffed,
        **kwargs,
    )


def test_ceremonial_dagger_accepts_any_destroyable_joker_immediately_right():
    state = SimpleNamespace(jokers=[_j("Ceremonial Dagger"), _j("Joker")], blind_selection_pending=True)
    assert realize_bond(_dev("joker_sacrifice"), state).realization == BondRealization.ACTIVE


def test_ceremonial_dagger_cannot_realize_from_eternal_joker_immediately_right():
    state = SimpleNamespace(jokers=[_j("Ceremonial Dagger"), _j("Joker", eternal=True)], blind_selection_pending=True)
    assert realize_bond(_dev("joker_sacrifice"), state).realization == BondRealization.PARTIAL


def test_castle_accepts_wild_card_as_current_target_suit():
    wild = _c(rank="4", suit="Hearts", enhancement="Wild")
    state = SimpleNamespace(jokers=[_j("Castle")], discarded_cards=[wild], castle_suit="Spades")
    assert realize_bond(_dev("discard"), state).realization == BondRealization.ACTIVE


def test_hit_the_road_ignores_debuffed_discarded_jack():
    state = SimpleNamespace(jokers=[_j("Hit the Road")], discarded_cards=[_c(rank="J", debuffed=True)])
    assert realize_bond(_dev("discard"), state).realization == BondRealization.PARTIAL


def test_eight_ball_ignores_debuffed_scoring_eight():
    state = SimpleNamespace(jokers=[_j("8 Ball")], scoring_cards=[_c(rank="8", debuffed=True)])
    assert realize_bond(_dev("tarot"), state).realization == BondRealization.PARTIAL


def test_blue_seal_does_not_trigger_while_held_card_is_debuffed():
    state = SimpleNamespace(jokers=[], hand=[_c(seal="Blue", debuffed=True)], round_end_pending=True, hands_left=0)
    assert realize_bond(_dev("planet"), state).realization == BondRealization.PARTIAL


def test_scholar_ignores_debuffed_scoring_ace():
    state = SimpleNamespace(jokers=[_j("Scholar")], scoring_cards=[_c(rank="A", debuffed=True)])
    assert realize_bond(_dev("aces"), state).realization == BondRealization.PARTIAL


def test_suit_payoff_ignores_debuffed_scoring_card():
    state = SimpleNamespace(jokers=[_j("Lusty Joker")], scoring_cards=[_c(suit="Hearts", debuffed=True)])
    assert realize_bond(_dev("hearts"), state).realization == BondRealization.PARTIAL


def test_lucky_payoff_ignores_debuffed_lucky_card():
    state = SimpleNamespace(jokers=[_j("Lucky Cat")], scoring_cards=[_c(enhancement="Lucky", debuffed=True)])
    assert realize_bond(_dev("lucky"), state).realization == BondRealization.PARTIAL


def test_baron_ignores_debuffed_held_king():
    state = SimpleNamespace(jokers=[_j("Baron")], hand=[_c(rank="K", debuffed=True)])
    assert realize_bond(_dev("kings"), state).realization == BondRealization.PARTIAL


def test_steel_held_effect_is_disabled_on_debuffed_card():
    state = SimpleNamespace(jokers=[], hand=[_c(enhancement="Steel", debuffed=True)])
    assert realize_bond(_dev("steel"), state).realization == BondRealization.PARTIAL


def test_hack_retrigger_ignores_debuffed_low_rank():
    state = SimpleNamespace(jokers=[_j("Hack")], scoring_cards=[_c(rank="4", debuffed=True)])
    assert realize_bond(_dev("played_retrigger"), state).realization == BondRealization.PARTIAL


def test_hanging_chad_has_no_realized_payoff_on_debuffed_first_scoring_card():
    state = SimpleNamespace(jokers=[_j("Hanging Chad")], scoring_cards=[_c(rank="7", debuffed=True)])
    assert realize_bond(_dev("played_retrigger"), state).realization == BondRealization.PARTIAL


def test_sixth_sense_ignores_debuffed_single_six():
    six = _c(rank="6", debuffed=True)
    state = SimpleNamespace(jokers=[_j("Sixth Sense")], cards_to_play=[six], first_hand_available=True)
    assert realize_bond(_dev("card_destruction"), state).realization == BondRealization.PARTIAL


def test_glass_joker_ignores_debuffed_scoring_glass_card():
    glass = _c(enhancement="Glass", debuffed=True)
    state = SimpleNamespace(jokers=[_j("Glass Joker")], scoring_cards=[glass])
    assert realize_bond(_dev("card_destruction"), state).realization == BondRealization.PARTIAL


def test_enhancement_consumption_remains_a_live_run_axis_with_owned_feedstock():
    enhanced = _c(enhancement="Bonus", debuffed=True)
    state = SimpleNamespace(
        jokers=[_j("Vampire")],
        scoring_cards=[enhanced],
        hand=[enhanced],
        owned_deck=[enhanced],
    )
    # Debuff state controls the immediate Vampire trigger in tactical mechanics;
    # it does not erase the run-level enhancement-consumption structure.
    assert realize_bond(_dev("enhancement_consumption"), state).realization == BondRealization.ACTIVE
