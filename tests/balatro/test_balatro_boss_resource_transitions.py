from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.castle import CastleJoker
from games.balatro.jokers.chicot import ChicotJoker
from games.balatro.jokers.green_joker import GreenJoker
from games.balatro.jokers.mail_in_rebate import MailInRebateJoker
from games.balatro.jokers.trading_card import TradingCardJoker
from games.balatro.live.final_joker_outcomes import LiveFinalJokerScoreOutcomeModel
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner
from games.balatro.state import BalatroState


def _state(boss_name: str, cards):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.blind = Blind(BlindType.BOSS, 10_000)
    state.boss_name = boss_name
    state.hand = list(cards)
    state.owned_deck = list(cards)
    state.deck = [
        BalatroCard("2", "Spades"),
        BalatroCard("3", "Spades"),
        BalatroCard("4", "Spades"),
        BalatroCard("5", "Spades"),
        BalatroCard("6", "Spades"),
    ]
    state.hands_remaining = 4
    state.discards_remaining = 3
    state.discards_used = 0
    state.hand_size = len(cards)
    return state


def _project(state, cards, hand=PokerHand.HIGH_CARD):
    return LiveFinalJokerScoreOutcomeModel().project_transition(
        hand,
        state,
        cards,
    )


def test_hook_discards_held_cards_before_castle_and_current_hand_score():
    played = BalatroCard("A", "Spades", live_id=1)
    club_a = BalatroCard("2", "Clubs", live_id=2)
    club_b = BalatroCard("3", "Clubs", live_id=3)
    state = _state("The Hook", [played, club_a, club_b])
    castle = CastleJoker("Clubs")
    state.jokers = [castle]

    transition = _project(state, [played])

    assert transition.distribution.deterministic is True
    assert transition.distribution.minimum == 22
    branch = transition.distribution.outcomes[0].state_after_scoring
    assert branch is not None
    assert branch.jokers[0].chips == 6
    assert [card.live_id for card in branch.hand] == [1]
    assert castle.chips == 0


def test_hook_green_joker_forced_discard_resolves_before_hand_play_scaling():
    played = BalatroCard("A", "Spades", live_id=1)
    held = [
        BalatroCard("2", "Clubs", live_id=2),
        BalatroCard("3", "Diamonds", live_id=3),
    ]
    state = _state("The Hook", [played, *held])
    green = GreenJoker()
    green.mult = 4
    state.jokers = [green]

    transition = _project(state, [played])

    # Hook first reduces Green 4 -> 3. The played hand then raises it back to 4
    # before Green contributes +4 Mult: (5 + 11 chips) * (1 + 4 Mult) = 80.
    assert transition.distribution.minimum == 80
    branch = transition.distribution.outcomes[0].state_after_scoring
    assert branch.jokers[0].mult == 4
    assert green.mult == 4


def test_hook_random_pair_is_enumerated_without_hidden_rng_sampling():
    played = BalatroCard("10", "Spades", live_id=1)
    ace = BalatroCard("A", "Hearts", live_id=2)
    king = BalatroCard("K", "Clubs", live_id=3)
    queen = BalatroCard("Q", "Diamonds", live_id=4)
    state = _state("The Hook", [played, ace, king, queen])
    state.money = 0
    state.jokers = [MailInRebateJoker("A")]

    transition = _project(state, [played])

    assert len(transition.distribution.outcomes) == 3
    assert all(
        abs(outcome.probability - (1.0 / 3.0)) < 1e-12
        for outcome in transition.distribution.outcomes
    )
    money = sorted(
        outcome.state_after_scoring.money
        for outcome in transition.distribution.outcomes
    )
    assert money == [0, 5, 5]
    assert "The Hook forced discard x2" in transition.distribution.random_sources


def test_hook_forced_discard_does_not_consume_discard_use_and_can_trigger_trading_card():
    played = BalatroCard("A", "Spades", live_id=1)
    victim = BalatroCard("K", "Hearts", live_id=2)
    state = _state("The Hook", [played, victim])
    state.money = 0
    state.jokers = [TradingCardJoker()]

    transition = _project(state, [played])
    branch = transition.distribution.outcomes[0].state_after_scoring

    assert branch.money == 3
    assert branch.discards_used == 0
    assert [card.live_id for card in branch.owned_deck] == [1]
    assert [card.live_id for card in branch.hand] == [1]


def test_hook_forced_purple_seal_creates_abstract_tarot_before_card_leaves_hand():
    played = BalatroCard("A", "Spades", live_id=1)
    purple = BalatroCard("K", "Hearts", seal="Purple", live_id=2)
    state = _state("The Hook", [played, purple])
    state.consumables = []
    state.consumable_slots = 2

    transition = _project(state, [played])
    branch = transition.distribution.outcomes[0].state_after_scoring

    assert len(branch.consumables) == 1
    assert branch.consumables[0].category == "TAROT"
    assert branch.consumables[0].projected_random_identity is True
    assert branch.discards_used == 0


def test_chicot_suppresses_hook_forced_discard():
    played = BalatroCard("A", "Spades", live_id=1)
    held = [
        BalatroCard("2", "Clubs", live_id=2),
        BalatroCard("3", "Diamonds", live_id=3),
    ]
    state = _state("The Hook", [played, *held])
    state.jokers = [ChicotJoker()]

    transition = _project(state, [played])
    branch = transition.distribution.outcomes[0].state_after_scoring

    assert "The Hook forced discard x2" not in transition.distribution.random_sources
    assert sorted(card.live_id for card in branch.hand) == [1, 2, 3]


def test_serpent_always_draws_three_after_play_or_discard():
    cards = [BalatroCard(str(rank), "Spades", live_id=rank) for rank in range(2, 10)]
    state = _state("The Serpent", cards)
    state.hand_size = 8
    planner = D1LiveBlindClearPlanner(horizon=2)

    assert planner._post_action_draw_count(state, cards[:7]) == 3
    assert planner._post_action_draw_count(state, cards) == 3


def test_chicot_restores_normal_draw_to_hand_size_against_serpent():
    cards = [BalatroCard(str(rank), "Spades", live_id=rank) for rank in range(2, 10)]
    state = _state("The Serpent", cards)
    state.hand_size = 8
    state.jokers = [ChicotJoker()]
    planner = D1LiveBlindClearPlanner(horizon=2)

    assert planner._post_action_draw_count(state, cards[:7]) == 1
    assert planner._post_action_draw_count(state, cards) == 0


def test_manacle_uses_observed_reduced_hand_size_for_replacement_draws():
    cards = [BalatroCard(str(rank), "Spades", live_id=rank) for rank in range(2, 9)]
    state = _state("The Manacle", cards)
    state.hand_size = 7
    planner = D1LiveBlindClearPlanner(horizon=2)

    assert planner._post_action_draw_count(state, cards[:5]) == 2


def test_water_with_zero_observed_discards_generates_no_discard_candidate():
    cards = [
        BalatroCard("A", "Spades", live_id=1),
        BalatroCard("K", "Hearts", live_id=2),
    ]
    state = _state("The Water", cards)
    state.discards_remaining = 0
    planner = D1LiveBlindClearPlanner(
        horizon=2,
        play_width=4,
        discard_width=4,
    )

    actions = planner._candidate_actions(state, allow_discards=True)

    assert actions
    assert all(action.name != DISCARD_CARDS for action in actions)


def test_needle_uses_authoritative_hands_remaining_instead_of_hardcoding_one():
    card = BalatroCard("A", "Spades", live_id=1)
    state = _state("The Needle", [card])
    # This is the live state after a Burglar-style post-boss hand grant. The
    # planner must trust the observed resource count rather than reapply Needle.
    state.hands_remaining = 4
    planner = D1LiveBlindClearPlanner(horizon=1)

    estimate = planner._estimate_action(
        state,
        BalatroAction(PLAY_CARDS, cards=[card]),
        depth=1,
    )

    assert estimate.value.expected_hands_remaining == 3.0
