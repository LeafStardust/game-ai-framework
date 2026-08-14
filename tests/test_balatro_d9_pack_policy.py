from types import SimpleNamespace

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.live.external.live_memory_pack_policy_validation import (
    build_live_d9_view,
)
from games.balatro.live.pack import LivePackChoice
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.spectrals import SPECTRAL_CARDS
from games.balatro.state import BalatroState


def _choice(
    kind: str,
    label: str,
    *,
    area_index: int = 0,
    value: dict | None = None,
    modifier: dict | None = None,
) -> LivePackChoice:
    data = {
        "area_index": area_index,
        "address": 0x1000 + area_index,
        "live_id": 500 + area_index,
        "label": label,
        "ability_name": label,
        "ability_set": kind,
    }
    if value is not None:
        data["value"] = value
    if modifier is not None:
        data["modifier"] = modifier
    return LivePackChoice(
        area_index=area_index,
        address=0x1000 + area_index,
        data=data,
    )


def _rank(state: BalatroState, choice: LivePackChoice):
    return BalatroPackPolicy(skip_bias=0.35).rank_actions(
        state,
        [
            BalatroAction(SELECT_PACK_CARD, target=choice),
            BalatroAction(SKIP_BOOSTER),
        ],
    )


def test_d9_buffoon_joker_uses_b3_whole_build_value_against_skip():
    state = BalatroState()
    state.phase = "BUFFOON_PACK"
    state.joker_slots = 5
    choice = _choice("Joker", "Joker")

    ranked = _rank(state, choice)

    assert ranked[0].action.name == SELECT_PACK_CARD
    assert ranked[0].total > 0.35
    assert any("whole-build Joker gain=" in note for note in ranked[0].notes)
    assert any("B3 contextual gain=" in note for note in ranked[0].notes)


def test_d9_standard_card_uses_b6_build_context_against_skip():
    state = BalatroState()
    state.phase = "STANDARD_PACK"
    state.deck = [BalatroCard("Q", "Hearts") for _ in range(8)]
    choice = _choice(
        "PLAYING_CARD",
        "Steel King",
        value={"rank": "K", "suit": "Hearts"},
        modifier={"enhancement": "m_steel"},
    )

    ranked = _rank(state, choice)

    assert ranked[0].action.name == SELECT_PACK_CARD
    assert ranked[0].total > 0.35
    assert any("B6 playing-card build gain=" in note for note in ranked[0].notes)


def test_d9_celestial_planet_uses_b4_build_path_value_against_skip():
    state = BalatroState()
    state.phase = "CELESTIAL_PACK"
    state.hand_levels["PAIR"] = 3
    choice = _choice("Planet", "Mercury")

    ranked = _rank(state, choice)

    assert ranked[0].action.name == SELECT_PACK_CARD
    assert ranked[0].total > 0.35
    assert any("planet upgrade" in note for note in ranked[0].notes)
    assert any("B4 build-path gain=" in note for note in ranked[0].notes)


def test_d9_arcana_immediate_tarot_uses_b4_value_against_skip():
    state = BalatroState()
    state.phase = "TAROT_PACK"
    state.money = 10
    choice = _choice("Tarot", "The Hermit")

    ranked = _rank(state, choice)

    assert ranked[0].action.name == SELECT_PACK_CARD
    assert ranked[0].total > 0.35
    assert any("Hermit potential money gain=" in note for note in ranked[0].notes)
    assert any("B4 build-path gain=" in note for note in ranked[0].notes)


def test_d9_spectral_targeted_choice_uses_b6_target_value_against_skip():
    card = BalatroCard("4", "Clubs")
    state = BalatroState()
    state.phase = "SPECTRAL_PACK"
    state.hand = [card]
    state.deck = [BalatroCard("4", "Clubs")]
    choice = _choice("Spectral", "Deja Vu")

    ranked = _rank(state, choice)

    assert ranked[0].action.name == SELECT_PACK_CARD
    assert ranked[0].action.cards == [card]
    assert ranked[0].total > 0.35
    assert any("B6 pack target gain=" in note for note in ranked[0].notes)
    assert any("target_indices=(0,)" in note for note in ranked[0].notes)


def test_d9_black_hole_uses_b4_immediate_spectral_value_against_skip():
    state = BalatroState()
    state.phase = "SPECTRAL_PACK"
    choice = _choice("Spectral", "Black Hole")

    ranked = _rank(state, choice)

    assert ranked[0].action.name == SELECT_PACK_CARD
    assert ranked[0].action.cards == []
    assert ranked[0].total > 0.35
    assert any(
        "deterministic immediate Spectral uses shared B4 item valuation" in note
        for note in ranked[0].notes
    )
    assert any("B4 build-path gain=" in note for note in ranked[0].notes)


def test_d9_every_current_spectral_is_explicitly_classified():
    assert BalatroPackPolicy.classified_spectrals() == frozenset(SPECTRAL_CARDS)


def test_d9_unmodeled_visible_effect_stays_below_explicit_skip_baseline():
    state = BalatroState()
    state.phase = "SPECTRAL_PACK"
    state.hand = [BalatroCard("4", "Clubs")]
    choice = _choice("Spectral", "Aura")

    ranked = _rank(state, choice)

    assert ranked[0].action.name == SKIP_BOOSTER
    unsupported = next(
        result for result in ranked if result.action.name == SELECT_PACK_CARD
    )
    assert unsupported.total == -1.0
    assert unsupported.action.cards == []


def test_d9_live_view_preserves_policy_order_and_explicit_skip_candidate():
    state = BalatroState()
    state.phase = "STANDARD_PACK"
    choice = _choice(
        "PLAYING_CARD",
        "Steel King",
        value={"rank": "K", "suit": "Hearts"},
        modifier={"enhancement": "m_steel"},
    )
    snapshot = SimpleNamespace(
        phase="STANDARD_PACK",
        state_complete=True,
        sequence=7,
    )

    view = build_live_d9_view(snapshot, state, [choice])

    assert view.recommendation.score.action.name == SELECT_PACK_CARD
    assert view.recommendation.area_index == 0
    assert any(candidate.kind == "SKIP" for candidate in view.candidates)
    skip = next(candidate for candidate in view.candidates if candidate.kind == "SKIP")
    assert skip.score.total == BalatroPackPolicy().skip_bias
