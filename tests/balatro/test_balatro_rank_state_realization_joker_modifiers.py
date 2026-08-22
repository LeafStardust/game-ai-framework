from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond


def _joker(name): return SimpleNamespace(name=name)
def _card(rank="2", suit="Hearts", enhancement=""): return SimpleNamespace(rank=rank,suit=suit,enhancement=enhancement,is_stone=False)
def _dev(bond_id): return BondDevelopment(bond_id=bond_id,unlocked=True,contribution=10.0,rank=BondRank.R2,next_rank_threshold=15.0,contributions=(),realization=BondRealization.PARTIAL)


def test_pareidolia_realizes_face_cards_on_nonface_play():
    state=SimpleNamespace(jokers=[_joker("Pareidolia")],scoring_cards=[_card("2"),_card("7")])
    assert realize_bond(_dev("face_cards"),state).realization==BondRealization.ACTIVE


def test_pareidolia_blocks_ride_the_bus_no_face_realization():
    state=SimpleNamespace(jokers=[_joker("Ride the Bus"),_joker("Pareidolia")],scoring_cards=[_card("2"),_card("7")],ride_the_bus_streak=10)
    assert realize_bond(_dev("no_face_cards"),state).realization==BondRealization.PARTIAL


def test_smeared_allows_diamond_to_realize_hearts_payoff():
    state=SimpleNamespace(jokers=[_joker("Smeared Joker"),_joker("Bloodstone")],scoring_cards=[_card("9","Diamonds")])
    assert realize_bond(_dev("hearts"),state).realization==BondRealization.ACTIVE


def test_golden_ticket_realizes_when_gold_card_is_played():
    state=SimpleNamespace(jokers=[_joker("Golden Ticket")],scoring_cards=[_card("9","Hearts","Gold")],hand=[])
    assert realize_bond(_dev("gold_economy"),state).realization==BondRealization.ACTIVE


def test_midas_mask_realizes_gold_engine_when_face_is_played():
    state=SimpleNamespace(jokers=[_joker("Midas Mask")],scoring_cards=[_card("K")],hand=[])
    assert realize_bond(_dev("gold_economy"),state).realization==BondRealization.ACTIVE


def test_reserved_parking_realizes_from_held_face_card():
    state=SimpleNamespace(jokers=[_joker("Reserved Parking")],scoring_cards=[],hand=[_card("Q")])
    assert realize_bond(_dev("gold_economy"),state).realization==BondRealization.ACTIVE
