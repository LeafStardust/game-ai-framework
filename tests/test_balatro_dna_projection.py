from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.dna import DNAJoker
from games.balatro.jokers.hologram import HologramJoker
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live.draw_outcomes import PublicDrawOutcomeModel
from games.balatro.live.post_hand_outcomes import LiveVisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _state(*jokers):
    ace = BalatroCard("A", "Spades", live_id=101)
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [ace]
    state.deck = [BalatroCard("2", "Hearts", live_id=202)]
    state.owned_deck = [ace]
    state.jokers = list(jokers)
    state.hands_remaining = 2
    state.discards_remaining = 0
    state.round_hand_play_counts = {
        hand: 0
        for hand in state.hand_levels
    }
    return state, ace


def test_dna_first_single_card_hand_adds_permanent_copy_and_draws_it_to_hand():
    state, ace = _state(DNAJoker())

    transition = LiveVisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    assert transition.joker_projection_complete is True
    assert transition.unsupported_jokers == ()
    assert transition.distribution.deterministic is True
    assert transition.distribution.minimum == 16

    projected = transition.state_after_scoring
    assert projected is not None
    assert len(projected.hand) == 2
    assert len(projected.owned_deck) == 2

    copied = projected.hand[1]
    assert copied is projected.owned_deck[1]
    assert copied is not projected.hand[0]
    assert copied.rank == "A"
    assert copied.suit == "Spades"
    assert copied.live_id is None

    assert len(state.hand) == 1
    assert len(state.owned_deck) == 1
    assert state.hand[0] is ace


def test_dna_does_not_trigger_after_any_hand_has_already_been_played_this_round():
    state, ace = _state(DNAJoker())
    state.round_hand_play_counts[PokerHand.PAIR.value] = 1

    transition = LiveVisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    assert transition.joker_projection_complete is True
    assert len(transition.state_after_scoring.hand) == 1
    assert len(transition.state_after_scoring.owned_deck) == 1


def test_dna_requires_exactly_one_played_card():
    state, ace = _state(DNAJoker())
    two = BalatroCard("2", "Hearts", live_id=202)
    state.hand.append(two)
    state.owned_deck.append(two)

    transition = LiveVisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace, two],
    )

    assert transition.joker_projection_complete is True
    assert len(transition.state_after_scoring.hand) == 2
    assert len(transition.state_after_scoring.owned_deck) == 2


def test_dna_fails_closed_without_authoritative_owned_deck():
    state, ace = _state(DNAJoker())
    state.owned_deck = None

    transition = LiveVisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    assert transition.joker_projection_complete is False
    assert "DNA" in transition.unsupported_jokers


def test_dna_card_addition_grows_hologram_before_same_hand_scores():
    hologram = HologramJoker()
    state, ace = _state(DNAJoker(), hologram)

    transition = LiveVisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    assert transition.joker_projection_complete is True
    assert transition.distribution.minimum == 20
    projected_hologram = next(
        joker
        for joker in transition.state_after_scoring.jokers
        if type(joker).__name__ == "HologramJoker"
    )
    assert projected_hologram.x_mult == 1.25
    assert hologram.x_mult == 1.0


def test_dna_only_triggers_on_first_hand_across_projected_child_state():
    state, ace = _state(DNAJoker())

    first = LiveVisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )
    after_first = first.state_after_scoring
    copied = after_first.hand[1]

    assert after_first.round_hand_play_counts[PokerHand.HIGH_CARD.value] == 1

    second = LiveVisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        after_first,
        [copied],
    )

    assert second.joker_projection_complete is True
    assert len(second.state_after_scoring.owned_deck) == 2


class _RecordingDrawOutcomeModel(PublicDrawOutcomeModel):
    def __init__(self):
        super().__init__(exact_combination_limit=128, sample_count=8)
        self.draw_counts = []

    def distribution(self, composition, draws):
        self.draw_counts.append(int(draws))
        return super().distribution(composition, draws)


def test_dna_copy_consumes_the_normal_random_refill_slot_in_d1_search():
    state, ace = _state(DNAJoker())
    state.blind = Blind(BlindType.SMALL, 1_000)
    recorder = _RecordingDrawOutcomeModel()
    planner = LiveBlindClearPlanner(
        draw_outcomes=recorder,
        horizon=2,
        play_width=2,
        discard_width=0,
        child_play_width=2,
        child_discard_width=0,
    )

    estimate = planner._estimate_play(
        state,
        BalatroAction(PLAY_CARDS, cards=[ace]),
        depth=2,
    )

    assert estimate.exact is True
    assert recorder.draw_counts == []
