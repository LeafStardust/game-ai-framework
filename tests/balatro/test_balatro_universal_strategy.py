from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.jokers.pareidolia import PareidoliaJoker
from games.balatro.jokers.ride_the_bus import RideTheBusJoker
from games.balatro.jokers.the_duo import TheDuoJoker
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy
from games.balatro.planets import create_planet
from games.balatro.playbook import default_balatro_playbooks
from games.balatro.shop_consumable_policy import (
    HOLD,
    ConsumableAcquisitionPolicy,
    ConsumableAcquisitionThresholds,
)
from games.balatro.state import BalatroState
from games.balatro.strategy import BANNED, GOLD, BalatroStrategyTracker
from games.balatro.strategy_catalog import UNIVERSAL_BALATRO_STRATEGIES
from games.balatro.strategy_pack_playstyle import StrategyAwarePackPlaystyleEvaluator
from games.balatro.strategy_value import (
    StrategyAwareConsumableSynergyEvaluator,
    StrategyAwareJokerBuildValueEvaluator,
)


def _state() -> BalatroState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    return state


def _tracker() -> BalatroStrategyTracker:
    return BalatroStrategyTracker(
        UNIVERSAL_BALATRO_STRATEGIES,
        modifier_provider=lambda state: (
            default_balatro_playbooks().for_state(state).strategy_modifiers()
        ),
    )


def test_strategy_definitions_are_universal_and_red_white_only_modifies_them():
    playbook = default_balatro_playbooks().get("RED", "WHITE")

    assert "straight_flush" in UNIVERSAL_BALATRO_STRATEGIES
    assert "hearts" in UNIVERSAL_BALATRO_STRATEGIES
    assert "diamonds" in UNIVERSAL_BALATRO_STRATEGIES
    assert "clubs" in UNIVERSAL_BALATRO_STRATEGIES
    assert "spades" in UNIVERSAL_BALATRO_STRATEGIES
    straight_flush = UNIVERSAL_BALATRO_STRATEGIES["straight_flush"]
    assert "neptune" in straight_flush.gold_planets

    modifiers = playbook.strategy_modifiers()
    assert "definitions" not in modifiers
    assert modifiers["strategies"]["straight_flush"]["enabled"] is False
    assert modifiers["strategies"]["straight"]["effectiveness"] == 1.10
    assert modifiers["strategies"]["flush"]["effectiveness"] == 1.10


def test_neutral_start_has_zero_strategy_scores_and_no_gold_autobuy_bonus():
    state = _state()
    tracker = _tracker()

    resolution = tracker.observe(state)
    assert resolution.dominant_strategy_id is None
    assert all(assessment.score == 0.0 for assessment in resolution.assessments)

    evaluation = tracker.evaluate_item(state, TheDuoJoker(), kind="JOKER")
    assert evaluation.tier == GOLD
    assert evaluation.value == 0.0
    assert evaluation.projected_score > 0.0


def test_current_owned_joker_adds_evidence_and_selling_removes_it():
    state = _state()
    tracker = _tracker()

    state.jokers = [JollyJoker()]
    with_jolly = tracker.observe(state)
    assert with_jolly.assessment("pair").score > 0.0

    state.jokers = []
    after_sale = tracker.observe(state)
    assert after_sale.assessment("pair").score == 0.0
    assert after_sale.dominant_strategy_id is None


def test_strategy_purchase_influence_rises_with_ante():
    state = _state()
    state.jokers = [JollyJoker()]
    tracker = _tracker()

    state.ante = 1
    early = tracker.evaluate_item(state, TheDuoJoker(), kind="JOKER")
    state.ante = 6
    late = tracker.evaluate_item(state, TheDuoJoker(), kind="JOKER")

    assert early.value > 0.0
    assert late.value > early.value


def test_shared_pair_joker_highlights_pair_not_composite_full_house():
    state = _state()
    state.jokers = [JollyJoker()]
    tracker = _tracker()

    resolution = tracker.observe(state)

    assert resolution.active_strategy_id == "pair"
    assert resolution.assessment("pair").score > resolution.assessment("full_house").score


def test_gold_pair_joker_is_prioritized_inside_leading_pair_strategy():
    state = _state()
    state.jokers = [JollyJoker()]
    tracker = _tracker()
    assert tracker.observe(state).active_strategy_id == "pair"

    evaluation = tracker.evaluate_item(
        state,
        TheDuoJoker(),
        kind="JOKER",
    )

    assert evaluation.strategy_id == "pair"
    assert evaluation.tier == GOLD
    assert evaluation.active_alignment
    assert evaluation.value > 0.0


def test_held_planet_is_not_current_evidence_but_used_planet_level_is():
    state = _state()
    tracker = _tracker()
    state.consumables = [create_planet("MERCURY")]

    assert tracker.observe(state).assessment("pair").score == 0.0

    state.hand_levels["PAIR"] = 2
    assert tracker.observe(state).assessment("pair").score > 0.0


def test_banned_joker_is_negative_strategy_evidence_and_purchase_alignment():
    state = _state()
    tracker = _tracker()

    state.jokers = [PareidoliaJoker()]
    face_before = tracker.observe(state).assessment("face_cards").score
    assert face_before > 0.0

    candidate = tracker.evaluate_item(state, RideTheBusJoker(), kind="JOKER")
    assert candidate.tier == BANNED
    assert candidate.value < 0.0

    state.jokers.append(RideTheBusJoker())
    face_after = tracker.observe(state).assessment("face_cards").score
    assert face_after < face_before


def test_persistent_suit_conversion_creates_suit_strategy_evidence():
    state = _state()
    state.owned_deck = [
        BalatroCard(card.rank, card.suit, card.enhancement, card.edition, card.seal)
        for card in state.deck
    ]
    # Move two permanent cards from Diamonds into Hearts. A normal 13/13/13/13
    # deck has zero suit-concentration evidence; this creates real Hearts evidence.
    changed = 0
    for card in state.owned_deck:
        if card.suit == "Diamonds" and changed < 2:
            card.suit = "Hearts"
            changed += 1

    tracker = _tracker()
    resolution = tracker.observe(state)

    assert resolution.assessment("hearts").score > 0.0
    assert resolution.assessment("diamonds").score == 0.0


def test_cartridge_can_bias_or_disable_universal_strategies_without_redefining_them():
    state = _state()
    tracker = BalatroStrategyTracker(
        UNIVERSAL_BALATRO_STRATEGIES,
        modifier_provider=lambda state: {
            "strategies": {
                "hearts": {"base_score": 2.0, "effectiveness": 1.20},
                "spades": {"enabled": False},
            }
        },
    )

    resolution = tracker.observe(state)

    assert resolution.assessment("hearts").score == 2.0
    assert resolution.assessment("hearts").effectiveness == 1.20
    assert resolution.assessment("spades") is None
    assert resolution.dominant_strategy_id == "hearts"


def test_strategy_aware_d2_neutralizes_legacy_playstyle_lock():
    state = _state()
    state.ante = 6
    state.jokers = [RideTheBusJoker()]

    evaluator = StrategyAwareJokerBuildValueEvaluator(
        strategy_tracker=_tracker(),
    )
    result = evaluator.evaluate(state, PareidoliaJoker())

    assert result.playstyle_fit == 0.0
    assert result.playstyle_value == 0.0
    assert not result.playstyle_locked


def test_strategy_aware_d1_keeps_legacy_playstyle_intent_neutral():
    state = _state()
    state.ante = 6
    state.jokers = [RideTheBusJoker()]
    policy = StrategyAwareLiveHandActionPolicy(
        strategy_tracker=_tracker(),
    )

    intent = policy.playstyle_evaluator.prepare(state)

    assert intent.strengths == ()
    assert not intent.locked


def test_strategy_aware_d9_keeps_legacy_playstyle_intent_neutral():
    state = _state()
    state.ante = 6
    state.jokers = [RideTheBusJoker()]
    evaluator = StrategyAwarePackPlaystyleEvaluator(
        strategy_tracker=_tracker(),
    )

    result = evaluator.evaluate(
        state,
        kind="PLAYING_CARD",
        rank="K",
        suit="Hearts",
    )

    assert result.intent.strengths == ()
    assert not result.intent.locked


def test_red_white_blocks_neptune_and_other_planets_until_their_strategy_is_active():
    state = _state()
    state.phase = "SHOP"
    state.money = 20
    tracker = _tracker()
    evaluator = StrategyAwareConsumableSynergyEvaluator(
        strategy_tracker=tracker,
    )
    thresholds = ConsumableAcquisitionThresholds.from_mapping(
        default_balatro_playbooks().for_state(state).thresholds_for("D4")
    )
    policy = ConsumableAcquisitionPolicy(
        thresholds,
        evaluator=evaluator,
    )

    neptune = create_planet("NEPTUNE")
    jupiter = create_planet("JUPITER")

    assert tracker.evaluate_item(state, neptune, kind="PLANET").tier is None
    assert evaluator.evaluate(neptune, state).total_gain < 0.0
    assert policy.decide(state, neptune).action == HOLD

    assert evaluator.evaluate(jupiter, state).total_gain < 0.0
    assert policy.decide(state, jupiter).action == HOLD


def test_active_pair_strategy_admits_mercury_but_rejects_off_strategy_jupiter():
    state = _state()
    state.phase = "SHOP"
    state.money = 20
    state.jokers = [JollyJoker()]
    tracker = _tracker()
    assert tracker.observe(state).active_strategy_id == "pair"

    evaluator = StrategyAwareConsumableSynergyEvaluator(
        strategy_tracker=tracker,
    )
    mercury = create_planet("MERCURY")
    jupiter = create_planet("JUPITER")

    mercury_value = evaluator.evaluate(mercury, state)
    jupiter_value = evaluator.evaluate(jupiter, state)

    assert mercury_value.total_gain > 0.0
    assert jupiter_value.total_gain < 0.0


def test_d1_prefers_active_strategic_hand_when_survival_layer_considers_lines_equal():
    state = _state()
    state.jokers = [JollyJoker()]
    tracker = _tracker()
    assert tracker.observe(state).active_strategy_id == "pair"
    policy = StrategyAwareLiveHandActionPolicy(
        strategy_tracker=tracker,
    )

    pair = BalatroAction(
        PLAY_CARDS,
        [
            BalatroCard("A", "Spades"),
            BalatroCard("A", "Hearts"),
        ],
    )
    high_card = BalatroAction(
        PLAY_CARDS,
        [
            BalatroCard("A", "Spades"),
            BalatroCard("K", "Hearts"),
        ],
    )

    pair_fit, _ = policy._strategy_fit(state, pair)
    high_card_fit, _ = policy._strategy_fit(state, high_card)

    assert pair_fit > 0.0
    assert pair_fit > high_card_fit
