from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.hit_the_road import HitTheRoadJoker
from games.balatro.jokers.ramen import RamenJoker
from games.balatro.jokers.yorick import YorickJoker
from games.balatro.live.final_joker_outcomes import LiveFinalJokerScoreOutcomeModel
from games.balatro.state import BalatroState


def _hook_state(cards, joker):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.blind = Blind(BlindType.BOSS, 10_000)
    state.boss_name = "The Hook"
    state.hand = list(cards)
    state.owned_deck = list(cards)
    state.deck = []
    state.jokers = [joker]
    state.hands_remaining = 4
    state.discards_remaining = 3
    state.discards_used = 0
    state.hand_size = len(cards)
    return state


def _project(state, played):
    return LiveFinalJokerScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        played,
    )


def test_hook_forced_discard_advances_yorick_before_current_hand_scores():
    played = BalatroCard("A", "Spades", live_id=1)
    forced = BalatroCard("2", "Hearts", live_id=2)
    yorick = YorickJoker()
    yorick.discarded_cards = 22
    yorick.x_mult = 1.0
    state = _hook_state([played, forced], yorick)

    transition = _project(state, [played])
    branch = transition.distribution.outcomes[0].state_after_scoring

    # One forced discard reaches Yorick's 23-card threshold before scoring.
    # High Card A is 16 chips x 1 Mult, then Yorick's current X2 => 32.
    assert transition.distribution.minimum == 32
    assert branch.jokers[0].discarded_cards == 0
    assert branch.jokers[0].x_mult == 2.0
    assert yorick.discarded_cards == 22
    assert yorick.x_mult == 1.0


def test_hook_forced_jack_discard_advances_hit_the_road_before_scoring():
    played = BalatroCard("A", "Spades", live_id=1)
    forced = BalatroCard("J", "Hearts", live_id=2)
    joker = HitTheRoadJoker()
    state = _hook_state([played, forced], joker)

    transition = _project(state, [played])
    branch = transition.distribution.outcomes[0].state_after_scoring

    # Hook discards the Jack first, making Hit the Road X1.5 for this hand.
    assert transition.distribution.minimum == 24
    assert branch.jokers[0].x_mult == 1.5
    assert joker.x_mult == 1.0


def test_hook_forced_discard_reduces_ramen_before_current_hand_scores():
    played = BalatroCard("A", "Spades", live_id=1)
    forced = BalatroCard("2", "Hearts", live_id=2)
    ramen = RamenJoker()
    ramen.x_mult = 2.0
    state = _hook_state([played, forced], ramen)

    transition = _project(state, [played])
    branch = transition.distribution.outcomes[0].state_after_scoring

    # Ramen loses X0.01 first, so 16 * 1.99 truncates to 31.
    assert transition.distribution.minimum == 31
    assert branch.jokers[0].x_mult == 1.99
    assert ramen.x_mult == 2.0


def test_hook_debuffed_purple_seal_does_not_generate_tarot():
    played = BalatroCard("A", "Spades", live_id=1)
    forced = BalatroCard(
        "2",
        "Hearts",
        seal="Purple",
        live_id=2,
        debuffed=True,
    )
    state = _hook_state([played, forced], RamenJoker())
    state.consumables = []
    state.consumable_slots = 2

    transition = _project(state, [played])
    branch = transition.distribution.outcomes[0].state_after_scoring

    assert branch.consumables == []
