from games.balatro.card import BalatroCard
from games.balatro.jokers.arrowhead import ArrowheadJoker
from games.balatro.jokers.baron import BaronJoker
from games.balatro.jokers.dna import DNAJoker
from games.balatro.jokers.mime import MimeJoker
from games.balatro.jokers.seeing_double import SeeingDoubleJoker
from games.balatro.jokers.stuntman import StuntmanJoker
from games.balatro.jokers.the_idol import TheIdolJoker
from games.balatro.live.runtime.strategy_autonomous_runner import (
    StrategyAwareLiveMemoryInjectedSingleStepRunner,
)
from games.balatro.state import BalatroState
from games.balatro.strategy import BANNED, BRONZE, GOLD, NEUTRAL, SILVER
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES
from games.balatro.strategy_conditional_relationships import (
    StateAwareBalatroStrategyTracker,
    conditional_joker_relationship,
)
from games.balatro.strategy_tree_catalog import (
    TREE_MIGRATED_UNIVERSAL_BALATRO_STRATEGIES,
)
from games.balatro.strategy_tree_tracker import (
    TreeAwareStateAwareBalatroStrategyTracker,
)


def _state() -> BalatroState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.owned_deck = list(state.deck)
    return state


def _tracker() -> StateAwareBalatroStrategyTracker:
    return StateAwareBalatroStrategyTracker(RUNTIME_UNIVERSAL_BALATRO_STRATEGIES)


def _tree_definition_tracker() -> StateAwareBalatroStrategyTracker:
    return StateAwareBalatroStrategyTracker(
        TREE_MIGRATED_UNIVERSAL_BALATRO_STRATEGIES
    )


def test_seeing_double_is_neutral_for_ordinary_flush_structure():
    state = _state()

    assert (
        conditional_joker_relationship(state, "flush", SeeingDoubleJoker())
        == NEUTRAL
    )


def test_seeing_double_becomes_flush_bronze_when_one_flush_can_trigger_it():
    state = _state()
    state.owned_deck.append(BalatroCard("2", "Clubs", enhancement="Wild"))

    assert (
        conditional_joker_relationship(state, "flush", SeeingDoubleJoker())
        == BRONZE
    )

    state.jokers = [SeeingDoubleJoker()]
    flush = next(
        assessment
        for assessment in _tracker().assess(state)
        if assessment.strategy_id == "flush"
    )
    assert flush.bronze_owned == 1


def test_suit_payoff_joker_requires_developed_matching_straight_flush_shell():
    ordinary = _state()
    shaped = _state()
    shaped.owned_deck.append(BalatroCard("2", "Spades"))

    assert (
        conditional_joker_relationship(ordinary, "straight_flush", ArrowheadJoker())
        == NEUTRAL
    )
    assert (
        conditional_joker_relationship(shaped, "straight_flush", ArrowheadJoker())
        == BRONZE
    )


def test_candidate_index_receives_same_conditional_suit_relationship():
    state = _state()
    state.owned_deck.append(BalatroCard("2", "Spades"))
    tracker = _tracker()
    tracker.assess(state)

    relationships = tracker._relationships_for(ArrowheadJoker(), kind="JOKER")

    assert relationships["straight_flush"] == BRONZE


def test_idol_five_kind_requires_reachable_rank_and_exact_target_duplicate():
    state = _state()
    idol = TheIdolJoker("K", "Hearts")

    assert conditional_joker_relationship(state, "five_kind", idol) == NEUTRAL

    state.owned_deck = [
        BalatroCard("K", "Hearts"),
        BalatroCard("K", "Hearts"),
        BalatroCard("K", "Diamonds"),
        BalatroCard("K", "Clubs"),
        BalatroCard("K", "Spades"),
    ]
    assert conditional_joker_relationship(state, "five_kind", idol) == SILVER
    assert conditional_joker_relationship(state, "flush_five", idol) == NEUTRAL


def test_idol_flush_five_gold_requires_five_effective_exact_targets():
    state = _state()
    idol = TheIdolJoker("K", "Hearts")
    state.owned_deck = [BalatroCard("K", "Hearts") for _ in range(5)]

    assert conditional_joker_relationship(state, "five_kind", idol) == SILVER
    assert conditional_joker_relationship(state, "flush_five", idol) == GOLD


def test_dna_stays_neutral_until_public_deck_is_structurally_rank_collapsed():
    ordinary = _state()
    collapsed = _state()
    collapsed.owned_deck = [
        *[BalatroCard("A", "Spades") for _ in range(5)],
        *[BalatroCard("K", "Hearts") for _ in range(5)],
        *[BalatroCard("Q", "Clubs") for _ in range(5)],
    ]

    assert (
        conditional_joker_relationship(ordinary, "straight_flush", DNAJoker())
        == NEUTRAL
    )
    assert (
        conditional_joker_relationship(collapsed, "straight_flush", DNAJoker())
        == BANNED
    )


def test_baron_is_neutral_until_current_deck_has_deliberate_king_support():
    state = _state()

    assert (
        conditional_joker_relationship(
            state,
            "high_card_baron_mime",
            BaronJoker(),
        )
        == NEUTRAL
    )

    state.owned_deck.append(BalatroCard("K", "Hearts"))

    assert (
        conditional_joker_relationship(
            state,
            "high_card_baron_mime",
            BaronJoker(),
        )
        == SILVER
    )


def test_mime_requires_a_real_held_king_payoff_or_baron_partner():
    ordinary = _state()
    assert (
        conditional_joker_relationship(
            ordinary,
            "high_card_baron_mime",
            MimeJoker(),
        )
        == NEUTRAL
    )

    steel_king = _state()
    steel_king.owned_deck.append(
        BalatroCard("K", "Hearts", enhancement="Steel")
    )
    assert (
        conditional_joker_relationship(
            steel_king,
            "high_card_baron_mime",
            MimeJoker(),
        )
        == SILVER
    )

    paired = _state()
    paired.jokers = [BaronJoker()]
    assert (
        conditional_joker_relationship(
            paired,
            "high_card_baron_mime",
            MimeJoker(),
        )
        == SILVER
    )


def test_static_baron_tier_is_authoritatively_neutralized_and_recomputed():
    state = _state()
    state.jokers = [BaronJoker()]
    tracker = _tree_definition_tracker()

    ordinary = next(
        assessment
        for assessment in tracker.assess(state)
        if assessment.strategy_id == "high_card_baron_mime"
    )
    assert ordinary.silver_owned == 0

    state.owned_deck.append(BalatroCard("K", "Spades"))
    shaped = next(
        assessment
        for assessment in tracker.assess(state)
        if assessment.strategy_id == "high_card_baron_mime"
    )
    assert shaped.silver_owned == 1

    state.owned_deck = list(state.deck)
    reverted = next(
        assessment
        for assessment in tracker.assess(state)
        if assessment.strategy_id == "high_card_baron_mime"
    )
    assert reverted.silver_owned == 0


def test_candidate_index_uses_same_baron_mime_downgrade_semantics():
    state = _state()
    tracker = _tree_definition_tracker()
    tracker.assess(state)

    relationships = tracker._relationships_for(BaronJoker(), kind="JOKER")
    assert "high_card_baron_mime" not in relationships

    state.owned_deck.append(BalatroCard("K", "Diamonds"))
    tracker.assess(state)
    relationships = tracker._relationships_for(BaronJoker(), kind="JOKER")
    assert relationships["high_card_baron_mime"] == SILVER


def test_baron_and_mime_together_are_defining_evidence_even_before_deck_shaping():
    state = _state()
    state.jokers = [BaronJoker(), MimeJoker()]
    tracker = _tree_definition_tracker()

    assessment = next(
        assessment
        for assessment in tracker.assess(state)
        if assessment.strategy_id == "high_card_baron_mime"
    )

    assert assessment.silver_owned == 2


def test_stuntman_conflict_requires_a_material_held_card_engine():
    ordinary = _state()
    assert (
        conditional_joker_relationship(
            ordinary,
            "high_card_baron_mime",
            StuntmanJoker(),
        )
        == NEUTRAL
    )

    isolated_steel_king = _state()
    isolated_steel_king.owned_deck.append(
        BalatroCard("K", "Hearts", enhancement="Steel")
    )
    assert (
        conditional_joker_relationship(
            isolated_steel_king,
            "high_card_baron_mime",
            StuntmanJoker(),
        )
        == NEUTRAL
    )

    paired = _state()
    paired.jokers = [BaronJoker(), MimeJoker()]
    assert (
        conditional_joker_relationship(
            paired,
            "high_card_baron_mime",
            StuntmanJoker(),
        )
        == BANNED
    )

    steel_shell = _state()
    steel_shell.owned_deck.extend(
        (
            BalatroCard("K", "Hearts", enhancement="Steel"),
            BalatroCard("K", "Spades", enhancement="Steel"),
        )
    )
    assert (
        conditional_joker_relationship(
            steel_shell,
            "high_card_baron_mime",
            StuntmanJoker(),
        )
        == BANNED
    )


def test_static_stuntman_ban_is_neutralized_then_recomputed_from_current_state():
    state = _state()
    state.jokers = [StuntmanJoker()]
    tracker = _tree_definition_tracker()

    ordinary = next(
        assessment
        for assessment in tracker.assess(state)
        if assessment.strategy_id == "high_card_baron_mime"
    )
    assert ordinary.banned_owned == 0

    state.jokers = [BaronJoker(), MimeJoker(), StuntmanJoker()]
    established = next(
        assessment
        for assessment in tracker.assess(state)
        if assessment.strategy_id == "high_card_baron_mime"
    )
    assert established.silver_owned == 2
    assert established.banned_owned == 1

    state.jokers = [StuntmanJoker()]
    reverted = next(
        assessment
        for assessment in tracker.assess(state)
        if assessment.strategy_id == "high_card_baron_mime"
    )
    assert reverted.banned_owned == 0


def test_stuntman_candidate_is_gold_for_small_hand_leaf_and_banned_for_established_held_leaf():
    state = _state()
    state.jokers = [BaronJoker(), MimeJoker()]
    tracker = _tree_definition_tracker()
    tracker.assess(state)

    relationships = tracker._relationships_for(StuntmanJoker(), kind="JOKER")

    assert relationships["high_card_stuntman"] == GOLD
    assert relationships["high_card_baron_mime"] == BANNED


def test_production_strategy_runner_uses_tree_state_aware_strategy_tracker():
    assert (
        StrategyAwareLiveMemoryInjectedSingleStepRunner.__init__.__globals__[
            "TreeAwareStateAwareBalatroStrategyTracker"
        ]
        is TreeAwareStateAwareBalatroStrategyTracker
    )
