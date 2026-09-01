from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.bonds.burnt import evaluate_burnt_bond
from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.strategy_semantics import StrategyCommitment
from games.balatro.burnt_bond_execution_policy import _burnt_strategy_fit
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.burnt_joker import BurntJoker
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState


class _SequenceEvaluator:
    def project_play(self, state, action):
        del state
        return SimpleNamespace(
            expected_hand_score=float(action.target.get("immediate_score", 0.0)),
            clear_probability=float(action.target.get("clear_probability", 0.0)),
            outcomes=(),
        )

    def evaluate(self, state, action):
        del state
        return float(action.target.get("fallback_value", 0.0))


def _state(
    cards,
    *,
    hands_remaining=3,
    discards_remaining=2,
    discards_used=0,
    blind_requirement=300,
):
    state = BalatroState()
    state.hand = list(cards)
    state.deck = []
    state.owned_deck = []
    state.jokers = [BurntJoker()]
    state.score = 0
    state.blind = SimpleNamespace(requirement=blind_requirement)
    state.hands_remaining = hands_remaining
    state.discards_remaining = discards_remaining
    state.discards_used = discards_used
    state.boss_name = None
    state.blind_type = "SMALL"
    return state


def _plan(
    action_name,
    cards,
    *,
    clear_probability=0.0,
    expected_score=0.0,
    fallback_value=0.0,
):
    action = BalatroAction(
        action_name,
        cards=list(cards),
        target={
            "immediate_score": expected_score,
            "clear_probability": clear_probability,
            "fallback_value": fallback_value,
        },
    )
    return LiveBlindPlan(
        action=action,
        value=LiveBlindPlanValue(
            clear_probability=clear_probability,
            expected_progress=0.0,
            expected_score=expected_score,
            expected_hands_remaining=2.0,
            expected_discards_remaining=1.0,
        ),
        horizon=1,
        exact=True,
        candidate_count=3,
    )


def _action_signature(action):
    return (
        action.name,
        tuple(
            (
                str(getattr(card, "rank", "")),
                str(getattr(card, "suit", "")),
                str(getattr(card, "enhancement", "") or ""),
                str(getattr(card, "edition", "") or ""),
                str(getattr(card, "seal", "") or ""),
            )
            for card in action.cards
        ),
    )


def _policy(monkeypatch):
    policy = StrategyAwareLiveHandActionPolicy(evaluator=_SequenceEvaluator())
    monkeypatch.setattr(policy, "_hand_bond_intents", lambda state: ())
    monkeypatch.setattr(policy, "_preservation", lambda plan: 0.0)
    monkeypatch.setattr(policy, "_vagabond_generation_active", lambda state: False)
    monkeypatch.setattr(
        policy,
        "_green_preserved_decision",
        lambda state, plans, decision: decision,
    )
    monkeypatch.setattr(policy.build_evaluator, "prepare", lambda state: None)
    monkeypatch.setattr(policy.build_evaluator, "reset_cache", lambda: None)
    return policy


def test_burnt_controlled_sequence_develops_exploits_and_yields_to_survival(monkeypatch):
    scorer = BalatroScorer()
    policy = _policy(monkeypatch)

    ace = BalatroCard("A", "Spades")
    two_hearts = BalatroCard("2", "Hearts")
    two_clubs = BalatroCard("2", "Clubs")

    # Decision 1: the real modeled Burnt Joker must naturally create the production
    # FORMING strategy before D1 uses its bounded first-discard development signal.
    development_state = _state([ace, two_hearts, two_clubs])
    development = evaluate_burnt_bond(development_state)
    assert development.unlocked
    assert development.target == "HIGH_CARD"

    _, composition = evaluate_bond_composition(development_state)
    burnt_candidate = next(
        candidate
        for candidate in composition.strategy_candidates
        if candidate.strategy_id == "burnt_target_level"
    )
    assert burnt_candidate.commitment == StrategyCommitment.FORMING
    assert composition.pinned_strategy_id is None
    assert composition.strategy_plan is not None
    assert composition.strategy_plan.strategy_id == burnt_candidate.strategy_id

    weak_play = _plan(PLAY_CARDS, [two_hearts, two_clubs], expected_score=10.0)
    generic_pair_discard = _plan(DISCARD_CARDS, [two_hearts, two_clubs])
    target_high_card_discard = _plan(DISCARD_CARDS, [ace])

    target_fit, target_notes = _burnt_strategy_fit(
        development_state,
        target_high_card_discard.action,
    )
    generic_fit, _ = _burnt_strategy_fit(
        development_state,
        generic_pair_discard.action,
    )
    assert target_fit > generic_fit
    assert any("Burnt target=HIGH_CARD" in note for note in target_notes)

    first_decision = policy.decide(
        development_state,
        [weak_play, generic_pair_discard, target_high_card_discard],
        setup_discard_consensus=True,
    )
    assert _action_signature(first_decision.action) == _action_signature(
        target_high_card_discard.action
    )

    # Decision 2: the next observed state contains the public result of Burnt's
    # trigger. At level 1 neither available play meets pace; after Burnt raises
    # High Card to level 2, that exact hand clears the pace threshold and becomes
    # the canonical play while the otherwise stronger level-1 Pair remains below it.
    exploitation_state = _state(
        [ace, two_hearts, two_clubs],
        discards_remaining=1,
        discards_used=1,
        blind_requirement=150,
    )
    level_one_high = scorer.score(
        PokerHand.HIGH_CARD,
        exploitation_state,
        cards=[ace],
        include_card_chips=True,
    ).total
    pair_score = scorer.score(
        PokerHand.PAIR,
        exploitation_state,
        cards=[two_hearts, two_clubs],
        include_card_chips=True,
    ).total
    assert level_one_high < pair_score

    exploitation_state.hand_levels["HIGH_CARD"] = 2
    developed_high = scorer.score(
        PokerHand.HIGH_CARD,
        exploitation_state,
        cards=[ace],
        include_card_chips=True,
    ).total
    assert developed_high > pair_score

    pair_play = _plan(PLAY_CARDS, [two_hearts, two_clubs], expected_score=pair_score)
    developed_high_play = _plan(PLAY_CARDS, [ace], expected_score=developed_high)
    exploit_decision = policy.decide(
        exploitation_state,
        [pair_play, developed_high_play],
    )
    assert _action_signature(exploit_decision.action) == _action_signature(
        developed_high_play.action
    )

    # Decision 3: permanent development does not authorize another setup action
    # when the current play deterministically clears the blind. Survival remains
    # the D1 authority even though a first discard is still otherwise available.
    pressure_state = _state(
        [ace, two_hearts, two_clubs],
        hands_remaining=1,
        discards_remaining=2,
        discards_used=0,
        blind_requirement=developed_high,
    )
    pressure_state.hand_levels["HIGH_CARD"] = 2
    survival_play = _plan(
        PLAY_CARDS,
        [ace],
        clear_probability=1.0,
        expected_score=developed_high,
    )
    tempting_development_discard = _plan(
        DISCARD_CARDS,
        [ace],
        clear_probability=0.10,
        expected_score=developed_high + 50.0,
    )

    assert _burnt_strategy_fit(
        pressure_state,
        tempting_development_discard.action,
    ) == (0.0, ())
    pressure_decision = policy.decide(
        pressure_state,
        [tempting_development_discard, survival_play],
        setup_discard_consensus=True,
    )
    assert _action_signature(pressure_decision.action) == _action_signature(
        survival_play.action
    )
