from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization_engine import (
    realize_burnt, realize_cash, realize_discard, realize_enhanced_cards,
    realize_hand_repetition, realize_sell_value, realize_vampire,
)


def dev(bond_id, rank=BondRank.R3, target=None):
    return BondDevelopment(bond_id=bond_id, unlocked=True, contribution=15.0, rank=rank,
                           next_rank_threshold=20.0, contributions=(), target=target,
                           realization=BondRealization.PARTIAL)

def joker(name): return SimpleNamespace(name=name)
def card(*, enhancement="", rank=""): return SimpleNamespace(enhancement=enhancement, rank=rank)


def test_burnt_requires_current_first_discard_access():
    assert realize_burnt(dev("burnt", target="HIGH_CARD"), SimpleNamespace(discards_left=0)).realization == BondRealization.PARTIAL
    assert realize_burnt(dev("burnt", target="HIGH_CARD"), SimpleNamespace(discards_left=1)).realization == BondRealization.ACTIVE


def test_cash_payoff_requires_bankroll_but_income_engine_can_be_active():
    state = SimpleNamespace(jokers=[joker("Bull")], money=5)
    assert realize_cash(dev("cash"), state).realization == BondRealization.PARTIAL
    state = SimpleNamespace(jokers=[joker("Bull")], money=50)
    assert realize_cash(dev("cash"), state).realization == BondRealization.ACTIVE
    state = SimpleNamespace(jokers=[joker("Cloud 9")], money=0)
    assert realize_cash(dev("cash"), state).realization == BondRealization.ACTIVE


def test_discard_needs_discard_resource_now():
    state = SimpleNamespace(jokers=[joker("Yorick")], discards_left=0)
    assert realize_discard(dev("discard"), state).realization == BondRealization.PARTIAL
    state.discards_left = 2
    assert realize_discard(dev("discard"), state).realization == BondRealization.ACTIVE


def test_sell_value_needs_actual_sell_value():
    state = SimpleNamespace(jokers=[joker("Swashbuckler")], joker_sell_value_total=0)
    assert realize_sell_value(dev("sell_value"), state).realization == BondRealization.PARTIAL
    state.joker_sell_value_total = 25
    assert realize_sell_value(dev("sell_value"), state).realization == BondRealization.ACTIVE


def test_hand_repetition_cardsharp_uses_any_prior_same_hand_this_round():
    state = SimpleNamespace(jokers=[joker("Card Sharp")], current_hand_type="PAIR", previous_hand_type="HIGH_CARD", hand_play_counts={"PAIR": 4})
    assert realize_hand_repetition(dev("hand_repetition"), state).realization == BondRealization.ACTIVE
    state.hand_play_counts = {"HIGH_CARD": 4}
    assert realize_hand_repetition(dev("hand_repetition"), state).realization == BondRealization.PARTIAL


def test_drivers_license_requires_threshold_to_realize():
    state = SimpleNamespace(jokers=[joker("Driver's License")], owned_deck=[card(enhancement="Gold") for _ in range(15)])
    assert realize_enhanced_cards(dev("enhanced_cards"), state).realization == BondRealization.PARTIAL
    state.owned_deck.append(card(enhancement="Mult"))
    assert realize_enhanced_cards(dev("enhanced_cards"), state).realization == BondRealization.ACTIVE


def test_vampire_requires_current_or_renewable_feed():
    state = SimpleNamespace(jokers=[joker("Vampire")], hand=[card()], vampire_enhancements_consumed=8)
    assert realize_vampire(dev("vampire"), state).realization == BondRealization.PARTIAL
    state.hand=[card(enhancement="Gold")]
    assert realize_vampire(dev("vampire"), state).realization == BondRealization.ACTIVE
