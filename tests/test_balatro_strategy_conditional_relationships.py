from games.balatro.card import BalatroCard
from games.balatro.jokers.arrowhead import ArrowheadJoker
from games.balatro.jokers.dna import DNAJoker
from games.balatro.jokers.seeing_double import SeeingDoubleJoker
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


def _state() -> BalatroState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.owned_deck = list(state.deck)
    return state


def _tracker() -> StateAwareBalatroStrategyTracker:
    return StateAwareBalatroStrategyTracker(RUNTIME_UNIVERSAL_BALATRO_STRATEGIES)


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


def test_production_strategy_runner_uses_state_aware_strategy_tracker():
    assert (
        StrategyAwareLiveMemoryInjectedSingleStepRunner.__init__.__globals__[
            "StateAwareBalatroStrategyTracker"
        ]
        is StateAwareBalatroStrategyTracker
    )
