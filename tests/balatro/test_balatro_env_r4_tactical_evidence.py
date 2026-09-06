from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.deal import deal_supported_round_start
from games.balatro.env.tactical_evidence import PublicTacticalTransitionEvidence
from games.balatro.env.tactical_transition import apply_planned_tactical_step_with_evidence
from games.balatro.env.transition import HeadlessRunState
from games.balatro.state import BalatroState


def _dealt_run(*, seed="R4-EVIDENCE", play=False):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "DRAW_TO_HAND"
    state.discards_remaining = 3
    state.discards_used = 0
    if play:
        state.blind = Blind(BlindType.SMALL, 9999)
    run = HeadlessRunState(public=state, seed=seed)
    return deal_supported_round_start(run)


class _CountingDecisionEngine:
    def __init__(self, action_name, indices):
        self.action_name = action_name
        self.indices = tuple(indices)
        self.calls = 0
        self.observation = None

    def decide(self, state):
        self.calls += 1
        self.observation = state
        return SimpleNamespace(
            action=BalatroAction(
                self.action_name,
                cards=[state.hand[index] for index in self.indices],
            )
        )


def _card_signature(card):
    return (
        card.rank,
        card.suit,
        card.enhancement,
        card.edition,
        card.seal,
        card.permanent_bonus,
        card.face_down,
    )


def test_env_r4_tactical_evidence_reuses_single_production_decision_and_stable_indices():
    run = _dealt_run(seed="R4-EVIDENCE-DISCARD")
    engine = _CountingDecisionEngine(DISCARD_CARDS, (3, 1))
    before_hand = [_card_signature(card) for card in run.public.hand]

    result, evidence = apply_planned_tactical_step_with_evidence(run, engine)

    assert engine.calls == 1
    assert isinstance(evidence, PublicTacticalTransitionEvidence)
    assert evidence.selected_hand_indices == (1, 3)
    assert evidence.action.name == DISCARD_CARDS
    assert evidence.action.cards == [evidence.before.hand[1], evidence.before.hand[3]]
    assert [_card_signature(card) for card in evidence.before.hand] == before_hand
    assert evidence.before.discards_remaining == 3
    assert evidence.after.discards_remaining == 2
    assert evidence.after.phase == result.public.phase
    assert evidence.after is not result.public
    assert evidence.before is not run.public


def test_env_r4_tactical_evidence_masks_pre_action_face_down_identity():
    run = _dealt_run(seed="R4-EVIDENCE-MASK")
    hidden_rank = run.public.hand[0].rank
    hidden_suit = run.public.hand[0].suit
    run.public.hand[0].face_down = True
    engine = _CountingDecisionEngine(DISCARD_CARDS, (0,))

    result, evidence = apply_planned_tactical_step_with_evidence(run, engine)

    before_card = evidence.before.hand[0]
    action_card = evidence.action.cards[0]
    assert before_card.face_down is True
    assert before_card.rank == "?"
    assert before_card.suit == "?"
    assert before_card.live_id is None
    assert action_card is before_card
    assert action_card.rank == "?"
    assert action_card.suit == "?"
    # Once discarded the card is public, so the post-state may expose its actual
    # identity without leaking future/private information.
    assert result.public.discard_pile[-1].rank == hidden_rank
    assert result.public.discard_pile[-1].suit == hidden_suit
    assert evidence.after.discard_pile[-1].rank == hidden_rank
    assert evidence.after.discard_pile[-1].suit == hidden_suit


def test_env_r4_tactical_evidence_contains_no_private_run_or_rng_authority():
    run = _dealt_run(seed="R4-EVIDENCE-PRIVATE")
    engine = _CountingDecisionEngine(DISCARD_CARDS, (0, 2))

    _, evidence = apply_planned_tactical_step_with_evidence(run, engine)

    assert set(vars(evidence)) == {
        "before",
        "action",
        "selected_hand_indices",
        "after",
    }
    for name in (
        "draw_pile",
        "played_pile",
        "rng",
        "rng_state",
        "playing_card_order",
    ):
        assert not hasattr(evidence, name)


def test_env_r4_tactical_evidence_is_durable_after_result_card_mutation():
    run = _dealt_run(seed="R4-EVIDENCE-DURABLE")
    engine = _CountingDecisionEngine(DISCARD_CARDS, (0,))

    result, evidence = apply_planned_tactical_step_with_evidence(run, engine)
    recorded_rank = evidence.after.discard_pile[-1].rank
    recorded_suit = evidence.after.discard_pile[-1].suit

    result.public.discard_pile[-1].rank = "MUTATED"
    result.public.discard_pile[-1].suit = "MUTATED"

    assert evidence.after.discard_pile[-1].rank == recorded_rank
    assert evidence.after.discard_pile[-1].suit == recorded_suit


def test_env_r4_tactical_evidence_records_supported_play_transition():
    run = _dealt_run(seed="R4-EVIDENCE-PLAY", play=True)
    engine = _CountingDecisionEngine(PLAY_CARDS, (0,))

    result, evidence = apply_planned_tactical_step_with_evidence(run, engine)

    assert engine.calls == 1
    assert evidence.action.name == PLAY_CARDS
    assert evidence.selected_hand_indices == (0,)
    assert evidence.before.score == 0
    assert evidence.before.hands_remaining == 4
    assert evidence.after.score == result.public.score > 0
    assert evidence.after.hands_remaining == 3
    assert evidence.after.phase == "SELECTING_HAND"
