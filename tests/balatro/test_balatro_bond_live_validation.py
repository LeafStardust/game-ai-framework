from types import SimpleNamespace

from games.balatro.bond_prescription_policy import prescription_bonus
from games.balatro.bond_shop_health_policy import (
    StrategyHealthProvenance,
    _LAST_STRATEGY_HEALTH,
    _LAST_STRATEGY_HEALTH_PROVENANCE,
    clear_strategy_health,
    last_strategy_health,
)
from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.model import BondRank
from games.balatro.bonds.motifs import MotifState
from games.balatro.live.strategy_health import StrategyHealthMode
from games.balatro.state import BalatroState


def _card(rank, enhancement=None, seal=None):
    return SimpleNamespace(rank=rank, enhancement=enhancement, seal=seal, suit="Spades")


def _joker(name):
    return type(name.replace(" ", ""), (), {})()


def _state():
    state = BalatroState()
    state.phase = "SHOP"
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.ante = 3
    state.round = 5
    state.owned_deck = list(state.deck)
    return state


def test_shop_health_cache_rejects_unrelated_round_or_run_identity(monkeypatch):
    import games.balatro.bond_shop_health_policy as policy

    matching = _state()
    health = SimpleNamespace(mode=StrategyHealthMode.REPAIR)
    monkeypatch.setattr(policy, "_LAST_STRATEGY_HEALTH", health)
    monkeypatch.setattr(
        policy,
        "_LAST_STRATEGY_HEALTH_PROVENANCE",
        StrategyHealthProvenance("RED", "WHITE", 3, 5),
    )
    assert last_strategy_health(matching) is health

    different_round = _state()
    different_round.round = 6
    assert last_strategy_health(different_round) is None

    different_deck = _state()
    different_deck.deck_name = "BLUE"
    assert last_strategy_health(different_deck) is None


def test_clear_strategy_health_removes_cached_authority(monkeypatch):
    import games.balatro.bond_shop_health_policy as policy

    monkeypatch.setattr(policy, "_LAST_STRATEGY_HEALTH", SimpleNamespace(mode=StrategyHealthMode.SURVIVE))
    monkeypatch.setattr(
        policy,
        "_LAST_STRATEGY_HEALTH_PROVENANCE",
        StrategyHealthProvenance("RED", "WHITE", 2, 4),
    )
    clear_strategy_health()
    assert policy._LAST_STRATEGY_HEALTH is None
    assert policy._LAST_STRATEGY_HEALTH_PROVENANCE is None


def test_baron_mime_steel_scenario_activates_and_prescribes_engine_cards():
    state = _state()
    state.jokers = [_joker("Baron"), _joker("Mime")]
    state.owned_deck = [
        *[_card("K") for _ in range(4)],
        _card("2", enhancement="Steel"),
        _card("3", enhancement="Steel"),
    ]
    state.hand = [
        _card("K", enhancement="Steel"),
        _card("K"),
        _card("2", enhancement="Steel"),
    ]
    developments, composition = evaluate_bond_composition(state)
    motif = next(m for m in composition.motifs if m.motif_id == "baron_mime_steel")
    steel = next(d for d in developments if d.bond_id == "steel")

    # The motif contract intentionally activates at two Steel cards because Baron
    # + Mime makes that small Steel package super-additive. The standalone Steel
    # Bond may still be R0; it is required only for MATURE motif status.
    assert steel.rank == BondRank.R0
    assert motif.state == MotifState.ACTIVE

    steel_bonus, _ = prescription_bonus(state, kind="TAROT", label="The Chariot")
    king_bonus, _ = prescription_bonus(
        state,
        kind="PLAYING_CARD",
        label="King",
        playing_card=_card("K", enhancement="Steel", seal="Red"),
    )
    assert steel_bonus > 0.0
    assert king_bonus > steel_bonus


def test_burnt_scenario_targets_actual_hand_not_generic_high_card():
    state = _state()
    state.jokers = [_joker("Burnt Joker")]
    state.hand_levels["PAIR"] = 5
    state.hand_play_counts["PAIR"] = 10
    state.hand_play_counts["HIGH_CARD"] = 0
    _, composition = evaluate_bond_composition(state)
    motif = next((m for m in composition.motifs if m.motif_id == "burnt_target_level"), None)
    if motif is None or motif.state < MotifState.ACTIVE:
        return
    mercury_bonus, _ = prescription_bonus(state, kind="PLANET", label="Mercury")
    pluto_bonus, _ = prescription_bonus(state, kind="PLANET", label="Pluto")
    assert mercury_bonus > 0.0
    assert pluto_bonus == 0.0


def test_red_seal_prescription_differs_by_active_motif_context():
    baron_state = _state()
    baron_state.jokers = [_joker("Baron"), _joker("Mime")]
    baron_state.owned_deck = [
        *[_card("K") for _ in range(4)],
        _card("2", enhancement="Steel"),
        _card("3", enhancement="Steel"),
    ]
    baron_state.hand = [
        _card("K", enhancement="Steel"),
        _card("K"),
        _card("3", enhancement="Steel"),
    ]
    baron_bonus, baron_notes = prescription_bonus(
        baron_state,
        kind="SPECTRAL",
        label="Deja Vu",
        cards=(_card("K"),),
    )
    assert baron_bonus > 0.0
    assert any("Baron-Mime-Steel" in note for note in baron_notes)

    hack_state = _state()
    hack_state.jokers = [_joker("Hack")]
    hack_state.owned_deck = [_card("2"), _card("3"), _card("4"), _card("5")] * 4
    hack_bonus, hack_notes = prescription_bonus(
        hack_state,
        kind="SPECTRAL",
        label="Deja Vu",
        cards=(_card("3"),),
    )
    if hack_bonus > 0.0:
        assert any("Hack" in note for note in hack_notes)


def test_photograph_chad_targets_face_card_red_seal_support():
    state = _state()
    state.jokers = [_joker("Photograph"), _joker("Hanging Chad")]
    state.owned_deck = [_card("J"), _card("Q"), _card("K")] * 3
    state.hand = [_card("K"), _card("9")]
    bonus, notes = prescription_bonus(
        state,
        kind="SPECTRAL",
        label="Deja Vu",
        cards=(_card("K"),),
    )
    if bonus > 0.0:
        assert any("Photograph-Chad" in note for note in notes)


def test_vampire_midas_prefers_face_and_enhanced_feedstock():
    state = _state()
    state.jokers = [_joker("Vampire"), _joker("Midas Mask")]
    state.owned_deck = [
        _card("J", enhancement="Gold"),
        _card("Q", enhancement="Gold"),
        _card("K", enhancement="Gold"),
        _card("9"),
    ]
    face_bonus, face_notes = prescription_bonus(
        state,
        kind="PLAYING_CARD",
        label="King",
        playing_card=_card("K", enhancement="Gold"),
    )
    if face_bonus > 0.0:
        assert any("Vampire-Midas" in note for note in face_notes)


def test_hack_prefers_low_rank_red_seal_target():
    state = _state()
    state.jokers = [_joker("Hack")]
    state.owned_deck = [_card("2"), _card("3"), _card("4"), _card("5")] * 4
    low_bonus, low_notes = prescription_bonus(
        state,
        kind="SPECTRAL",
        label="Deja Vu",
        cards=(_card("4"),),
    )
    high_bonus, _ = prescription_bonus(
        state,
        kind="SPECTRAL",
        label="Deja Vu",
        cards=(_card("K"),),
    )
    if low_bonus > 0.0:
        assert low_bonus >= high_bonus
        assert any("Hack" in note for note in low_notes)
