from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.live.pack import LivePackActionGenerator, LivePackChoice
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


def test_d9_planet_uses_b4_build_path_value_against_skip():
    state = BalatroState()
    state.phase = "PLANET_PACK"
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
    assert any("Hermit deterministic money gain=" in note for note in ranked[0].notes)
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


def test_d9_soul_is_prioritized_for_early_ante_legendary_joker_value():
    state = BalatroState()
    state.phase = "SPECTRAL_PACK"
    state.ante = 1
    state.joker_slots = 5
    soul = _choice("Spectral", "The Soul", area_index=0)
    black_hole = _choice("Spectral", "Black Hole", area_index=1)

    ranked = BalatroPackPolicy().rank_actions(
        state,
        [
            BalatroAction(SELECT_PACK_CARD, target=black_hole),
            BalatroAction(SELECT_PACK_CARD, target=soul),
            BalatroAction(SKIP_BOOSTER),
        ],
    )

    assert ranked[0].action.target is soul
    assert ranked[0].total == 14.0
    assert any("Legendary Joker option value=8.000" in note for note in ranked[0].notes)
    assert any("early-Ante scaling opportunity bonus=6.000" in note for note in ranked[0].notes)


def test_d9_soul_early_priority_decays_but_remains_above_skip():
    soul = _choice("Spectral", "The Soul")
    policy = BalatroPackPolicy()

    early = BalatroState()
    early.phase = "SPECTRAL_PACK"
    early.ante = 2
    late = BalatroState()
    late.phase = "SPECTRAL_PACK"
    late.ante = 7

    early_score = policy.score_action(
        early,
        BalatroAction(SELECT_PACK_CARD, target=soul),
    )
    late_score = policy.score_action(
        late,
        BalatroAction(SELECT_PACK_CARD, target=soul),
    )

    assert early_score.total == 12.5
    assert late_score.total == 8.0
    assert early_score.total > late_score.total > policy.skip_bias


def test_d9_soul_fails_closed_without_a_free_joker_slot():
    state = BalatroState()
    state.phase = "SPECTRAL_PACK"
    state.joker_slots = 5
    state.jokers = [object() for _ in range(5)]
    soul = _choice("Spectral", "The Soul")

    ranked = BalatroPackPolicy().rank_actions(
        state,
        [
            BalatroAction(SELECT_PACK_CARD, target=soul),
            BalatroAction(SKIP_BOOSTER),
        ],
    )

    assert ranked[0].action.name == SKIP_BOOSTER
    soul_score = next(
        result for result in ranked if result.action.name == SELECT_PACK_CARD
    )
    assert soul_score.total == -1.0
    assert any("no free Joker slot (5/5)" in note for note in soul_score.notes)


def test_d9_every_current_spectral_is_explicitly_classified():
    assert BalatroPackPolicy.classified_spectrals() == frozenset(SPECTRAL_CARDS)


def test_d9_aura_uses_analytic_b6_target_expectation_against_skip():
    card = BalatroCard("K", "Hearts")
    state = BalatroState()
    state.phase = "SPECTRAL_PACK"
    state.hand = [card]
    choice = _choice("Spectral", "Aura")

    ranked = _rank(state, choice)

    assert ranked[0].action.name == SELECT_PACK_CARD
    assert ranked[0].action.cards == [card]
    assert ranked[0].total > 0.35
    assert any(
        "Aura uses analytic public-state expectation" in note
        for note in ranked[0].notes
    )
    assert any("B6 Aura expected target gain=" in note for note in ranked[0].notes)
    assert any("selected target index=0" in note for note in ranked[0].notes)


def test_d9_aura_fails_closed_when_every_public_target_already_has_edition():
    state = BalatroState()
    state.phase = "SPECTRAL_PACK"
    state.hand = [BalatroCard("K", "Hearts", edition="Foil")]
    choice = _choice("Spectral", "Aura")

    ranked = _rank(state, choice)

    assert ranked[0].action.name == SKIP_BOOSTER
    aura = next(
        result for result in ranked if result.action.name == SELECT_PACK_CARD
    )
    assert aura.total == -1.0
    assert aura.action.cards == []
    assert any("Aura unavailable" in note for note in aura.notes)


def test_d9_current_pack_generator_preserves_policy_order_and_skip_candidate():
    state = BalatroState()
    state.phase = "STANDARD_PACK"
    choice = _choice(
        "PLAYING_CARD",
        "Steel King",
        value={"rank": "K", "suit": "Hearts"},
        modifier={"enhancement": "m_steel"},
    )

    actions = LivePackActionGenerator().generate_actions(state, [choice])
    ranked = BalatroPackPolicy().rank_actions(state, actions)

    assert ranked[0].action.name == SELECT_PACK_CARD
    assert ranked[0].action.target is choice
    assert any(result.action.name == SKIP_BOOSTER for result in ranked)
    skip = next(result for result in ranked if result.action.name == SKIP_BOOSTER)
    assert skip.total == BalatroPackPolicy().skip_bias
