from types import SimpleNamespace

from games.balatro.bonds.burnt import evaluate_hand_leveling_bond
from games.balatro.bonds.gold_cards import evaluate_gold_cards_bond
from games.balatro.bonds.mechanical_core import (
    evaluate_deck_thinning_bond,
    evaluate_held_retrigger_bond,
    evaluate_steel_bond,
)
from games.balatro.bonds.mechanical_engines import (
    evaluate_blind_skip_bond,
    evaluate_card_destruction_bond,
    evaluate_discard_bond,
    evaluate_enhanced_cards_bond,
    evaluate_hand_repetition_bond,
    evaluate_joker_sacrifice_bond,
    evaluate_sell_value_bond,
)
from games.balatro.bonds.mechanical_rank_consumables import (
    evaluate_jacks_bond,
    evaluate_kings_bond,
    evaluate_planet_bond,
    evaluate_queens_bond,
    evaluate_tarot_bond,
)
from games.balatro.bonds.model import BondRealization
from games.balatro.bonds.realization import realize_bond
from games.balatro.bonds.vampire import evaluate_enhancement_consumption_bond
from games.balatro.jokers.burnt_joker import BurntJoker
from games.balatro.jokers.erosion import ErosionJoker
from games.balatro.jokers.midas_mask import MidasMaskJoker
from games.balatro.jokers.mime import MimeJoker
from games.balatro.jokers.sixth_sense import SixthSenseJoker
from games.balatro.jokers.space_joker import SpaceJoker
from games.balatro.jokers.steel_joker import SteelJoker
from games.balatro.jokers.trading_card import TradingCardJoker
from games.balatro.mechanics import (
    ALL_CARDS_FACE,
    BLIND_SKIP_SCALING,
    BLIND_SKIP_TAG_GENERATION,
    CARD_DESTRUCTION,
    DECK_THIN_PAYOFF,
    DISCARD_FACE_ECONOMY,
    DISCARD_HAND_LEVELING,
    DISCARD_JACK_XMULT,
    DISCARD_SCALING,
    ENHANCEMENT_CONSUMPTION,
    ENHANCEMENT_DENSITY_PAYOFF,
    ENHANCEMENT_FEED_ACCESS,
    ENHANCEMENT_GENERATION,
    FACE_DESTRUCTION_SCALING,
    GLOBAL_SELL_VALUE_GROWTH,
    GOLD_CARD_GENERATION,
    GOLD_CARD_SCORING_ECONOMY,
    HAND_LEVEL_COPY,
    HAND_REPETITION_SCALING,
    HAND_REPETITION_XMULT,
    HELD_KING_XMULT,
    HELD_QUEEN_MULT,
    JOKER_FODDER_GENERATION,
    LEFT_JOKER_SACRIFICE,
    PLANET_GENERATION,
    PLANET_PACK_TARGETING,
    PLANET_SCALING,
    PLANET_SHOP_ACCESS_MAJOR,
    PLAYED_KING_QUEEN_XMULT,
    PROBABILISTIC_HAND_LEVELING,
    RETRIGGER_HELD_CARDS,
    SELF_SELL_VALUE_GROWTH,
    SELL_VALUE_SCORING,
    SPECTRAL_GENERATION,
    STEEL_CARD_PAYOFF,
    TAROT_GENERATION,
    TAROT_LOW_MONEY_GENERATION,
    TAROT_PACK_GENERATION,
    TAROT_SCALING,
    TAROT_SHOP_ACCESS_MAJOR,
    component_mechanics,
)


def _component(*mechanics):
    return SimpleNamespace(name="arbitrary-component-name", mechanics=frozenset(mechanics))


def _card(rank="7", enhancement="", seal=""):
    return SimpleNamespace(rank=rank, suit="Hearts", enhancement=enhancement, seal=seal)


def _state(*, jokers=(), vouchers=(), deck=(), hand=(), hand_levels=None, **extra):
    data = dict(
        jokers=list(jokers),
        vouchers=list(vouchers),
        owned_deck=list(deck),
        deck=list(deck),
        deck_name="Red Deck",
        hand=list(hand),
        current_hand=list(hand),
        cards_in_hand=list(hand),
        hand_levels=dict(hand_levels or {}),
        hand_play_counts={},
        vampire_enhancements_consumed=0,
        discards_per_round=3,
        blinds_skipped=0,
        joker_sell_value_total=0,
        jokers_destroyed=0,
        cards_destroyed=0,
    )
    data.update(extra)
    return SimpleNamespace(**data)


def test_modeled_jokers_expose_native_mechanics():
    assert DISCARD_HAND_LEVELING in component_mechanics(BurntJoker())
    assert PROBABILISTIC_HAND_LEVELING in component_mechanics(SpaceJoker())
    assert GOLD_CARD_GENERATION in component_mechanics(MidasMaskJoker())
    assert RETRIGGER_HELD_CARDS in component_mechanics(MimeJoker())
    assert STEEL_CARD_PAYOFF in component_mechanics(SteelJoker())
    assert CARD_DESTRUCTION in component_mechanics(TradingCardJoker())
    assert DECK_THIN_PAYOFF in component_mechanics(ErosionJoker())
    assert {CARD_DESTRUCTION, SPECTRAL_GENERATION} <= component_mechanics(SixthSenseJoker())


def test_hand_leveling_uses_mechanics_not_component_display_names():
    state = _state(jokers=(_component(DISCARD_HAND_LEVELING), _component(HAND_LEVEL_COPY)))
    dev = evaluate_hand_leveling_bond(state)
    assert dev.bond_id == "hand_leveling"
    assert dev.contribution == 13.0


def test_gold_cards_uses_mechanics_not_component_display_names():
    state = _state(jokers=(_component(GOLD_CARD_GENERATION), _component(GOLD_CARD_SCORING_ECONOMY)))
    dev = evaluate_gold_cards_bond(state)
    assert dev.bond_id == "gold_cards"
    assert dev.contribution == 10.0


def test_enhancement_consumption_uses_mechanics_not_component_display_names():
    enhanced = _card(enhancement="Bonus")
    state = _state(
        jokers=(
            _component(ENHANCEMENT_CONSUMPTION),
            _component(ENHANCEMENT_FEED_ACCESS),
            _component(ALL_CARDS_FACE),
        ),
        deck=(enhanced,),
        hand=(enhanced,),
    )
    dev = evaluate_enhancement_consumption_bond(state)
    realized = realize_bond(dev, state)
    assert dev.bond_id == "enhancement_consumption"
    assert dev.contribution == 13.0
    assert realized.realization == BondRealization.ACTIVE


def test_held_retrigger_uses_mechanics_not_component_display_names():
    state = _state(jokers=(_component(RETRIGGER_HELD_CARDS), _component(HAND_LEVEL_COPY)))
    dev = evaluate_held_retrigger_bond(state)
    assert dev.bond_id == "held_retrigger"
    assert dev.contribution == 10.0


def test_steel_uses_mechanics_not_component_display_names():
    state = _state(
        jokers=(_component(STEEL_CARD_PAYOFF),),
        deck=(_card(enhancement="Steel"), _card(enhancement="Steel")),
    )
    dev = evaluate_steel_bond(state)
    assert dev.bond_id == "steel"
    assert dev.contribution == 8.0


def test_deck_thinning_uses_mechanics_not_component_display_names():
    deck = tuple(_card() for _ in range(44))
    state = _state(
        jokers=(
            _component(DECK_THIN_PAYOFF),
            _component(CARD_DESTRUCTION),
            _component(CARD_DESTRUCTION, SPECTRAL_GENERATION),
        ),
        deck=deck,
    )
    dev = evaluate_deck_thinning_bond(state)
    assert dev.bond_id == "deck_thinning"
    assert dev.contribution == 19.0


def test_discard_uses_mechanics_not_component_display_names():
    state = _state(
        jokers=(_component(DISCARD_SCALING), _component(DISCARD_FACE_ECONOMY)),
        discards_per_round=5,
    )
    dev = evaluate_discard_bond(state)
    assert dev.bond_id == "discard"
    assert dev.contribution == 13.0


def test_blind_skip_uses_mechanics_not_component_display_names():
    state = _state(
        jokers=(_component(BLIND_SKIP_SCALING), _component(BLIND_SKIP_TAG_GENERATION)),
        blinds_skipped=5,
    )
    dev = evaluate_blind_skip_bond(state)
    assert dev.bond_id == "blind_skip"
    assert dev.contribution == 16.0


def test_sell_value_uses_mechanics_not_component_display_names():
    state = _state(
        jokers=(
            _component(SELL_VALUE_SCORING),
            _component(GLOBAL_SELL_VALUE_GROWTH),
            _component(SELF_SELL_VALUE_GROWTH),
        ),
        joker_sell_value_total=35,
    )
    dev = evaluate_sell_value_bond(state)
    assert dev.bond_id == "sell_value"
    assert dev.contribution == 23.0


def test_joker_sacrifice_uses_mechanics_not_component_display_names():
    state = _state(
        jokers=(_component(LEFT_JOKER_SACRIFICE), _component(JOKER_FODDER_GENERATION)),
        jokers_destroyed=6,
    )
    dev = evaluate_joker_sacrifice_bond(state)
    assert dev.bond_id == "joker_sacrifice"
    assert dev.contribution == 15.0


def test_card_destruction_uses_mechanics_not_component_display_names():
    state = _state(
        jokers=(
            _component(FACE_DESTRUCTION_SCALING),
            _component(CARD_DESTRUCTION),
            _component(CARD_DESTRUCTION, SPECTRAL_GENERATION),
        ),
        cards_destroyed=10,
    )
    dev = evaluate_card_destruction_bond(state)
    assert dev.bond_id == "card_destruction"
    assert dev.contribution == 21.0


def test_hand_repetition_uses_mechanics_not_component_display_names():
    state = _state(
        jokers=(_component(HAND_REPETITION_XMULT), _component(HAND_REPETITION_SCALING)),
        hand_play_counts={"PAIR": 18},
    )
    dev = evaluate_hand_repetition_bond(state)
    assert dev.bond_id == "hand_repetition"
    assert dev.contribution == 18.0


def test_enhanced_cards_uses_mechanics_not_component_display_names():
    state = _state(
        jokers=(
            _component(ENHANCEMENT_DENSITY_PAYOFF),
            _component(ENHANCEMENT_GENERATION),
            _component(ENHANCEMENT_GENERATION),
        ),
        deck=tuple(_card(enhancement="Bonus") for _ in range(16)),
    )
    dev = evaluate_enhanced_cards_bond(state)
    assert dev.bond_id == "enhanced_cards"
    assert dev.contribution == 18.0


def test_rank_bonds_use_mechanics_not_component_display_names():
    kings = evaluate_kings_bond(_state(jokers=(_component(HELD_KING_XMULT), _component(PLAYED_KING_QUEEN_XMULT))))
    queens = evaluate_queens_bond(_state(jokers=(_component(HELD_QUEEN_MULT), _component(PLAYED_KING_QUEEN_XMULT))))
    jacks = evaluate_jacks_bond(_state(jokers=(_component(DISCARD_JACK_XMULT),)))
    assert kings.contribution == 13.0
    assert queens.contribution == 11.0
    assert jacks.contribution == 7.0


def test_tarot_uses_mechanics_not_component_display_names():
    state = _state(
        jokers=(
            _component(TAROT_GENERATION),
            _component(TAROT_LOW_MONEY_GENERATION),
            _component(TAROT_PACK_GENERATION),
            _component(TAROT_SCALING),
        ),
        vouchers=(_component(TAROT_SHOP_ACCESS_MAJOR),),
    )
    dev = evaluate_tarot_bond(state)
    assert dev.bond_id == "tarot"
    assert dev.contribution == 25.0


def test_planet_uses_mechanics_not_component_display_names():
    state = _state(
        jokers=(_component(PLANET_SCALING), _component(PLANET_GENERATION)),
        vouchers=(
            _component(PLANET_PACK_TARGETING),
            _component(PLANET_SHOP_ACCESS_MAJOR),
        ),
        deck=tuple(_card(seal="Blue") for _ in range(4)),
    )
    dev = evaluate_planet_bond(state)
    assert dev.bond_id == "planet"
    assert dev.contribution == 25.0
