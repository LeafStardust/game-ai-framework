from copy import copy as standard_shallow_copy

import games.balatro.state as state_module
from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.blueprint import BlueprintJoker
from games.balatro.jokers.brainstorm import BrainstormJoker
from games.balatro.jokers.dna import DNAJoker
from games.balatro.jokers.eight_ball import EightBallJoker
from games.balatro.jokers.four_fingers import FourFingersJoker
from games.balatro.jokers.glass_joker import GlassJoker
from games.balatro.jokers.oops_all_6s import OopsAll6sJoker
from games.balatro.jokers.seance import SeanceJoker
from games.balatro.jokers.sixth_sense import SixthSenseJoker
from games.balatro.jokers.superposition import SuperpositionJoker
from games.balatro.jokers.vagabond import VagabondJoker
from games.balatro.live.generated_consumable_outcomes import (
    LiveGeneratedConsumableScoreOutcomeModel,
    ProjectedGeneratedConsumable,
)
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.live.post_hand_outcomes import LiveVisibleCardScoreOutcomeModel
from games.balatro.env.parity import canonical_public_state_signature
from games.balatro.state import BalatroState


def _state(cards, jokers, *, money=0, consumables=None, consumable_slots=2):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.owned_deck = list(cards)
    state.jokers = list(jokers)
    state.money = money
    state.consumables = list(consumables or [])
    state.consumable_slots = consumable_slots
    return state


def _project(state, hand, cards):
    return LiveGeneratedConsumableScoreOutcomeModel().project_transition(
        hand,
        state,
        cards,
    )


def _generated_categories(outcome):
    return [
        consumable.category
        for consumable in outcome.state_after_scoring.consumables
        if isinstance(consumable, ProjectedGeneratedConsumable)
    ]


def test_inert_generated_layer_reuses_exact_isolated_parent_transition(monkeypatch):
    card = BalatroCard("A", "Spades", permanent_bonus=12)
    held = {"history": ["held"]}
    state = _state([card], [], consumables=[held])
    state.deck = [card]
    baseline = LiveVisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [card],
    )

    def fail_redundant_copy(self):
        raise AssertionError("inert generated layer must not copy parent state")

    monkeypatch.setattr(
        BalatroState,
        "copy_for_tactical_projection",
        fail_redundant_copy,
    )
    transition = _project(state, PokerHand.HIGH_CARD, [card])

    assert transition.distribution.random_sources == baseline.distribution.random_sources
    assert transition.unsupported_jokers == baseline.unsupported_jokers
    assert [
        (outcome.score, outcome.probability)
        for outcome in transition.distribution.outcomes
    ] == [
        (outcome.score, outcome.probability)
        for outcome in baseline.distribution.outcomes
    ]
    assert canonical_public_state_signature(transition.state_after_scoring) == (
        canonical_public_state_signature(baseline.state_after_scoring)
    )
    assert transition.state_after_scoring is not state
    assert transition.distribution.outcomes[0].state_after_scoring is (
        transition.state_after_scoring
    )
    assert transition.state_after_scoring.hand[0] is not card
    assert transition.state_after_scoring.hand[0] is (
        transition.state_after_scoring.deck[0]
    )
    assert transition.state_after_scoring.hand[0] is (
        transition.state_after_scoring.owned_deck[0]
    )
    transition.state_after_scoring.hand[0].permanent_bonus = 99
    transition.state_after_scoring.consumables[0]["history"].append("projected")
    assert card.permanent_bonus == 12
    assert held == {"history": ["held"]}


def test_generated_capability_classifier_is_exact_and_conservative():
    model = LiveGeneratedConsumableScoreOutcomeModel()
    card = BalatroCard("A", "Spades")
    assert model._generated_consumable_capability(_state([card], [])) is False

    for joker in (
        EightBallJoker(),
        SeanceJoker(),
        SixthSenseJoker(),
        SuperpositionJoker(),
        VagabondJoker(),
    ):
        assert model._generated_consumable_capability(
            _state([card], [joker])
        ) is True

    assert model._generated_consumable_capability(
        _state([card], [BlueprintJoker(), SeanceJoker()])
    ) is True
    assert model._generated_consumable_capability(
        _state([card], [BrainstormJoker(), SeanceJoker()])
    ) is True

    class SeanceSubclass(SeanceJoker):
        pass

    class BlueprintSubclass(BlueprintJoker):
        pass

    assert model._generated_consumable_capability(
        _state([card], [SeanceSubclass()])
    ) is None
    assert model._generated_consumable_capability(
        _state([card], [BlueprintSubclass()])
    ) is None

    malformed = _state([card], [])
    malformed.jokers = ()
    assert model._generated_consumable_capability(malformed) is None

    class StateSubclass(BalatroState):
        pass

    assert model._generated_consumable_capability(StateSubclass()) is None


def test_selective_alias_detachment_covers_mutable_tactical_collections():
    card = BalatroCard("A", "Spades")
    card.projection_metadata = {"history": ["card"]}
    state = _state([card], [])
    state.deck = [card]
    state.discard_pile = [card]
    state.consumables = [{"history": ["held"]}]
    state.shop_jokers = [{"history": ["joker"]}]
    state.shop_consumables = [{"history": ["consumable"]}]
    state.shop_boosters = [{"history": ["booster"]}]
    state.shop_vouchers = [{"history": ["voucher"]}]
    state.vouchers = [{"history": ["owned"]}]

    branch = state.copy().detach_tactical_mutable_aliases()

    assert branch.hand[0] is branch.deck[0]
    assert branch.hand[0] is branch.owned_deck[0]
    assert branch.hand[0] is branch.discard_pile[0]
    assert branch.hand[0] is not card
    branch.hand[0].projection_metadata["history"].append("projected")
    for name in (
        "consumables",
        "shop_jokers",
        "shop_consumables",
        "shop_boosters",
        "shop_vouchers",
        "vouchers",
    ):
        getattr(branch, name)[0]["history"].append("projected")

    assert card.projection_metadata == {"history": ["card"]}
    assert state.consumables == [{"history": ["held"]}]
    assert state.shop_jokers == [{"history": ["joker"]}]
    assert state.shop_consumables == [{"history": ["consumable"]}]
    assert state.shop_boosters == [{"history": ["booster"]}]
    assert state.shop_vouchers == [{"history": ["voucher"]}]
    assert state.vouchers == [{"history": ["owned"]}]


def test_capable_generated_paths_keep_full_tactical_projection(monkeypatch):
    original = BalatroState.copy_for_tactical_projection
    calls = []

    def observed_copy(state):
        calls.append(type(state.jokers[0]))
        return original(state)

    monkeypatch.setattr(
        BalatroState,
        "copy_for_tactical_projection",
        observed_copy,
    )
    card = BalatroCard("A", "Spades")
    generator_types = (
        EightBallJoker,
        SeanceJoker,
        SixthSenseJoker,
        SuperpositionJoker,
        VagabondJoker,
    )
    for generator_type in generator_types:
        _project(_state([card], [generator_type()]), PokerHand.HIGH_CARD, [card])

    assert calls == list(generator_types)


def test_generated_branch_copy_shares_only_frozen_generation_authority():
    card = BalatroCard("A", "Spades")
    state = _state([card], [], consumables=["held"])
    state.joker_unlocks = {"j_joker": {"unlocked": True}}
    state.joker_generation_pools = {"Common": [{"key": "j_joker"}]}
    state.consumable_generation_pools = {"Tarot": [{"key": "c_fool"}]}
    state.voucher_generation_pool = [{"key": "v_overstock", "requires": []}]

    branch = state.copy_for_tactical_projection()

    assert branch is not state
    assert branch.hand is not state.hand
    assert branch.hand[0] is not state.hand[0]
    assert branch.consumables is not state.consumables
    assert branch.jokers is not state.jokers
    for name in (
        "joker_unlocks",
        "joker_generation_pools",
        "consumable_generation_pools",
        "voucher_generation_pool",
    ):
        assert getattr(branch, name) is getattr(state, name)

    branch.consumables.append("projected")
    branch.hand.clear()
    assert state.consumables == ["held"]
    assert state.hand == [card]


def test_tactical_projection_copy_preserves_card_aliases_and_isolation():
    card = BalatroCard("A", "Spades", permanent_bonus=12)
    state = _state([card], [], consumables=["held"])
    state.deck = [card]

    branch = state.copy_for_tactical_projection()

    assert branch.hand[0] is branch.deck[0]
    assert branch.hand[0] is branch.owned_deck[0]
    assert branch.hand[0] is not card
    assert vars(branch.hand[0]) is not vars(card)
    branch.hand[0].permanent_bonus = 99
    assert card.permanent_bonus == 12


def test_tactical_projection_copy_deep_copies_extended_card_state():
    card = BalatroCard("A", "Spades")
    card.projection_metadata = {"history": ["played"]}
    state = _state([card], [])

    branch = state.copy_for_tactical_projection()

    assert branch.hand[0].projection_metadata == card.projection_metadata
    assert branch.hand[0].projection_metadata is not card.projection_metadata
    assert (
        branch.hand[0].projection_metadata["history"]
        is not card.projection_metadata["history"]
    )


def test_tactical_projection_shallow_copies_only_exact_scalar_cards(monkeypatch):
    class CardSubclass(BalatroCard):
        pass

    scalar = BalatroCard("A", "Spades")
    extended = BalatroCard("K", "Hearts")
    extended.projection_metadata = {"history": ["played"]}
    subclass = CardSubclass("Q", "Clubs")
    state = _state([scalar, extended, subclass], [])
    state.deck = [scalar, extended, subclass]
    copied = []

    def observed_shallow_copy(card):
        copied.append(card)
        return standard_shallow_copy(card)

    monkeypatch.setattr(state_module, "shallow_copy", observed_shallow_copy)

    branch = state.copy_for_tactical_projection()

    assert copied == [scalar]
    assert branch.hand[0] is branch.deck[0]
    assert branch.hand[1] is branch.deck[1]
    assert branch.hand[2] is branch.deck[2]
    assert all(
        projected is not source
        for projected, source in zip(branch.hand, state.hand)
    )
    assert branch.hand[1].projection_metadata == extended.projection_metadata
    assert branch.hand[1].projection_metadata is not extended.projection_metadata
    assert type(branch.hand[2]) is CardSubclass


def test_seance_creates_abstract_spectral_without_sampling_identity():
    cards = [
        BalatroCard("4", "Hearts"),
        BalatroCard("5", "Hearts"),
        BalatroCard("6", "Hearts"),
        BalatroCard("7", "Hearts"),
        BalatroCard("8", "Hearts"),
    ]
    state = _state(cards, [SeanceJoker()])

    transition = _project(state, PokerHand.STRAIGHT_FLUSH, cards)

    assert transition.joker_projection_complete is True
    assert len(transition.distribution.outcomes) == 1
    assert _generated_categories(transition.distribution.outcomes[0]) == ["SPECTRAL"]
    assert "generated Spectral identity (abstracted)" in transition.distribution.random_sources
    assert state.consumables == []


def test_seance_and_blueprint_fill_two_slots_in_joker_order():
    cards = [
        BalatroCard("4", "Hearts"),
        BalatroCard("5", "Hearts"),
        BalatroCard("6", "Hearts"),
        BalatroCard("7", "Hearts"),
        BalatroCard("8", "Hearts"),
    ]
    state = _state(cards, [BlueprintJoker(), SeanceJoker()])

    transition = _project(state, PokerHand.STRAIGHT_FLUSH, cards)

    assert _generated_categories(transition.distribution.outcomes[0]) == [
        "SPECTRAL",
        "SPECTRAL",
    ]


def test_generated_consumables_respect_full_slot_capacity():
    cards = [
        BalatroCard("4", "Hearts"),
        BalatroCard("5", "Hearts"),
        BalatroCard("6", "Hearts"),
        BalatroCard("7", "Hearts"),
        BalatroCard("8", "Hearts"),
    ]
    held = "held-consumable"
    state = _state(
        cards,
        [SeanceJoker()],
        consumables=[held],
        consumable_slots=1,
    )

    transition = _project(state, PokerHand.STRAIGHT_FLUSH, cards)

    outcome_state = transition.distribution.outcomes[0].state_after_scoring
    assert outcome_state.consumables == [held]


def test_vagabond_checks_money_at_hand_play():
    card = BalatroCard("A", "Spades")
    eligible = _state([card], [VagabondJoker()], money=4)
    blocked = _state([card], [VagabondJoker()], money=5)

    eligible_transition = _project(eligible, PokerHand.HIGH_CARD, [card])
    blocked_transition = _project(blocked, PokerHand.HIGH_CARD, [card])

    assert _generated_categories(eligible_transition.distribution.outcomes[0]) == ["TAROT"]
    assert _generated_categories(blocked_transition.distribution.outcomes[0]) == []


def test_superposition_requires_ace_to_belong_to_the_straight_component():
    cards = [
        BalatroCard("5", "Spades"),
        BalatroCard("6", "Hearts"),
        BalatroCard("7", "Clubs"),
        BalatroCard("8", "Diamonds"),
        BalatroCard("A", "Spades"),
    ]
    state = _state(cards, [FourFingersJoker(), SuperpositionJoker()])

    transition = _project(state, PokerHand.STRAIGHT, cards)

    assert _generated_categories(transition.distribution.outcomes[0]) == []


def test_superposition_counts_debuffed_ace_for_straight_structure():
    cards = [
        BalatroCard("A", "Spades", debuffed=True),
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Clubs"),
        BalatroCard("4", "Diamonds"),
        BalatroCard("5", "Spades"),
    ]
    state = _state(cards, [SuperpositionJoker()])

    transition = _project(state, PokerHand.STRAIGHT, cards)

    assert _generated_categories(transition.distribution.outcomes[0]) == ["TAROT"]


def test_sixth_sense_first_hand_destroys_six_and_creates_one_spectral():
    six = BalatroCard("6", "Hearts", live_id=600)
    state = _state([six], [SixthSenseJoker()])

    transition = _project(state, PokerHand.HIGH_CARD, [six])

    outcome_state = transition.distribution.outcomes[0].state_after_scoring
    assert _generated_categories(transition.distribution.outcomes[0]) == ["SPECTRAL"]
    assert outcome_state.owned_deck == []
    assert len(state.owned_deck) == 1


def test_sixth_sense_does_not_trigger_after_an_earlier_hand():
    six = BalatroCard("6", "Hearts", live_id=600)
    state = _state([six], [SixthSenseJoker()])
    state.round_hand_play_counts["PAIR"] = 1

    transition = _project(state, PokerHand.HIGH_CARD, [six])

    outcome_state = transition.distribution.outcomes[0].state_after_scoring
    assert _generated_categories(transition.distribution.outcomes[0]) == []
    assert len(outcome_state.owned_deck) == 1


def test_sixth_sense_full_slots_prevent_both_creation_and_destruction():
    six = BalatroCard("6", "Hearts", live_id=600)
    held = "held-consumable"
    state = _state(
        [six],
        [SixthSenseJoker()],
        consumables=[held],
        consumable_slots=1,
    )

    transition = _project(state, PokerHand.HIGH_CARD, [six])

    outcome_state = transition.distribution.outcomes[0].state_after_scoring
    assert outcome_state.consumables == [held]
    assert len(outcome_state.owned_deck) == 1


def test_duplicate_sixth_sense_only_destroys_the_six_once():
    six = BalatroCard("6", "Hearts", live_id=600)
    state = _state([six], [SixthSenseJoker(), SixthSenseJoker()])

    transition = _project(state, PokerHand.HIGH_CARD, [six])

    assert _generated_categories(transition.distribution.outcomes[0]) == ["SPECTRAL"]
    assert transition.distribution.outcomes[0].state_after_scoring.owned_deck == []


def test_blueprint_does_not_copy_sixth_sense():
    six = BalatroCard("6", "Hearts", live_id=600)
    state = _state(
        [six],
        [BlueprintJoker(), SixthSenseJoker()],
        consumable_slots=2,
    )

    transition = _project(state, PokerHand.HIGH_CARD, [six])

    assert _generated_categories(transition.distribution.outcomes[0]) == ["SPECTRAL"]
    assert transition.joker_projection_complete is True


def test_dna_copy_survives_sixth_sense_destruction_of_original():
    six = BalatroCard("6", "Hearts", live_id=600)
    state = _state([six], [DNAJoker(), SixthSenseJoker()])

    transition = _project(state, PokerHand.HIGH_CARD, [six])

    outcome_state = transition.distribution.outcomes[0].state_after_scoring
    assert _generated_categories(transition.distribution.outcomes[0]) == ["SPECTRAL"]
    assert len(outcome_state.owned_deck) == 1
    assert outcome_state.owned_deck[0].rank == "6"
    assert outcome_state.owned_deck[0].live_id is None


def test_glass_six_is_destroyed_by_sixth_sense_without_glass_break_rng():
    six = BalatroCard("6", "Hearts", enhancement="Glass", live_id=600)
    glass_joker = GlassJoker()
    state = _state([six], [glass_joker, SixthSenseJoker()])

    transition = _project(state, PokerHand.HIGH_CARD, [six])

    assert transition.distribution.deterministic is True
    assert "Glass break x1" not in transition.distribution.random_sources
    outcome = transition.distribution.outcomes[0]
    assert _generated_categories(outcome) == ["SPECTRAL"]
    assert outcome.state_after_scoring.owned_deck == []
    projected_glass = next(
        joker
        for joker in outcome.state_after_scoring.jokers
        if isinstance(joker, GlassJoker)
    )
    assert projected_glass.x_mult == 1.75
    assert glass_joker.x_mult == 1.0


def test_eight_ball_has_exact_one_in_four_creation_branch():
    eight = BalatroCard("8", "Hearts")
    state = _state([eight], [EightBallJoker()], consumable_slots=1)

    transition = _project(state, PokerHand.HIGH_CARD, [eight])

    branches = sorted(
        (
            tuple(_generated_categories(outcome)),
            round(outcome.probability, 10),
        )
        for outcome in transition.distribution.outcomes
    )
    assert branches == [
        ((), 0.75),
        (("TAROT",), 0.25),
    ]
    assert "8 Ball x1" in transition.distribution.random_sources


def test_oops_all_sixes_doubles_eight_ball_probability():
    eight = BalatroCard("8", "Hearts")
    state = _state(
        [eight],
        [EightBallJoker(), OopsAll6sJoker()],
        consumable_slots=1,
    )

    transition = _project(state, PokerHand.HIGH_CARD, [eight])

    probabilities = {
        tuple(_generated_categories(outcome)): round(outcome.probability, 10)
        for outcome in transition.distribution.outcomes
    }
    assert probabilities == {
        (): 0.5,
        ("TAROT",): 0.5,
    }


def test_red_seal_retrigger_gives_eight_ball_two_independent_attempts():
    eight = BalatroCard("8", "Hearts", seal="Red")
    state = _state([eight], [EightBallJoker()], consumable_slots=1)

    transition = _project(state, PokerHand.HIGH_CARD, [eight])

    probabilities = {
        tuple(_generated_categories(outcome)): round(outcome.probability, 10)
        for outcome in transition.distribution.outcomes
    }
    assert probabilities == {
        (): 0.5625,
        ("TAROT",): 0.4375,
    }
    assert "8 Ball x2" in transition.distribution.random_sources


def test_two_eight_ball_attempts_can_fill_two_slots():
    eight = BalatroCard("8", "Hearts", seal="Red")
    state = _state([eight], [EightBallJoker()], consumable_slots=2)

    transition = _project(state, PokerHand.HIGH_CARD, [eight])

    probabilities = {
        tuple(_generated_categories(outcome)): round(outcome.probability, 10)
        for outcome in transition.distribution.outcomes
    }
    assert probabilities == {
        (): 0.5625,
        ("TAROT",): 0.375,
        ("TAROT", "TAROT"): 0.0625,
    }


def test_blueprint_copy_of_eight_ball_adds_independent_attempt():
    eight = BalatroCard("8", "Hearts")
    state = _state(
        [eight],
        [BlueprintJoker(), EightBallJoker()],
        consumable_slots=1,
    )

    transition = _project(state, PokerHand.HIGH_CARD, [eight])

    probabilities = {
        tuple(_generated_categories(outcome)): round(outcome.probability, 10)
        for outcome in transition.distribution.outcomes
    }
    assert probabilities == {
        (): 0.5625,
        ("TAROT",): 0.4375,
    }
    assert "8 Ball x2" in transition.distribution.random_sources


def test_generated_copy_keeps_copier_edition_inside_lucky_score_branches():
    cards = [
        BalatroCard("4", "Hearts"),
        BalatroCard("5", "Hearts"),
        BalatroCard("6", "Hearts"),
        BalatroCard("7", "Hearts"),
        BalatroCard("8", "Hearts", enhancement="Lucky"),
    ]
    blueprint = BlueprintJoker()
    blueprint.edition = "Holographic"
    state = _state(cards, [blueprint, SeanceJoker()], consumable_slots=2)

    transition = _project(state, PokerHand.STRAIGHT_FLUSH, cards)

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert sorted(
        (outcome.score, round(outcome.probability, 10))
        for outcome in transition.distribution.outcomes
    ) == [
        (2340, 0.8),
        (4940, 0.2),
    ]
    assert all(
        _generated_categories(outcome) == ["SPECTRAL", "SPECTRAL"]
        for outcome in transition.distribution.outcomes
    )


def test_eight_ball_uses_slot_before_main_seance_generation():
    cards = [
        BalatroCard("4", "Hearts"),
        BalatroCard("5", "Hearts"),
        BalatroCard("6", "Hearts"),
        BalatroCard("7", "Hearts"),
        BalatroCard("8", "Hearts"),
    ]
    state = _state(
        cards,
        [EightBallJoker(), SeanceJoker()],
        consumable_slots=1,
    )

    transition = _project(state, PokerHand.STRAIGHT_FLUSH, cards)

    probabilities = {
        tuple(_generated_categories(outcome)): round(outcome.probability, 10)
        for outcome in transition.distribution.outcomes
    }
    assert probabilities == {
        ("SPECTRAL",): 0.75,
        ("TAROT",): 0.25,
    }


def test_live_hand_evaluator_routes_through_generated_consumable_projection():
    cards = [
        BalatroCard("4", "Hearts"),
        BalatroCard("5", "Hearts"),
        BalatroCard("6", "Hearts"),
        BalatroCard("7", "Hearts"),
        BalatroCard("8", "Hearts"),
    ]
    state = _state(cards, [SeanceJoker()])
    evaluator = LiveHandDecisionEvaluator()

    projection = evaluator.project_play(
        state,
        BalatroAction(PLAY_CARDS, cards),
    )

    assert projection.joker_projection_complete is True
    assert projection.unsupported_jokers == ()
    assert any(
        _generated_categories(outcome) == ["SPECTRAL"]
        for outcome in projection.outcomes
    )
