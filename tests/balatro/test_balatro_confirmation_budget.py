from games.balatro.live.adaptive_search import AdaptiveBlindSearchConfig
from games.balatro.live.hand_action_policy import LiveHandActionDecisionEngine


def test_confirmation_strengthens_sampling_with_dedicated_node_cap():
    engine = LiveHandActionDecisionEngine(max_search_nodes=5000)
    config = AdaptiveBlindSearchConfig(
        horizon=2,
        samples=8,
        child_samples=1,
        play_width=3,
        discard_width=1,
        child_play_width=1,
        child_discard_width=1,
        max_nodes=2000,
    )

    confirmation = engine._confirmation_config(config)

    assert confirmation.horizon == config.horizon
    assert confirmation.samples >= engine.CONFIRMATION_MIN_ROOT_SAMPLES
    assert confirmation.samples > config.samples
    assert confirmation.child_samples >= engine.CONFIRMATION_MIN_CHILD_SAMPLES
    assert confirmation.child_samples > config.child_samples
    assert confirmation.play_width == config.play_width
    assert confirmation.discard_width == config.discard_width
    assert confirmation.child_play_width == config.child_play_width
    assert confirmation.child_discard_width == config.child_discard_width
    assert confirmation.max_nodes == engine.CONFIRMATION_MAX_NODES
    assert confirmation.max_nodes < config.max_nodes


def test_confirmation_budget_never_exceeds_smaller_originating_search():
    engine = LiveHandActionDecisionEngine(max_search_nodes=5000)
    config = AdaptiveBlindSearchConfig(
        horizon=2,
        samples=8,
        child_samples=1,
        play_width=3,
        discard_width=1,
        child_play_width=1,
        child_discard_width=1,
        max_nodes=500,
    )

    confirmation = engine._confirmation_config(config)

    assert confirmation.max_nodes == 500


def test_adaptive_and_confirmation_searches_share_one_wall_clock_deadline():
    engine = LiveHandActionDecisionEngine(max_search_seconds=8.0)
    engine._search_deadline = 123.0
    config = AdaptiveBlindSearchConfig(
        horizon=2,
        samples=8,
        child_samples=1,
        play_width=3,
        discard_width=1,
        child_play_width=1,
        child_discard_width=1,
        max_nodes=500,
    )

    adaptive = engine._adaptive_planner(config)
    confirmation = engine._adaptive_planner(engine._confirmation_config(config))

    assert adaptive.deadline == 123.0
    assert confirmation.deadline == 123.0
